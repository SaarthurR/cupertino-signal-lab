"""Historical turn counts → sampled routes, then an independent holdout check."""
import copy
from collections import Counter, defaultdict
import csv
import hashlib
import math
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET

from . import pipeline as p


def seconds(clock):
    hour, minute = map(int, clock.split(':'))
    return hour * 3600 + minute * 60


def load_counts():
    with open(p.ROOT / 'data/processed/tmc.csv') as stream:
        rows = list(csv.DictReader(stream))
    seen = set()
    names = {s['name'] for s in p.config()['signals']}
    for row in rows:
        key = tuple(row[k] for k in ('intersection', 'approach', 'movement', 'interval_start'))
        if key in seen:
            raise ValueError(f'Duplicate count: {key}')
        seen.add(key)
        if row['intersection'] not in names or row['approach'] not in ('N', 'S', 'E', 'W') or row['movement'] not in ('L', 'T', 'R'):
            raise ValueError(f'Invalid movement: {row}')
        if row['source'] not in ('measured', 'estimated') or int(row['vehicles']) < 0:
            raise ValueError(f'Invalid count/source: {row}')
        if seconds(row['interval_start']) % 900:
            raise ValueError(f'Count is not on a 15-minute boundary: {row}')
    return rows


def network():
    return p.sumolib.net.readNet(str(p.ROOT / 'sim/corridor.net.xml'))


def movement_map(net):
    """Approach is the originating compass leg: N means southbound traffic."""
    mapping = {}
    for signal in p.config()['signals']:
        for lane, outgoing, _ in net.getTLS(signal['sumo_tls_id']).getConnections():
            edge = lane.getEdge()
            x0, y0 = edge.getFromNode().getCoord()
            x1, y1 = edge.getToNode().getCoord()
            dx, dy = x0-x1, y0-y1
            approach = ('E' if dx > 0 else 'W') if abs(dx) > abs(dy) else ('N' if dy > 0 else 'S')
            for connection in lane.getOutgoing():
                if connection.getToLane() != outgoing or connection.getDirection() not in ('l', 's', 'r'):
                    continue
                if not lane.allows('passenger') or not outgoing.allows('passenger'):
                    continue
                movement = {'l': 'L', 's': 'T', 'r': 'R'}[connection.getDirection()]
                key = signal['name'], approach, movement
                pair = edge.getID(), outgoing.getEdge().getID()
                if key in mapping and mapping[key] != pair:
                    raise ValueError(f'Ambiguous movement mapping: {key}')
                mapping[key] = pair
    return mapping


def mapped_counts(rows, mapping):
    counts = defaultdict(Counter)
    for row in rows:
        key = tuple(row[k] for k in ('intersection', 'approach', 'movement'))
        if key not in mapping:
            raise ValueError(f'Count has no legal SUMO connection: {key}; rebuild the network')
        counts[seconds(row['interval_start'])][mapping[key]] += int(row['vehicles'])
    return counts


def turn_file(counts, path, duration=900):
    root = ET.Element('data')
    for begin, movements in sorted(counts.items()):
        interval = ET.SubElement(root, 'interval', begin=str(begin), end=str(begin+duration))
        for (incoming, outgoing), count in sorted(movements.items()):
            ET.SubElement(interval, 'edgeRelation', attrib={'from': incoming, 'to': outgoing, 'count': str(count)})
    p.xml_write(root, path)


def candidate_routes(net, mapping, path):
    edges = [e for e in net.getEdges() if e.allows('passenger')]
    # SUMO adds U-turns at clipped road ends; these are still demand boundaries.
    origins = [e for e in edges if not any(v.allows('passenger') and any(c.getDirection() != 't' for c in cs)
                                           for v, cs in e.getIncoming().items())]
    destinations = [e for e in edges if not any(v.allows('passenger') and any(c.getDirection() != 't' for c in cs)
                                                for v, cs in e.getOutgoing().items())]
    routes = set()
    for incoming, outgoing in sorted(set(mapping.values())):
        first, last = net.getEdge(incoming), net.getEdge(outgoing)
        prefixes = [net.getShortestPath(start, first, vClass='passenger')[0] for start in origins]
        suffixes = [net.getShortestPath(last, end, vClass='passenger')[0] for end in destinations]
        for prefix in prefixes:
            for suffix in suffixes:
                if prefix is None or suffix is None:
                    continue
                path_edges = (*prefix, *suffix)
                route = tuple(e.getID() for e in path_edges)
                # L/T/R counts do not constrain U-turns; exclude artificial turnaround demand.
                reverses = any(all(c.getDirection() == 't' for c in a.getOutgoing()[b])
                               for a, b in zip(path_edges, path_edges[1:]))
                if len(set(route)) == len(route) and not reverses:
                    routes.add(route)
        if not any((incoming, outgoing) in zip(r, r[1:]) for r in routes):
            raise ValueError(f'No boundary-to-boundary route covers {incoming} → {outgoing}')
    root = ET.Element('routes')
    for i, route in enumerate(sorted(routes)):
        ET.SubElement(root, 'route', id=f'candidate_{i}', edges=' '.join(route))
    p.xml_write(root, path)
    return len(routes)


