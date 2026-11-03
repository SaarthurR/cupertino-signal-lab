"""Hidden worlds: demand the learner cannot read, and the stale old timing built from distorted demand."""
from collections import Counter
import copy
import hashlib
import json
import math
import random
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from learner import check, practice, road
from signal_lab import baseline, demand as d, pipeline as p

WORLDS = p.ROOT/'worlds'
TRUTH = p.ROOT/'reports/learner_truth'
LABEL = 'SYNTHETIC simulated demand from a fixed seed; not observed traffic'
# Fixed per road: world demand seed; stale-demand factors use seed+1000.
SEEDS = {'stevens_creek': 10, 'homestead': 11, 'wolfe': 12, 'deanza': 13}
# Hourly vehicles per approach lane, drawn per approach; calibrated on Homestead only, frozen for held-out roads.
MAIN_RATE, SIDE_RATE = (400, 640), (130, 280)
STALE = (.6, 1.4)
WATCH_SEEDS = range(3)


def routes(name):
    return p.ROOT/'sim/routes_pm_peak.rou.xml' if name == 'stevens_creek' else WORLDS/name/'routes.rou.xml'


def turn_counts(cfg, network, seed):
    """PM rush with a per-approach peak; flows and turn shares differ per approach."""
    rng = random.Random(seed)
    begin, end = road.window(cfg)
    starts = range(begin-cfg['warmup_s'], end, 900)
    counts = {t: {} for t in starts}
    for incoming, outs in sorted(road.relations(cfg, network).items()):
        edge = network.getEdge(incoming)
        main = incoming in cfg['mainline_edges']
        lanes = [l for l in edge.getLanes() if l.allows('passenger')]
        # Turn pockets add no approach volume: scale by through lanes, or all lanes where none go straight.
        through = sum(any(c.getDirection() == 's' for c in l.getOutgoing()) for l in lanes) or len(lanes)
        hourly = rng.uniform(*(MAIN_RATE if main else SIDE_RATE))*through
        weight = {'s': 1., 'l': rng.uniform(.08, .2), 'r': rng.uniform(.05, .15)} if main else \
            {k: rng.uniform(.2, 1.) for k in 'slr'}
        shares = {o: weight[k]/sum(1 for v in outs.values() if v == k) for o, k in outs.items()}
        total = sum(shares.values())
        peak, width = rng.uniform(d.seconds('17:15'), d.seconds('17:45')), rng.uniform(2400, 3600)
        profile = {t: .7+.6*math.exp(-((t+450-peak)/width)**2) for t in starts}
        scale = len(range(begin, end, 900))/sum(profile[t] for t in starts if t >= begin)
        for t in starts:
            for o, share in shares.items():
                counts[t][incoming, o] = round(hourly/4*profile[t]*scale*share/total)
    return counts


def build_demand(name):
    cfg = road.load(name)
    network = road.net(cfg)
    folder = WORLDS/name
    folder.mkdir(parents=True, exist_ok=True)
    counts = turn_counts(cfg, network, SEEDS[name])
    with tempfile.TemporaryDirectory() as temp:
        pairs = {pair: pair for t in counts.values() for pair in t}
        d.candidate_routes(network, pairs, Path(temp)/'candidates.xml')
        d.turn_file(counts, Path(temp)/'turns.xml')
        log = d.sample(Path(temp)/'candidates.xml', Path(temp)/'turns.xml', folder/'routes.rou.xml')
    root = ET.parse(folder/'routes.rou.xml').getroot()
    root.insert(0, ET.Comment(LABEL))
    p.xml_write(root, folder/'routes.rou.xml')
    return dict(label=LABEL, seed=SEEDS[name], main_rate=MAIN_RATE, side_rate=SIDE_RATE,
                vehicles=len(root.findall('vehicle')), sample_log=log)


