"""Labeled synthetic PM demand and simulated five-minute approach counts."""
from collections import Counter, defaultdict
import copy
from datetime import datetime, timedelta
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

from . import demand as d, evaluate, pipeline as p

SCENARIOS = ('calm', 'south_surge', 'east_surge', 'drop', 'sensor_failure')
CHANGE_START = d.seconds('17:00')
CHANGE_END = CHANGE_START + 1800
FAILURE_END = CHANGE_START + 1200
ENTRIES = {'south_surge': '754815172', 'east_surge': '526011476'}
# Synthetic clock only; no claim that these are observations on this date.
CLOCK = datetime.fromisoformat('2026-10-31T00:00:00-07:00')


def scenario_routes(scenario, output):
    if scenario not in SCENARIOS:
        raise ValueError(f'Unknown scenario: {scenario}')
    source = p.ROOT/'sim/routes_pm_peak.rou.xml'
    if scenario in ('calm', 'sensor_failure'):
        shutil.copyfile(source, output)
        return
    root = ET.parse(source).getroot()
    groups = defaultdict(list)
    for vehicle in root.findall('vehicle'):
        origin = vehicle.find('route').get('edges').split()[0]
        if CHANGE_START <= float(vehicle.get('depart')) < CHANGE_END:
            if scenario == 'drop' or origin == ENTRIES[scenario]:
                groups[origin].append(vehicle)
    extra = 0
    for vehicles in groups.values():
        fraction = .4 if scenario == 'south_surge' else .3
        n = round(len(vehicles)*fraction)
        for i in range(n):
            vehicle = vehicles[int((i+.5)*len(vehicles)/n)]
            if scenario == 'drop':
                root.remove(vehicle)
            else:
                clone = copy.deepcopy(vehicle)
                clone.set('id', f'{scenario}_{extra}')
                root.append(clone)
                extra += 1
    vehicles = sorted(root.findall('vehicle'), key=lambda v: float(v.get('depart')))
    for vehicle in root.findall('vehicle'):
        root.remove(vehicle)
    root.extend(vehicles)
    p.xml_write(root, output)


def feed_detectors(folder):
    """Copy only stop-line loops; upstream loops would double-count vehicles."""
    net = d.network()
    mapping = d.movement_map(net)
    edges = {}
    for (site, approach, _), (incoming, _) in mapping.items():
        key = site, approach
        if incoming in edges and edges[incoming] != key:
            raise ValueError(f'Ambiguous approach: {incoming}')
        edges[incoming] = key
    root = ET.Element('additional')
    ids, unmapped = {}, []
    for detector in ET.parse(p.ROOT/'sim/detectors.add.xml').getroot():
        edge = net.getLane(detector.get('lane')).getEdge().getID()
        if edge not in edges:
            unmapped.append(detector.get('id'))
            continue
        if not detector.get('id').startswith('stop_'):
            continue
        detector.set('freq', '300')
        detector.set('file', str(Path(folder)/'counts.xml'))
        root.append(detector)
        ids[detector.get('id')] = edges[edge]
    path = Path(folder)/'detectors.add.xml'
    p.xml_write(root, path)
    return path, ids, unmapped


def feed_rows(path, ids, begin, end, sensor_failure=False):
    counts = Counter()
    seen = set()
    for interval in ET.parse(path).getroot().findall('interval'):
        a, b = float(interval.get('begin')), float(interval.get('end'))
        if a < begin or b > end:
            continue
        if b-a != 300 or a % 300:
            raise ValueError('Feed requires aligned five-minute detector windows')
        key = int(b), interval.get('id')
        if key in seen or key[1] not in ids:
            raise ValueError(f'Duplicate or unknown detector interval: {key}')
        seen.add(key)
        counts[(int(b), *ids[key[1]])] += int(interval.get('nVehEntered'))
    expected = {(t, detector) for t in range(begin+300, end+1, 300) for detector in ids}
    if seen != expected:
        raise ValueError('Missing detector windows; cannot label missing data ok=1')
    return [dict(window_end=(CLOCK+timedelta(seconds=t)).isoformat(), site=site,
                 approach=approach, count=counts[t, site, approach],
                 ok=int(not (sensor_failure and (site, approach) == ('De Anza Blvd', 'N')
                             and CHANGE_START < t <= FAILURE_END)))
            for t in range(begin+300, end+1, 300) for site, approach in sorted(set(ids.values()))]


def insertion_counts(routes, trips):
    records = {t.get('id'): float(t.get('depart')) for t in ET.parse(trips).getroot().findall('tripinfo')}
    vehicles = ET.parse(routes).getroot().findall('vehicle')
    if records.keys() != {v.get('id') for v in vehicles}:
        raise ValueError('Trip output must include every requested vehicle, including undeparted')
    counts = defaultdict(Counter)
    for vehicle in vehicles:
        if not CHANGE_START <= float(vehicle.get('depart')) < CHANGE_END:
            continue
        origin = vehicle.find('route').get('edges').split()[0]
        counts[origin]['requested'] += 1
        depart = records[vehicle.get('id')]
        counts[origin]['entered_by_run_end'] += int(depart >= 0)
        counts[origin]['entered_during_change'] += int(CHANGE_START <= depart < CHANGE_END)
        if vehicle.get('id').startswith('south_surge_') or vehicle.get('id').startswith('east_surge_'):
            counts[origin]['added_requested'] += 1
            counts[origin]['added_entered_by_run_end'] += int(depart >= 0)
            counts[origin]['added_entered_during_change'] += int(CHANGE_START <= depart < CHANGE_END)
    return dict(counts)


def feed(scenario='calm', seed=0):
    if seed < 0:
        raise ValueError('Seed must be nonnegative')
    cfg = p.config()
    begin, end = map(d.seconds, (cfg['scenarios']['pm_peak']['begin'], cfg['scenarios']['pm_peak']['end']))
    folder = p.ROOT/f'reports/feed/{scenario}_seed{seed}'
    folder.mkdir(parents=True, exist_ok=True)
    routes = folder/'routes.rou.xml'
    scenario_routes(scenario, routes)
    detectors, ids, unmapped = feed_detectors(folder)
    args = evaluate.command('pm_peak', 'optuna_v5', seed, cfg)
    args[args.index('-r')+1] = routes
    args[args.index('-a')+1] = f'{detectors},{p.ROOT}/sim/tls_optuna_v5_pm_peak.add.xml'
    log = p.run([*args, '-e', end+1800, '--tripinfo-output', folder/'trips.xml',
                 '--tripinfo-output.write-unfinished', 'true', '--tripinfo-output.write-undeparted', 'true',
                 '--summary-output', folder/'summary.xml'])
    (folder/'sumo.log').write_text(log)
    rows = feed_rows(folder/'counts.xml', ids, begin, end, scenario == 'sensor_failure')
    p.write_csv(folder/'feed.csv', rows)
    metadata = dict(scenario=scenario, seed=seed, simulated_counts=True, controller='optuna_v5',
                    change_start_s=CHANGE_START, change_end_s=CHANGE_END, failure_end_s=FAILURE_END,
                    failure_approach=['De Anza Blvd', 'N'], unmapped_detectors=unmapped,
                    insertion_counts=insertion_counts(routes, folder/'trips.xml'),
                    run_summary=d.summary_stats(folder/'summary.xml'))
    (folder/'metadata.json').write_text(json.dumps(metadata, indent=2)+'\n')
    print(f'feed: {scenario} seed {seed}; {len(rows)} rows; unmapped detectors: {unmapped}')
    print(json.dumps(metadata['insertion_counts'], sort_keys=True))