def sample(candidates, turns, output):
    log = p.tool('routeSampler.py', '-r', candidates, '-t', turns, '-o', output,
                 '--optimize', 'full', '--seed', '0', '--attributes', 'departLane="best" departSpeed="max"')
    return log


def extend_fit(sampled, output, fit_begin, fit_end, end, warmup):
    """Repeat only the fit hour. Never read holdout counts when generating vehicles."""
    root = ET.Element('routes')
    vehicles = []
    for vehicle in ET.parse(sampled).getroot().findall('vehicle'):
        depart = float(vehicle.get('depart'))
        shift = -warmup
        # Warmup reuses the first fit interval; subsequent hours replay the whole fit window.
        if depart < fit_begin + warmup:
            v = copy.deepcopy(vehicle)
            v.set('depart', str(depart+shift))
            vehicles.append(v)
        for shift in range(0, end-fit_begin, fit_end-fit_begin):
            if depart+shift < end:
                v = copy.deepcopy(vehicle)
                v.set('depart', str(depart+shift))
                vehicles.append(v)
    for i, vehicle in enumerate(sorted(vehicles, key=lambda v: float(v.get('depart')))):
        vehicle.set('id', f'demand_{i}')
        root.append(vehicle)
    p.xml_write(root, output)
    return len(vehicles)


def simulation(scenario, folder, *, routes=None, additional=None):
    cfg = p.config()
    scenario_cfg = cfg['scenarios'][scenario]
    begin, end = seconds(scenario_cfg['begin']), seconds(scenario_cfg['end'])
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    summary = folder / 'summary.xml'
    args = [p.BIN/'sumo', '-c', p.ROOT/'sim/corridor.sumocfg', '-r',
            routes or p.ROOT/f'sim/routes_{scenario}.rou.xml', '--begin', begin-cfg['warmup_s'],
            '--end', end+1800, '--seed', '0', '--no-step-log', '--duration-log.statistics',
            '--summary-output', summary]
    additions = [p.ROOT/'sim/detectors.add.xml']
    baseline = p.ROOT/f'sim/tls_actuated_{scenario}.add.xml'
    if baseline.exists():
        additions.append(baseline)
    if additional:
        additions.append(additional)
    trips = folder/'tripinfo.xml'
    args.extend(['--additional-files', ','.join(map(str, additions)), '--tripinfo-output', trips])
    log = p.run(args)
    losses = [float(t.get('timeLoss')) for _, t in ET.iterparse(trips)
              if t.tag == 'tripinfo' and begin <= float(t.get('depart')) < end]
    return {**summary_stats(summary), 'mean_time_loss_s': sum(losses)/len(losses) if losses else None,
            'completed_after_warmup': len(losses), 'log': log}


def summary_stats(path):
    final = None
    for _, element in ET.iterparse(path):
        if element.tag == 'step':
            final = dict(element.attrib)
        element.clear()
    if final is None:
        raise ValueError('SUMO produced no summary')
    # SUMO summary counters, including teleports, are cumulative.
    return {key: int(final[key]) for key in ('teleports', 'inserted', 'running', 'waiting')}


