"""Frozen-plan evaluation: paired seeds, scheduled departure cohorts, no tuning."""
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET

from scipy.stats import wilcoxon

from . import pipeline as p
from .demand import network, seconds, summary_stats

SEEDS = range(13, 33)  # Preregistered final test; never used for selection.
CONTROLLERS = ('actuated', 'optuna')  # Illustration pair retained for existing media consumers.
EVAL_CONTROLLERS = ('actuated', 'optuna_v1', 'optuna')
TEST_METRICS = ('mean_time_loss_s', 'all_vehicle_delay_s',
                'all_vehicle_delay_zero_unfinished_s', 'all_requested_delay_s',
                'all_requested_delay_0_s', 'all_requested_delay_1800_s',
                'side_all_requested_delay_s', 'side_time_loss_s', 'unfinished',
                'teleports', 'mainline_travel_eb_s', 'mainline_travel_wb_s')


def mean(values):
    return sum(values)/len(values) if values else ''


def boundaries(cfg):
    """Outer approach entry to far-side departure-edge exit, including both signals."""
    net = network()
    ends = []
    for signal in (cfg['signals'][0], cfg['signals'][-1]):
        directions = {}
        for a, b, _ in net.getTLS(signal['sumo_tls_id']).getConnections():
            if (a.getEdge().getID() in cfg['mainline_edges']
                    and b.getEdge().getID() in cfg['mainline_edges']
                    and any(c.getToLane() == b and c.getDirection() == 's' for c in a.getOutgoing())):
                direction = 'eb' if b.getEdge().getToNode().getCoord()[0] > a.getEdge().getFromNode().getCoord()[0] else 'wb'
                pair = a.getEdge().getID(), b.getEdge().getID()
                if direction in directions and directions[direction] != pair:
                    raise ValueError('Ambiguous corridor boundary')
                directions[direction] = pair
        ends.append(directions)
    return {'eb': (ends[1]['eb'][0], ends[0]['eb'][1]),
            'wb': (ends[0]['wb'][0], ends[1]['wb'][1])}


def corridor_times(path, endpoints, mainline, teleported):
    times = {}
    for _, vehicle in ET.iterparse(path):
        if vehicle.tag != 'vehicle':
            continue
        vid = vehicle.get('id')
        route = vehicle.find('route')
        if vid not in teleported and route is not None:
            edges = route.get('edges').split()
            exits = list(map(float, route.get('exitTimes').split()))
            if len(edges) != len(exits):
                raise ValueError('Route exit times do not align with edges')
            for direction, (first, last) in endpoints.items():
                if first not in edges or last not in edges:
                    continue
                a, b = edges.index(first), edges.index(last)
                if a > b or not all(e in mainline for e in edges[a:b+1]):
                    continue
                entry = exits[a-1] if a else float(vehicle.get('depart'))
                if entry >= 0 and exits[b] >= entry:
                    times[vid] = direction, exits[b]-entry
        vehicle.clear()
    return times


def metrics(requested, trips, travels, teleports, begin, end):
    cohort = {vid: side for vid, (depart, side) in requested.items() if begin <= depart < end}
    completed = {vid: t for vid, t in trips.items() if vid in cohort and float(t['arrival']) >= 0}
    if not completed:
        raise ValueError('No completed evaluation vehicles')
    directions = {d: [duration for vid, (direction, duration) in travels.items()
                      if vid in cohort and direction == d] for d in ('eb', 'wb')}
    unfinished = len(cohort)-len(completed)
    teleport_events = sum(vid in cohort for vid in teleports)
    # M5 charges one drain window per unfinished vehicle and teleport event.
    observed = sum(float(t['timeLoss'])+float(t['departDelay']) for t in completed.values())
    lower = (observed+1800*teleport_events)/len(cohort)
    side_ids = {vid for vid, side in cohort.items() if side}
    side_completed = side_ids & completed.keys()
    side_observed = sum(float(completed[v]['timeLoss'])+float(completed[v]['departDelay']) for v in side_completed)
    side_unfinished = len(side_ids)-len(side_completed)
    side_teleports = sum(v in side_ids for v in teleports)
    extra = {f'all_requested_delay{suffix}_s': (observed+charge*(unfinished+teleport_events))/len(cohort)
             for suffix, charge in (('_0', 0), ('', 900), ('_1800', 1800))}
    extra.update(side_requested=len(side_ids), side_unfinished=side_unfinished, side_teleports=side_teleports,
                 side_all_requested_delay_s=(side_observed+900*(side_unfinished+side_teleports))/len(side_ids) if side_ids else '')
    return dict(all_vehicle_delay_s=lower+1800*unfinished/len(cohort),
                all_vehicle_delay_zero_unfinished_s=lower,
                requested=len(cohort), completed=len(completed), unfinished=len(cohort)-len(completed),
                mean_time_loss_s=mean([float(t['timeLoss']) for t in completed.values()]),
                mean_waiting_count=mean([float(t['waitingCount']) for t in completed.values()]),
                mainline_travel_s=mean(directions['eb']+directions['wb']),
                side_time_loss_s=mean([float(t['timeLoss']) for vid, t in completed.items() if cohort[vid]]),
                teleports=sum(vid in cohort for vid in teleports),
                teleported_vehicles=len(set(teleports) & cohort.keys()),
                mean_depart_delay_s=mean([float(t['departDelay']) for t in completed.values()]),
                mainline_travel_eb_s=mean(directions['eb']), mainline_travel_wb_s=mean(directions['wb']),
                mainline_eb_n=len(directions['eb']), mainline_wb_n=len(directions['wb']), **extra)