def stale_routes(cfg, source, seed, output):
    """Same road, flows scaled by one fixed seeded factor per origin approach."""
    rng = random.Random(seed)
    root = ET.parse(source).getroot()
    counted = set(cfg['mainline_edges']) | set(cfg['side_edges'])
    groups = {}
    for vehicle in root.findall('vehicle'):
        origin = next(e for e in vehicle.find('route').get('edges').split() if e in counted)
        groups.setdefault(origin, []).append(vehicle)
    factors = {}
    for origin, vehicles in sorted(groups.items()):
        factors[origin] = factor = rng.uniform(*STALE)
        n = round(len(vehicles)*abs(factor-1))
        for i in range(n):
            vehicle = vehicles[int((i+.5)*len(vehicles)/n)]
            if factor < 1:
                root.remove(vehicle)
            else:
                clone = copy.deepcopy(vehicle)
                clone.set('id', f'stale_{origin}_{i}')
                root.append(clone)
    vehicles = sorted(root.findall('vehicle'), key=lambda v: float(v.get('depart')))
    for vehicle in root.findall('vehicle'):
        root.remove(vehicle)
    root.extend(vehicles)
    p.xml_write(root, output)
    return factors


def build_world(name):
    """Hidden demand (new roads) and the old timing: textbook actuated method on stale demand."""
    cfg = road.load(name)
    info = build_demand(name) if name != 'stevens_creek' else dict(label='VTA 2024 count-fitted PM routes', vehicles=None)
    with tempfile.TemporaryDirectory() as temp:
        stale = Path(temp)/'stale.rou.xml'
        info['stale_factors'] = stale_routes(cfg, routes(name), SEEDS[name]+1000, stale)
        info['stale_range'] = STALE
        logs = baseline.actuated(road.file(cfg, 'net'), stale, road.window(cfg)[0],
                                 [s['sumo_tls_id'] for s in cfg['signals']], cfg['mainline_edges'],
                                 road.file(cfg, 'timing_inputs'), road.file(cfg, 'old_timing'))
    timing = ET.parse(road.file(cfg, 'old_timing')).getroot()
    timing.insert(0, ET.Comment('OLD timing for the learner test: textbook actuated plan from STALE simulated demand'))
    p.xml_write(timing, road.file(cfg, 'old_timing'))
    info['tool_log'] = logs
    info['routes_sha256'] = hashlib.sha256(routes(name).read_bytes()).hexdigest()
    (WORLDS/name).mkdir(parents=True, exist_ok=True)
    (WORLDS/name/'world.json').write_text(json.dumps(info, indent=2)+'\n')
    return info


def fresh_plan(name):
    """Descriptive textbook retiming from the true current demand; never an input to the learner."""
    cfg = road.load(name)
    output = TRUTH/name/'fresh_timing.add.xml'
    output.parent.mkdir(parents=True, exist_ok=True)
    baseline.actuated(road.file(cfg, 'net'), routes(name), road.window(cfg)[0],
                      [s['sumo_tls_id'] for s in cfg['signals']], cfg['mainline_edges'],
                      road.file(cfg, 'timing_inputs'), output)
    return output


def bad_plan(cfg, path):
    """Deliberately bad, still within bounds: shortest cycle, mainline starved, offsets half a cycle off."""
    old = practice.old_params(cfg)
    logics = ET.parse(road.file(cfg, 'old_timing')).getroot().findall('tlLogic')
    params = {'cycle_s': practice.bounds('cycle_s', old['cycle_s'])[0]}
    for index, logic in enumerate(logics):
        params[f'offset_{index}'] = (old[f'offset_{index}']+.5) % 1
        for i, phase in enumerate(logic.findall('phase')):
            if phase.get('minDur') is not None:
                params[f'share_{index}_{i}'] = .6 if phase.get('name') == 'mainline' else 1.4
    practice.plan(cfg, params, path)
    return _program(path, 'bad')


def noop_plan(cfg, path):
    """The old timing under another program name: a change that changes nothing."""
    p.xml_write(ET.parse(road.file(cfg, 'old_timing')).getroot(), path)
    return _program(path, 'noop')


def _program(path, name):
    root = ET.parse(path).getroot()
    for logic in root.findall('tlLogic'):
        logic.set('programID', name)
    p.xml_write(root, path)
    return name