def build_demand():
    cfg = p.config()
    net = network()
    mapping = movement_map(net)
    rows = load_counts()
    pm = cfg['scenarios']['pm_peak']
    fit_begin, fit_end = map(seconds, pm['fit'])
    fit = [r for r in rows if fit_begin <= seconds(r['interval_start']) < fit_end]
    if not fit or len({r['interval_start'] for r in fit}) != (fit_end-fit_begin)//900:
        raise ValueError('Fit window must contain all 15-minute intervals')
    counts = mapped_counts(fit, mapping)
    if any(set(values) != set(mapping.values()) for values in counts.values()):
        raise ValueError('Every modeled movement needs a count in every fit interval')
    turn_file(counts, 'data/processed/turns_pm_peak.xml')
    candidates = p.ROOT / 'data/processed/candidate_routes.rou.xml'
    n_candidates = candidate_routes(net, mapping, candidates)
    logs = []
    with tempfile.TemporaryDirectory() as temp:
        sampled = Path(temp)/'pm_fit.rou.xml'
        logs.append(sample(candidates, p.ROOT/'data/processed/turns_pm_peak.xml', sampled))
        total_pm = extend_fit(sampled, 'sim/routes_pm_peak.rou.xml', fit_begin, fit_end,
                              seconds(pm['end']), cfg['warmup_s'])
        # Night is a disclosed estimate: 10% of fit-hour mainline-origin movements; 2 veh/h per side turn.
        night_begin = seconds(cfg['scenarios']['night']['begin'])
        hourly = Counter()
        for values in counts.values():
            hourly.update(values)
        flows = []
        night_counts = {}
        for key, pair in sorted(mapping.items()):
            rate = hourly[pair] * 3600/(fit_end-fit_begin) * .1 if key[1] in ('E', 'W') else 2
            flows.append(dict(begin_s=night_begin, end_s=seconds(cfg['scenarios']['night']['end']),
                              from_edge=pair[0], to_edge=pair[1], veh_per_hour=round(rate, 3), source='estimated'))
            night_counts[pair] = round(rate)
        p.write_csv('data/processed/flows_night.csv', flows)
        turn_file({night_begin: night_counts}, 'data/processed/turns_night.xml', 3600)
        night_sampled = Path(temp)/'night.rou.xml'
        logs.append(sample(candidates, p.ROOT/'data/processed/turns_night.xml', night_sampled))
        total_night = extend_fit(night_sampled, 'sim/routes_night.rou.xml', night_begin, night_begin+3600,
                                 seconds(cfg['scenarios']['night']['end']), cfg['warmup_s'])
        stats = {s: simulation(s, Path(temp)/s) for s in ('pm_peak', 'night')}
    if stats['night']['teleports']:
        raise ValueError(f'Night must have zero teleports: {stats["night"]["teleports"]}')
    fit_hash = hashlib.sha256(repr(sorted(tuple(sorted(r.items())) for r in fit)).encode()).hexdigest()
    report = ['# M2 demand build', '', f'{n_candidates} boundary-to-boundary candidate routes; routeSampler --optimize full, seed 0.',
              f'Vehicles including 900 s warmup: PM {total_pm}; night {total_night}.',
              f'Fit-only input SHA256: `{fit_hash}`.', '',
              'PM fit is 16:30–17:30. The fit hour is replayed at 17:30–18:30 without reading holdout volumes; warmup replays its first 15 minutes. All scenarios have a 30-minute drain period.',
              'Night: mainline-origin movements at 10% of the PM fit-hour volume, each side-origin turn 2 veh/h. All night demand is estimated.',
              'Vehicle types are homogeneous passenger cars: measured totals include buses/trucks; quarter-hour per-movement heavy splits are unavailable. Pedestrians are recorded but not simulated.',
              'Simulation uses the retained textbook coordinated-actuated baseline files; timing is unchanged by this demand rebuild.', '',
              '| Scenario | Inserted | Running after drain | Waiting to insert | Teleports |', '|---|---:|---:|---:|---:|']
    for name, stat in stats.items():
        report.append(f'| {name} | {stat["inserted"]} | {stat["running"]} | {stat["waiting"]} | {stat["teleports"]} |')
    report.extend(['', '## SUMO and routeSampler output', '', '```', *logs, *(s['log'] for s in stats.values()), '```'])
    (p.ROOT/'reports/M2-REPORT.md').write_text('\n'.join(report)+'\n')
    print(f'build-demand: PM {total_pm}, night {total_night}; night teleports 0')


def geh(observed, simulated, interval_s=900):
    if observed < 0 or simulated < 0 or interval_s <= 0:
        raise ValueError('GEH requires nonnegative counts and a positive interval')
    observed, simulated = observed*3600/interval_s, simulated*3600/interval_s
    return math.sqrt(2*(simulated-observed)**2/(simulated+observed)) if simulated+observed else 0.0