def command(scenario, controller, seed, cfg):
    period = cfg['scenarios'][scenario]
    return [p.BIN/'sumo', '-c', p.ROOT/'sim/corridor.sumocfg',
            '-r', p.ROOT/f'sim/routes_{scenario}.rou.xml',
            '-a', f'{p.ROOT}/sim/detectors.add.xml,{p.ROOT}/sim/tls_{controller}_{scenario}.add.xml',
            '-b', seconds(period['begin'])-cfg['warmup_s'], '--seed', seed,
            '--time-to-teleport', cfg['time_to_teleport'], '--no-step-log', '--aggregate-warnings', -1]


def simulate(scenario, controller, seed, cfg, endpoints):
    period = cfg['scenarios'][scenario]
    begin, end = seconds(period['begin']), seconds(period['end'])
    requested = {}
    for v in ET.parse(p.ROOT/f'sim/routes_{scenario}.rou.xml').getroot().findall('vehicle'):
        edges = v.find('route').get('edges').split()
        approach = next(e for e in edges if e in cfg['mainline_edges'] or e in cfg['side_edges'])
        requested[v.get('id')] = float(v.get('depart')), approach in cfg['side_edges']
    with tempfile.TemporaryDirectory() as folder:
        folder = Path(folder)
        p.run([*command(scenario, controller, seed, cfg), '-e', end+1800,
               '--summary-output', folder/'summary.xml', '--tripinfo-output', folder/'trips.xml',
               '--tripinfo-output.write-unfinished', 'true', '--vehroute-output', folder/'routes.xml',
               '--vehroute-output.exit-times', 'true', '--vehroute-output.write-unfinished', 'true',
               '--error-log', folder/'warnings.txt'])
        teleports = re.findall(r"Teleporting vehicle '([^']+)'", (folder/'warnings.txt').read_text())
        total = summary_stats(folder/'summary.xml')['teleports']
        if total != len(teleports):
            raise ValueError(f'Teleport warning/summary mismatch: {len(teleports)} != {total}')
        trips = {t.get('id'): dict(t.attrib) for t in ET.parse(folder/'trips.xml').getroot().findall('tripinfo')}
        travels = corridor_times(folder/'routes.xml', endpoints, set(cfg['mainline_edges']), set(teleports))
    windows = [('full', begin, end)]
    if 'holdout' in period:
        windows.append(('holdout', *map(seconds, period['holdout'])))
    return [dict(controller=controller, scenario=scenario, seed=seed, window=window,
                 seed_group='fit_used' if seed in cfg['seeds'] else 'out_of_sample',
                 begin_s=a, end_s=b, **metrics(requested, trips, travels, teleports, a, b),
                 run_teleports_including_warmup=total) for window, a, b in windows]


def constraint_check(stats, baseline):
    return stats['side_all_requested_delay_s'] <= 1.05*baseline['side_all_requested_delay_s']+1e-9


