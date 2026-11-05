"""Export measured engineer-console data without changing plans or evaluation artifacts.

Run: PYTHONPATH=src python -m tools.engineer_metrics [wolfe deanza homestead stevens_creek]
Headline delay is the existing all-requested score, NOT intersection control delay.
Approach delay is time loss accrued on incoming edges per observed vehicle visit;
queues count stopped vehicles (<0.1 m/s) on those edges, sampled every second.
AoG/PCD use first entry within 5 m of the stop bar, including permissive green.
Timing greens are configured maxima; actuated branching has no single yellow/red
clearance per green phase, so those fields are null.
"""
import argparse
from collections import defaultdict
import copy
import csv
import json
from pathlib import Path
import re
import tempfile
import time
import xml.etree.ElementTree as ET

from learner import card, road
from signal_lab import evaluate, pipeline
from world import worlds

ROOT = Path(__file__).resolve().parents[1]
DIRECTION = {'N': 'SB', 'S': 'NB', 'E': 'WB', 'W': 'EB'}
WINDOW = (61200, 61800)


def mean(values):
    return round(sum(values)/len(values), 3) if values else None


def sample(values, limit):
    return values if len(values) <= limit else [values[i*len(values)//limit] for i in range(limit)]


def clock(t):
    return f'{int(t)//3600:02}:{int(t)%3600//60:02}'


def timing(path, cfg, net):
    return {sid: dict(cycle_s=row['cycle_s'], offset_s=row['offset_s'], phases=[
        dict(phase=g['phase'], label=', '.join(DIRECTION[s[0]]+s[1:] for s in g['serves']),
             green_s=g['max_green_s'], yellow_s=None, red_s=None) for g in row['greens']])
            for sid, row in card.settings(path, cfg, net).items()}


def endpoints(cfg, net, positions):
    """Outside entry edge to outside exit edge, through both end signals."""
    ends = sorted(cfg['signals'], key=lambda s: positions[s['sumo_tls_id']])
    legs = road.approaches(cfg, net)
    pairs = []
    for signal in (ends[0], ends[-1]):
        directions = defaultdict(set)
        for a, b, _ in net.getTLS(signal['sumo_tls_id']).getConnections():
            if a.getEdge().getID() in cfg['mainline_edges'] and b.getEdge().getID() in cfg['mainline_edges']:
                if any(c.getToLane() == b and c.getDirection() == 's' for c in a.getOutgoing()):
                    directions[DIRECTION[legs[a.getEdge().getID()][1]]].add((a.getEdge().getID(), b.getEdge().getID()))
        pairs.append({d: next(iter(p)) for d, p in directions.items() if len(p) == 1})
    out = {}
    for direction in ('NB', 'SB', 'EB', 'WB'):
        first, last = pairs if direction in ('NB', 'EB') else pairs[::-1]
        if direction in first and direction in last:
            out[direction] = first[direction][0], last[direction][1]
    return out


def run(cfg, net, path, seed, positions, axis):
    import libsumo as sumo
    from traci import constants as tc
    begin, end = road.window(cfg)
    directions = ('NB', 'SB') if axis else ('EB', 'WB')
    legs = road.approaches(cfg, net)
    name_to_id = {s['name']: s['sumo_tls_id'] for s in cfg['signals']}
    lane_info = {lane.getID(): (name_to_id[site], DIRECTION[leg])
                 for edge, (site, leg) in legs.items() for lane in net.getEdge(edge).getLanes()
                 if lane.allows('passenger')}
    keys = sorted(set(lane_info.values()))
    lane_ids = list(lane_info)
    visits, arrivals = defaultdict(set), defaultdict(list)
    loss, queues, queue_max = defaultdict(float), defaultdict(list), defaultdict(int)
    by_loss, by_visits, by_queue = defaultdict(float), defaultdict(set), defaultdict(list)
    seen_bar, previous_loss = set(), {}
    routes = {v.get('id'): v.find('route').get('edges').split()
              for v in ET.parse(worlds.routes(cfg['name'])).getroot().findall('vehicle')}
    detectors = {f'metrics_{i}': lane for i, lane in enumerate(lane_ids)}
    greens, paths = [], {}
    cycle_start, previous_phase, open_green = {}, {}, {}
    cycle_starts = defaultdict(list)
    pcd_points, pcd_bands = defaultdict(list), defaultdict(list)
    split_failures, green_queue, was_green = defaultdict(int), {}, {}
    emission_classes, emissions, travels = set(), {}, defaultdict(list)
    sid_keys = {s['sumo_tls_id']: [k for k in keys if k[0] == s['sumo_tls_id']] for s in cfg['signals']}
    links = {sid: net.getTLS(sid).getConnections() for sid in sid_keys}
    through = {k: [i for incoming, outgoing, i in links[k[0]]
                   if lane_info.get(incoming.getID()) == k and incoming.getEdge().getID() in cfg['mainline_edges']
                   and any(c.getToLane() == outgoing and c.getDirection() == 's' for c in incoming.getOutgoing())]
               for k in keys}
    approach_links = {k: [i for incoming, _, i in links[k[0]] if lane_info.get(incoming.getID()) == k] for k in keys}
    for k in keys:
        straight = [i for incoming, outgoing, i in links[k[0]] if lane_info.get(incoming.getID()) == k
                    and any(c.getToLane() == outgoing and c.getDirection() == 's' for c in incoming.getOutgoing())]
        approach_links[k] = straight or approach_links[k]
    boundary = endpoints(cfg, net, positions)
    by_score = {}

    def runner(args, timeout):
        stop, deadline = float(args[args.index('-e')+1]), time.monotonic()+timeout
        routes_path = Path(args[args.index('--tripinfo-output')+1]).with_name('vehicle_routes.xml')
        sumo.start(list(map(str, args))+['--device.emissions.probability', '1', '--emissions.volumetric-fuel', 'true',
                   '--vehroute-output', str(routes_path), '--vehroute-output.exit-times', 'true',
                   '--vehroute-output.write-unfinished', 'true'])
        try:
            for lane in lane_ids:
                sumo.lane.subscribe(lane, (tc.LAST_STEP_VEHICLE_ID_LIST, tc.LAST_STEP_VEHICLE_HALTING_NUMBER))
            while sumo.simulation.getMinExpectedNumber() > 0 and sumo.simulation.getTime() < stop:
                if time.monotonic() > deadline:
                    raise TimeoutError('Metrics run timed out')
                states = {sid: sumo.trafficlight.getRedYellowGreenState(sid) for sid in sid_keys}
                phases = {sid: sumo.trafficlight.getPhase(sid) for sid in sid_keys}
                t0 = sumo.simulation.getTime()
                for sid, phase in phases.items():
                    if phase == 0 and sid in previous_phase and previous_phase[sid] != 0:
                        cycle_start[sid] = t0
                        cycle_starts[sid].append(t0)
                    previous_phase[sid] = phase
                sumo.simulationStep()
                t = sumo.simulation.getTime()
                for vid in sumo.simulation.getDepartedIDList():
                    emission_classes.add(sumo.vehicle.getEmissionClass(vid))
                    sumo.vehicle.subscribe(vid, (tc.VAR_LANE_ID, tc.VAR_TIMELOSS, tc.VAR_POSITION))
                vehicles = sumo.vehicle.getAllSubscriptionResults()
                current_queues = defaultdict(int)
                split_states = {sid: sumo.trafficlight.getRedYellowGreenState(sid) for sid in sid_keys}
                for lane, values in sumo.lane.getAllSubscriptionResults().items():
                    current_queues[lane_info[lane]] += values[tc.LAST_STEP_VEHICLE_HALTING_NUMBER]
                active = begin <= t0 < end
                bucket = int((t0-begin)//900)
                for k in keys:
                    q = current_queues[k]
                    served = any(split_states[k[0]][i] in 'Gg' for i in approach_links[k])
                    if served and not was_green.get(k, served):
                        green_queue[k] = q > 0 if begin <= t < end else None
                    if not served and was_green.get(k, False):
                        if begin <= t < end and green_queue.get(k) and q > 0:
                            split_failures[k] += 1
                        green_queue.pop(k, None)
                    was_green[k] = served
                    if active:
                        queues[k].append(q)
                        queue_max[k] = max(queue_max[k], q)
                        by_queue[k, bucket].append(q)
                    indices = through[k]
                    green = bool(indices) and any(states[k[0]][i] in 'Gg' for i in indices)
                    if green and k not in open_green:
                        open_green[k] = (t0, cycle_start.get(k[0]))
                    if not green and k in open_green:
                        start, origin = open_green.pop(k)
                        if origin is not None and begin <= start < end:
                            pcd_bands[k].append([round(start-origin, 2), round(t0-origin, 2)])
                        if start < WINDOW[1] and t0 > WINDOW[0]:
                            greens.append(dict(signal=k[0], x_m=positions[k[0]],
                                               start_s=max(start, WINDOW[0]), end_s=min(t0, WINDOW[1])))
                for detector, lane in detectors.items():
                    k = lane_info[lane]
                    for vid, _, entry, _, _ in sumo.inductionloop.getVehicleData(detector):
                        token = (vid, k)
                        if not begin <= entry < end or token in seen_bar:
                            continue
                        seen_bar.add(token)
                        edge = net.getLane(lane).getEdge().getID()
                        route = routes[vid]
                        index = route.index(edge)
                        outgoing = route[index+1] if index+1 < len(route) else None
                        indices = [i for a, b, i in links[k[0]] if a.getID() == lane and b.getEdge().getID() == outgoing]
                        # A vehicle can reach the detector before changing into its turn lane.
                        indices = indices or [i for a, b, i in links[k[0]] if a.getEdge().getID() == edge and b.getEdge().getID() == outgoing]
                        if not indices:
                            raise ValueError(f'No controlled movement for {vid} on {lane}')
                        colors = {states[k[0]][i] in 'Gg' for i in indices}
                        green = next(iter(colors)) if len(colors) == 1 else None
                        arrivals[k].append((entry, green, int((entry-begin)//900)))
                        origin = cycle_start.get(k[0])
                        if origin is not None:
                            pcd_points[k].append([round(entry, 2), round(entry-origin, 2)])
                for vid, values in vehicles.items():
                    lane = values[tc.VAR_LANE_ID]
                    total_loss = values[tc.VAR_TIMELOSS]
                    delta = max(0, total_loss-previous_loss.get(vid, total_loss))
                    previous_loss[vid] = total_loss
                    if lane in lane_info:
                        k = lane_info[lane]
                        if active:
                            visits[k].add(vid)
                            loss[k] += delta
                            by_visits[k, bucket].add(vid)
                            by_loss[k, bucket] += delta
                    if WINDOW[0] <= t < WINDOW[1] and int(t) % 5 == 0:
                        edge = lane.rsplit('_', 1)[0] if lane and not lane.startswith(':') else None
                        if edge in cfg['mainline_edges']:
                            e = net.getEdge(edge)
                            direction = ('NB' if e.getToNode().getCoord()[1] > e.getFromNode().getCoord()[1] else 'SB') if axis == 1 else ('EB' if e.getToNode().getCoord()[0] > e.getFromNode().getCoord()[0] else 'WB')
                            coordinate = values[tc.VAR_POSITION][axis]-positions['_origin']
                            paths.setdefault((vid, direction), []).append([t, round(coordinate, 2)])
                for vid in sumo.simulation.getArrivedIDList():
                    previous_loss.pop(vid, None)
        finally:
            sumo.close()
        trips_path = Path(args[args.index('--tripinfo-output')+1])
        trip_nodes = ET.parse(trips_path).getroot()
        trips = {v.get('id'): dict(v.attrib) for v in trip_nodes}
        warnings = Path(args[args.index('--error-log')+1]).read_text()
        teleports = re.findall(r"Teleporting vehicle '([^']+)'", warnings)
        requested = {v.get('id'): (float(v.get('depart')), False)
                     for v in ET.parse(worlds.routes(cfg['name'])).getroot().findall('vehicle')}
        cohort = {v for v, (depart, _) in requested.items() if begin <= depart < end}
        emissions['co2_kg'] = sum(float(v.find('emissions').get('CO2_abs')) for v in trip_nodes if v.get('id') in cohort)/1e6
        emissions['fuel_l'] = sum(float(v.find('emissions').get('fuel_abs')) for v in trip_nodes if v.get('id') in cohort)/1000
        for _, v in ET.iterparse(routes_path):
            if v.tag != 'vehicle':
                continue
            route = v.find('route')
            if v.get('id') not in teleports and route is not None:
                edges = route.get('edges').split()
                exits = list(map(float, route.get('exitTimes').split()))
                assert len(edges) == len(exits)
                for direction, (first, last) in boundary.items():
                    if first not in edges or last not in edges:
                        continue
                    a, b = edges.index(first), edges.index(last)
                    entry = exits[a-1] if a else float(v.get('depart'))
                    if a <= b and all(e in cfg['mainline_edges'] for e in edges[a:b+1]) and begin <= entry < end and exits[b] >= entry:
                        travels[direction].append((entry, exits[b]-entry))
            v.clear()
        for b in range((end-begin)//900):
            by_score[b] = evaluate.metrics(requested, trips, {}, teleports, begin+b*900, begin+(b+1)*900)['all_requested_delay_s']

    with tempfile.TemporaryDirectory() as folder:
        detector_path = Path(folder)/'arrivals.add.xml'
        root = ET.Element('additional')
        for detector, lane in detectors.items():
            ET.SubElement(root, 'inductionLoop', id=detector, lane=lane,
                          pos=str(max(0, net.getLane(lane).getLength()-5)), freq='900', file='/dev/null')
        ET.ElementTree(root).write(detector_path)
        stats, _ = road.simulate(cfg, worlds.routes(cfg['name']), path, seed, additional=(detector_path,), runner=runner)
    approaches = {}
    for k in keys:
        points = arrivals[k]
        approaches[k] = dict(volume_vph=round(len(points)*3600/(end-begin), 3),
            aog_pct=mean([100*green for _, green, _ in points]) if all(green is not None for _, green, _ in points) else None, split_failures=split_failures[k],
            avg_delay_s=round(loss[k]/len(visits[k]), 3) if visits[k] else None,
            max_queue_veh=queue_max[k])
    def quarter_hours(selected):
        out = []
        for b in range((end-begin)//900):
            n = sum(len(by_visits[k, b]) for k in selected)
            a = [green for k in selected for _, green, bucket in arrivals[k] if bucket == b]
            out.append(dict(t=clock(begin+b*900), delay_s=round(sum(by_loss[k, b] for k in selected)/n, 3) if n else None,
                            queue_veh=sum(mean(by_queue[k, b]) or 0 for k in selected), aog_pct=mean([100*g for g in a]) if all(g is not None for g in a) else None))
        return out
    signal_by15 = {sid: quarter_hours(selected) for sid, selected in sid_keys.items()}
    approach_by15 = {k: quarter_hours([k]) for k in keys}
    headline = dict(avg_delay_s_per_veh=stats['all_requested_delay_s'], stops_per_veh=stats['mean_waiting_count'],
                    travel_time_s={d: mean([duration for _, duration in travels[d]]) for d in directions}, unfinished_trips=stats['unfinished'],
                    vehicles=stats['requested'], **emissions)
    by15 = [dict(t=clock(begin+b*900), delay_s=by_score[b], queue_veh=round(sum(mean(by_queue[k, b]) or 0 for k in keys), 3),
                 **{f'tt_{d.lower()}_s': mean([duration for entry, duration in travels[d] if begin+b*900 <= entry < begin+(b+1)*900]) for d in directions}) for b in range((end-begin)//900)]
    trajectories = []
    for direction in directions:
        for start in range(WINDOW[0], WINDOW[1], 60):
            candidates = [pts for (_, d), pts in paths.items() if d == direction and start <= pts[0][0] < start+60]
            trajectories.extend(dict(dir=direction, pts=pts) for pts in sample(candidates, 4))
    return dict(headline=headline, by15=by15, approaches=approaches, signal_by15=signal_by15, approach_by15=approach_by15,
                pcd_points=pcd_points, pcd_bands=pcd_bands, cycle_starts=cycle_starts, stats=stats,
                emission_classes=sorted(emission_classes), time_space=dict(green=greens, trajectories=trajectories))


def export(name, seed=200):
    cfg, net = road.load(name), road.net(road.load(name))
    coords = {s['sumo_tls_id']: net.convertLonLat2XY(s['lon'], s['lat']) for s in cfg['signals']}
    axis = int(max(v[1] for v in coords.values())-min(v[1] for v in coords.values()) > max(v[0] for v in coords.values())-min(v[0] for v in coords.values()))
    origin = min(v[axis] for v in coords.values())
    positions = {sid: round(v[axis]-origin, 2) for sid, v in coords.items()} | {'_origin': origin}
    decision = json.loads((road.OUT/name/'card.json').read_text())['decision']
    old = road.file(cfg, 'old_timing')
    plans = {'baseline': old, 'proposed': road.OUT/name/'plan.add.xml' if decision == 'change' else old}
    sides = {}
    for arm, plan in plans.items():
        print(f'{name} {arm} seed {seed}', flush=True)
        sides[arm] = copy.deepcopy(sides['baseline']) if arm == 'proposed' and plan == old else run(cfg, net, plan, seed, positions, axis)
    reference = ROOT/'reports/learner_heldout/results.csv'
    for row in csv.DictReader(reference.read_text().splitlines()):
        arm = {'old': 'baseline', 'learner': 'proposed'}.get(row['arm'])
        if row['road'] == name and int(row['seed']) == seed and arm:
            stats = sides[arm]['stats']
            assert abs(stats['all_requested_delay_s']-float(row['all_requested_delay_s'])) < .001, (name, arm, stats, row)
            assert stats['unfinished'] == int(row['unfinished'])
    merge = lambda a, b: [dict(t=x['t'], baseline={k: v for k, v in x.items() if k != 't'},
                              proposed={k: v for k, v in y.items() if k != 't'}) for x, y in zip(a, b)]
    source = ('VTA 2024 counts' if name == 'stevens_creek' else 'synthetic hidden-world demand; VTA 2024 is project motivation, not this demand')
    role = 'heldout' if cfg['role'] == 'heldout' else 'practice'
    measurement = f'held-out simulation seed {seed}' if role == 'heldout' else f'development-road measurement, seed {seed}; not held-out-road evaluation'
    out = dict(road=name, role=role, name=cfg['street'], window=f"{cfg['begin']}-{cfg['end']}", seeds=[seed],
               source=f'SUMO; {source}; {measurement}; baseline is modeled stale timing, not verified city timing. Headline: all-requested delay score (900 s unfinished/teleport charge). Approach: incoming-edge time loss/visit; queue: stopped vehicles each second; AoG/PCD: first entry within 5 m of stop bar. Split failures: queue at both green and yellow onset, through movements (any movement if no through link). Green timings: configured maxima; distance: projected first-to-last signal span. Stops: completed-trip mean waitingCount. Travel: complete mainline end-to-end traversals, actual entry-time bins, excluding teleports; direction keys follow road axis. Emissions: '+', '.join(sides['baseline']['emission_classes'])+' default model, probability 1; cohort totals including inserted unfinished trips, CO2 mg to kg, volumetric fuel ml to L; uninserted trips emit zero.',
               status='pending_review' if decision == 'change' else 'keep_current',
               corridor=dict(length_m=round(max(positions[s] for s in coords), 2), **{a: s['headline'] for a, s in sides.items()},
                             by15=merge(sides['baseline']['by15'], sides['proposed']['by15'])), signals=[],
               time_space={a: s['time_space'] for a, s in sides.items()} | dict(window_s=list(WINDOW)))
    timings = {a: timing(path, cfg, net) for a, path in plans.items()}
    for signal in cfg['signals']:
        sid = signal['sumo_tls_id']
        keys = [k for k in sides['baseline']['approaches'] if k[0] == sid]
        main = [k for k in keys if k[1] in (('NB', 'SB') if axis else ('EB', 'WB'))]
        chosen = max(main, key=lambda k: sides['baseline']['approaches'][k]['volume_vph']) if main else None
        out['signals'].append(dict(id=sid, name=signal['name'], x_m=positions[sid], timing={a: ts[sid] for a, ts in timings.items()},
            approaches=[dict(approach=k[1], **{a: s['approaches'][k] for a, s in sides.items()},
                             by15=merge(sides['baseline']['approach_by15'][k], sides['proposed']['approach_by15'][k])) for k in keys],
            by15=merge(sides['baseline']['signal_by15'][sid], sides['proposed']['signal_by15'][sid]),
            pcd=dict(approach=chosen[1] if chosen else None, **{a: dict(arrivals=sample(s['pcd_points'][chosen], 3000),
                green=s['pcd_bands'][chosen], cycle_starts=s['cycle_starts'][sid]) for a, s in sides.items()})))
    encoded = json.dumps(out, separators=(',', ':'), allow_nan=False)+'\n'
    assert len(encoded.encode()) < 1_500_000
    target = ROOT/'dashboard/console/data'/name/'metrics.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.with_suffix('.tmp').write_text(encoded)
    target.with_suffix('.tmp').replace(target)
    print(json.dumps({a: s['headline'] for a, s in sides.items()}), flush=True)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('roads', nargs='*', default=['wolfe', 'deanza', 'homestead', 'stevens_creek'])
    args = parser.parse_args()
    start = time.monotonic()
    for name in args.roads:
        pipeline.check_battery()
        export(name)
    print(f'Wall time: {time.monotonic()-start:.1f} s', flush=True)


if __name__ == '__main__':
    main()