def turn_detectors(net, mapping, folder):
    """Count physical entries to internal turn lanes, so teleported jumps are not crossings."""
    root = ET.Element('additional')
    ids = {}
    lanes = set()
    wanted = set(mapping.values())
    for signal in p.config()['signals']:
        for lane, outgoing, _ in net.getTLS(signal['sumo_tls_id']).getConnections():
            pair = lane.getEdge().getID(), outgoing.getEdge().getID()
            if pair not in wanted:
                continue
            for connection in lane.getOutgoing():
                if connection.getToLane() != outgoing:
                    continue
                via = connection.getViaLaneID()
                if via in lanes:
                    continue
                lanes.add(via)
                detector_id = f'turn_{len(ids)}'
                ids[detector_id] = pair
                ET.SubElement(root, 'inductionLoop', id=detector_id, lane=via, pos='0.1',
                              period='900', file=str(Path(folder)/'turn_counts.xml'))
    if set(ids.values()) != wanted:
        raise ValueError('Missing turn detectors')
    path = Path(folder)/'turn_detectors.add.xml'
    p.xml_write(root, path)
    return path, ids


def detector_counts(path, ids, begin, end):
    counts = Counter()
    for _, interval in ET.iterparse(path):
        if interval.tag == 'interval':
            time = float(interval.get('begin'))
            if begin <= time < end:
                pair = ids[interval.get('id')]
                counts[(int(time), *pair)] += int(interval.get('nVehEntered'))
        interval.clear()
    return counts


def check_demand():
    from .baseline import LABEL
    if not (p.ROOT/'sim/tls_actuated_pm_peak.add.xml').exists():
        raise ValueError('Run baseline before check-demand')
    pm = p.config()['scenarios']['pm_peak']
    begin, end = map(seconds, pm['holdout'])
    net = network()
    mapping = movement_map(net)
    holdout = [r for r in load_counts() if r['source'] == 'measured' and begin <= seconds(r['interval_start']) < end]
    if not holdout:
        raise ValueError('No measured holdout counts')
    with tempfile.TemporaryDirectory() as temp:
        detectors, ids = turn_detectors(net, mapping, temp)
        stat = simulation('pm_peak', temp, additional=detectors)
        actual = detector_counts(Path(temp)/'turn_counts.xml', ids, begin, end)
    results = []
    for row in holdout:
        key = row['intersection'], row['approach'], row['movement']
        pair = mapping[key]
        simulated = actual[(seconds(row['interval_start']), *pair)]
        observed = int(row['vehicles'])
        results.append(dict(movement=' / '.join(key), interval=row['interval_start'], observed=observed,
                            simulated=simulated, geh=round(geh(observed, simulated), 4)))
    p.write_csv('reports/demand_check.csv', results)
    percentage = 100*sum(r['geh'] < 5 for r in results)/len(results)
    lines = ['# M3 independent holdout count check', '', f'**{percentage:.2f}% of {len(results)} measured movement-intervals have GEH < 5** (target 85%; reported, not a gate).', '',
             'Observed = 2024-10-09 measured De Anza/Stelling 17:30–18:30 sheets; simulated = physical detector entries at the start of each internal turn lane in that same clock interval. Counts converted to hourly rates before GEH.',
             'Fit uses only 16:30–17:30; replay supplies holdout demand. Estimated intersections are excluded from this score. This is a count-matching check, not validation of travel time or current Cupertino traffic.',
             f'{LABEL} used. PM teleports: {stat["teleports"]}; running after drain: {stat["running"]}; waiting to insert: {stat["waiting"]}. Teleports and incomplete trips limit interpretation.',
             'A miss can reflect the repeated fit hour, mixed-year Mary observations, assumed side-street demand, OSM geometry/connectivity, or queues under the baseline timing; this run does not isolate those causes.', '',
             '| movement | interval | observed | simulated | geh |', '|---|---|---:|---:|---:|']
    lines.extend('| '+' | '.join(str(r[k]) for k in r)+' |' for r in results)
    (p.ROOT/'reports/demand_check.md').write_text('\n'.join(lines)+'\n')
    (p.ROOT/'reports/M3-REPORT.md').write_text('\n'.join(lines[:8])+'\n\nDetailed rows: demand_check.csv / demand_check.md. Raw detector/summary XML removed after extraction.\n')
    print(f'check-demand: {percentage:.2f}% GEH < 5 ({len(results)} measured holdout rows); target 85% is not a gate')