def paired_tests(rows):
    results = []
    candidates = [c for c in EVAL_CONTROLLERS if c != 'actuated' and any(r['controller'] == c for r in rows)]
    for scenario, window in sorted({(r['scenario'], r['window']) for r in rows}):
        for group in ('all', 'out_of_sample'):
            for candidate in candidates:
                comparison = {c: [r['side_all_requested_delay_s'] for r in rows
                                  if r['scenario'] == scenario and r['window'] == window and r['controller'] == c
                                  and (group == 'all' or r['seed_group'] == group)] for c in ('actuated', candidate)}
                side_ratio = mean(comparison[candidate])/mean(comparison['actuated'])
                for metric in TEST_METRICS:
                    paired = {c: {r['seed']: r[metric] for r in rows
                                  if r['scenario'] == scenario and r['window'] == window and r['controller'] == c
                                  and (group == 'all' or r['seed_group'] == group)} for c in ('actuated', candidate)}
                    if paired['actuated'].keys() != paired[candidate].keys():
                        raise ValueError('Unpaired evaluation seeds')
                    seeds = sorted(paired['actuated'])
                    diffs = [paired[candidate][s]-paired['actuated'][s] for s in seeds]
                    test = wilcoxon(diffs, alternative='less', method='auto') if any(diffs) else None
                    results.append(dict(scenario=scenario, window=window, seed_group=group, metric=metric, n=len(seeds),
                                        actuated_mean=mean(list(paired['actuated'].values())),
                                        optuna_mean=mean(list(paired[candidate].values())),
                                        statistic=float(test.statistic) if test else 0.,
                                        p_value=float(test.pvalue) if test else 1., alternative='optuna_less',
                                        method='auto', zero_method='wilcox', controller=candidate,
                                        side_constraint_ratio=side_ratio, side_constraint_met=side_ratio <= 1.05+1e-9))
    return results


def save_fcd(cfg):
    paths = []
    begin, end = map(seconds, ('17:30', '17:45'))
    for controller in CONTROLLERS:
        path = p.ROOT/f'reports/fcd_{controller}_pm_peak_seed13.xml.gz'
        p.run([*command('pm_peak', controller, 13, cfg), '-e', end,
               '--fcd-output', path, '--device.fcd.begin', begin, '--device.fcd.period', 1])
        steps = 0
        with gzip.open(path, 'rb') as stream:
            for _, element in ET.iterparse(stream):
                if element.tag == 'timestep':
                    assert begin <= float(element.get('time')) < end
                    steps += 1
                    element.clear()
        if steps != 900 or path.stat().st_size >= 100_000_000:
            raise ValueError('FCD must contain 900 steps and the pair must stay below 200 MB')
        paths.append(dict(path=str(path.relative_to(p.ROOT)), bytes=path.stat().st_size,
                          begin_s=begin, end_s=end, steps=steps, sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    return paths


def eval():
    start = time.monotonic()
    power = subprocess.check_output(['pmset', '-g', 'batt'], text=True).strip()
    print(power, flush=True)
    cfg = p.config()
    endpoints = boundaries(cfg)
    rows = []
    for scenario in cfg['scenarios']:
        for seed in SEEDS:
            for controller in EVAL_CONTROLLERS:
                rows.extend(simulate(scenario, controller, seed, cfg, endpoints))
            print(f'eval: {scenario} seed {seed} complete (serial, nice 15)', flush=True)
    for row in rows:
        baseline = next(r for r in rows if r['controller'] == 'actuated' and all(r[k] == row[k] for k in ('scenario', 'window', 'seed')))
        row['side_constraint_met'] = constraint_check(row, baseline)
        row['side_constraint_ratio'] = row['side_all_requested_delay_s']/baseline['side_all_requested_delay_s']
    p.write_csv('reports/results.csv', rows)
    p.write_csv('reports/wilcoxon.csv', paired_tests(rows))
    fcd = save_fcd(cfg)
    files = ['config/corridor.yaml', 'sim/corridor.net.xml']
    files += [f'sim/{kind}_{scenario}{suffix}' for scenario in cfg['scenarios']
              for kind, suffix in [('routes', '.rou.xml'), ('tls_actuated', '.add.xml'), ('tls_optuna', '.add.xml'), ('tls_optuna_v1', '.add.xml')]]
    provenance = dict(seeds=list(SEEDS), fit_used_seeds=cfg['seeds'], workers=1, power=power,
                      time_to_teleport=cfg['time_to_teleport'], warmup_s=cfg['warmup_s'], drain_s=1800,
                      corridor_boundaries=endpoints, fcd=fcd, wall_s=time.monotonic()-start,
                      sha256={f: hashlib.sha256((p.ROOT/f).read_bytes()).hexdigest() for f in files})
    (p.ROOT/'reports/eval.json').write_text(json.dumps(provenance, indent=2)+'\n')
    print(f'eval finished in {provenance["wall_s"]:.1f} s', flush=True)