def waut(cfg, path, switches):
    root = ET.Element('additional')
    plan = ET.SubElement(root, 'WAUT', id='approved', refTime='0', startProg='actuated')
    for time, program in switches:
        ET.SubElement(plan, 'wautSwitch', time=str(time), to=program)
    for signal in cfg['signals']:
        ET.SubElement(root, 'wautJunction', wautID='approved', junctionID=signal['sumo_tls_id'])
    p.xml_write(root, path)
    return path


def check_run(name, plan, program, seed, change_s=d.seconds('17:00'), demand=None):
    """Old timing until the approved change, then the change; the learner's rule reads the feed and may go back."""
    cfg = road.load(name)
    old = road.file(cfg, 'old_timing')
    demand = routes(name) if demand is None else demand
    with tempfile.TemporaryDirectory() as temp:
        held, (rows, _) = road.simulate(cfg, demand, old, seed, True,
                                        [plan, waut(cfg, Path(temp)/'held.xml', [(change_s, program)])])
        decision = check.decide(name, rows, change_s)
        ruled = held
        if decision['go_back']:
            ruled, _ = road.simulate(cfg, demand, old, seed, False, [plan, waut(
                cfg, Path(temp)/'back.xml', [(change_s, program), (decision['time_s'], 'actuated')])])
    pick = lambda s: {k: s[k] for k in ('all_requested_delay_s', 'unfinished', 'teleports', 'worst_origin_delay_s')}
    return dict(road=name, program=program, seed=seed, change_s=change_s, **decision,
                held=pick(held), with_rule=pick(ruled))


def truth_fit(name):
    """Copy demand against hidden demand: count vehicles and signal-turn passages separately."""
    cfg = road.load(name)
    begin, end = road.window(cfg)
    pairs = {(i, o) for i, outs in road.relations(cfg, road.net(cfg)).items() for o in outs}

    def turns(path):
        counts = Counter()
        vehicles = 0
        for vehicle in ET.parse(path).getroot().iter('vehicle'):
            depart = float(vehicle.get('depart'))
            if begin <= depart < end:
                vehicles += 1
                edges = vehicle.find('route').get('edges').split()
                counts.update((int(depart)//900*900, a, b) for a, b in zip(edges, edges[1:]) if (a, b) in pairs)
        return counts, vehicles
    (truth, truth_vehicles), (learned, copy_vehicles) = turns(routes(name)), turns(road.OUT/name/'copy.rou.xml')
    rows = [dict(quarter_start_s=t, from_edge=a, to_edge=b, truth=truth[t, a, b], copy=learned[t, a, b],
                 geh=round(d.geh(truth[t, a, b], learned[t, a, b]), 3))
            for t, a, b in sorted(set(truth) | set(learned))]
    total = sum(truth.values())
    if not rows or total <= 0:
        raise ValueError('No signal-turn passages in the evaluation cohort')
    (TRUTH/name).mkdir(parents=True, exist_ok=True)
    p.write_csv(TRUTH/name/'copy_vs_truth.csv', rows)
    summary = dict(road=name, turn_quarters=len(rows), geh_under_5_share=sum(r['geh'] < 5 for r in rows)/len(rows),
                   truth_turn_passages=total, copy_turn_passages=sum(learned.values()),
                   truth_unique_trips=truth_vehicles, copy_unique_trips=copy_vehicles,
                   abs_error_share=sum(abs(r['truth']-r['copy']) for r in rows)/total)
    (TRUTH/name/'copy_vs_truth.json').write_text(json.dumps(summary, indent=2)+'\n')
    return summary


def watch(name, seeds=WATCH_SEEDS):
    """Run the world on old timing; write only the feed where the learner can read it."""
    cfg = road.load(name)
    results = road.many([(cfg, routes(name), road.file(cfg, 'old_timing'), s, True) for s in seeds])
    for seed, (stats, (rows, lanes)) in zip(seeds, results):
        folder = road.OUT/name/'feed'/f'seed{seed}'
        folder.mkdir(parents=True, exist_ok=True)
        p.write_csv(folder/'feed.csv', rows)
        p.write_csv(folder/'lanes.csv', lanes)
    (TRUTH/name).mkdir(parents=True, exist_ok=True)
    (TRUTH/name/'watch_metrics.json').write_text(json.dumps([s for s, _ in results], indent=2)+'\n')
    return [s for s, _ in results]
