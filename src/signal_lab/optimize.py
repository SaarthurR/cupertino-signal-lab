"""Fit-only timing search; freeze the winning PM parameters for night too."""
from concurrent.futures import ProcessPoolExecutor
import csv
import json
import math
import re
from pathlib import Path
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET

import optuna

from . import pipeline as p
from .demand import seconds, summary_stats
from .evaluate import boundaries, corridor_times, metrics

TRAIN_SEEDS = range(5)
SELECTION_SEEDS = range(5, 13)
CONSTRAINT_METRICS = ('side_all_requested_delay_s', 'mainline_travel_eb_s', 'mainline_travel_wb_s')

def split_greens(cycle, split, rows, main, baseline_greens, baseline_cycle):
    """Scale Webster greens, using bounded phase shares and retaining nominal slack."""
    if not 80 <= cycle <= 150 or (not isinstance(split, list) and not .6 <= split <= 1.4):
        raise ValueError('Cycle/split outside M5 bounds')
    lower = [max(10., float(r['min_green_s'])+1) for r in rows]
    upper = [min(60., float(r['max_green_s'])) for r in rows]
    clearance = sum(float(r['yellow_s'])+float(r['red_clear_s']) for r in rows)
    available = cycle-clearance
    if available < sum(lower) or any(a > b for a, b in zip(lower, upper)):
        raise ValueError('Cycle cannot accommodate bounded greens and clearances')
    budget = max(sum(lower), sum(baseline_greens)*available/(baseline_cycle-clearance))
    multipliers = split if isinstance(split, list) else [split if i == main else 1. for i in range(len(rows))]
    if len(multipliers) != len(rows) or any(not .6 <= v <= 1.4 for v in multipliers):
        raise ValueError('Phase shares outside bounds')
    if cycle == baseline_cycle and all(m == 1 for m in multipliers):
        return baseline_greens[:]
    weights = [g*m for g, m in zip(baseline_greens, multipliers)]
    low, high = 0., budget/min(weights)
    for _ in range(60):
        scale = (low+high)/2
        if sum(min(hi, max(lo, w*scale)) for lo, hi, w in zip(lower, upper, weights)) < budget:
            low = scale
        else:
            high = scale
    greens = [min(hi, max(lo, w*low)) for lo, hi, w in zip(lower, upper, weights)]
    return greens


def baseline_params():
    logics = ET.parse(p.ROOT/'sim/tls_actuated_pm_peak.add.xml').getroot().findall('tlLogic')
    settings = {v.get('key'): float(v.get('value')) for v in logics[0].findall('param')
                if v.get('key') in ('cycleTime', 'max-gap')}
    params = dict(cycle_s=settings['cycleTime'])
    for index, logic in enumerate(logics):
        params[f'offset_{index}'] = float(logic.get('offset'))/params['cycle_s']
        params[f'passage_{index}'] = float(next(v.get('value') for v in logic.findall('param') if v.get('key') == 'max-gap'))
        for phase, row in enumerate(logic.findall('phase')):
            if row.get('minDur') is not None:
                params[f'share_{index}_{phase}'] = 1.
                if row.get('name') == 'mainline':
                    params[f'min_{index}'] = float(row.get('minDur'))
    return params


def v2_params():
    params = json.loads((p.ROOT/'reports/optimize.json').read_text())['best']['params']
    params.update({key: value for key, value in baseline_params().items() if key.startswith('min_')})
    return params


def plan(scenario, params, path):
    root = ET.parse(p.ROOT/f'sim/tls_actuated_{scenario}.add.xml').getroot()
    with open(p.ROOT/'data/processed/timing_inputs.csv') as stream:
        inputs = {(r['sumo_tls_id'], int(r['phase'])): r for r in csv.DictReader(stream)}
    timing = []
    cycle = params['cycle_s']
    for index, logic in enumerate(root.findall('tlLogic')):
        logic.set('programID', 'optuna_v3')
        offset = params[f'offset_{index}']*cycle
        logic.set('offset', str(offset))
        phases = logic.findall('phase')
        indices = [i for i, phase in enumerate(phases) if phase.get('minDur') is not None]
        rows = [inputs[logic.get('id'), i] for i in indices]
        main = next(j for j, i in enumerate(indices) if phases[i].get('name') == 'mainline')
        baseline_cycle = float(next(v.get('value') for v in logic.findall('param') if v.get('key') == 'cycleTime'))
        shares = [params[f'share_{index}_{i}'] for i in indices] if f'share_{index}_{indices[0]}' in params else params[f'split_{index}']
        passage = params.get(f'passage_{index}', params.get('passage_s'))
        greens = split_greens(cycle, shares, rows, main,
                              [float(phases[i].get('maxDur')) for i in indices], baseline_cycle)
        requested_min = params.get(f'min_{index}', float(phases[indices[main]].get('minDur')))
        if not 7 <= requested_min <= 30:
            raise ValueError('Mainline minimum green outside v3 bounds')
        main_min = min(requested_min, greens[main]-1e-6)
        phases[indices[main]].set('minDur', str(main_min))
        elapsed = 0.
        for i, row, maximum in zip(indices, rows, greens):
            phases[i].set('duration', str(maximum))
            phases[i].set('maxDur', str(maximum))
            elapsed += maximum
            phases[i].set('latestEnd', str(round(elapsed, 3)))
            elapsed += float(row['yellow_s'])+float(row['red_clear_s'])
            timing.append(dict(sumo_tls_id=logic.get('id'), cycle_s=cycle, offset_s=offset,
                               phase=i, min_green_s=main_min if i == indices[main] else float(phases[i].get('minDur')),
                               max_green_s=maximum, passage_s=passage))
        for param in logic.findall('param'):
            if param.get('key') == 'cycleTime':
                param.set('value', str(cycle))
            if param.get('key') == 'max-gap':
                param.set('value', str(passage))
    root.insert(0, ET.Comment('PM-fit Optuna v3 plan; demo assumptions, not city timing'))
    p.xml_write(root, path)
    return timing


def fit_routes(scenario, path):
    """Exclude holdout departures even during the drain; keep routes/IDs unchanged."""
    cfg = p.config()
    period = cfg['scenarios'][scenario]
    begin, end = map(seconds, period.get('fit', [period['begin'], period['end']]))
    root = ET.parse(p.ROOT/f'sim/routes_{scenario}.rou.xml').getroot()
    requested = {}
    for vehicle in list(root):
        if vehicle.tag != 'vehicle':
            continue
        depart = float(vehicle.get('depart'))
        if not begin-cfg['warmup_s'] <= depart < end:
            root.remove(vehicle)
        elif depart >= begin:
            edges = vehicle.find('route').get('edges').split()
            approach = next((e for e in edges if e in cfg['mainline_edges'] or e in cfg['side_edges']), None)
            if approach is None:
                raise ValueError('Route never reaches a modeled approach')
            requested[vehicle.get('id')] = approach in cfg['side_edges']
    if not requested:
        raise ValueError('No requested scenario vehicles')
    p.xml_write(root, path)
    return begin, end, requested


def score(scenario, seed, timing, folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    begin, end, requested = fit_routes(scenario, folder/'routes.xml')
    cfg = p.config()
    p.run([p.BIN/'sumo', '-c', p.ROOT/'sim/corridor.sumocfg', '-r', folder/'routes.xml',
           '-a', f'{p.ROOT}/sim/detectors.add.xml,{timing}', '-b', begin-cfg['warmup_s'],
           '-e', end+1800, '--seed', seed, '--time-to-teleport', cfg['time_to_teleport'],
           '--no-step-log', '--aggregate-warnings', -1, '--error-log', folder/'warnings.txt',
           '--summary-output', folder/'summary.xml', '--tripinfo-output', folder/'trips.xml',
           '--vehroute-output', folder/'vehroute.xml', '--vehroute-output.exit-times', 'true',
           '--vehroute-output.write-unfinished', 'true'])
    teleports = re.findall(r"Teleporting vehicle '([^']+)'", (folder/'warnings.txt').read_text())
    if len(teleports) != summary_stats(folder/'summary.xml')['teleports']:
        raise ValueError('Teleport warning/summary mismatch')
    trips = {t.get('id'): dict(t.attrib) for t in ET.parse(folder/'trips.xml').getroot().findall('tripinfo')}
    travels = corridor_times(folder/'vehroute.xml', boundaries(cfg), set(cfg['mainline_edges']), set(teleports))
    return metrics({v: (begin, side) for v, side in requested.items()}, trips, travels, teleports, begin, end)


def objective_value(stats, baseline):
    """Reject every preregistered constraint violation."""
    if not feasible(stats, baseline):
        return 1e9
    primary = sum(s['all_requested_delay_s'] for s in stats)/len(stats)
    return primary


def feasible(stats, baseline):
    return (all(s['teleports'] <= b['teleports']+2 for s, b in zip(stats, baseline))
            and all(sum(s[key] for s in stats) <= 1.05*sum(b[key] for b in baseline)+1e-9
                    for key in CONSTRAINT_METRICS))


def worker(storage, count, worker_seed, baseline):
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.load_study(study_name='pm_peak', storage=storage,
                              sampler=optuna.samplers.TPESampler(seed=worker_seed))
    def objective(trial):
        params = {}
        for key in baseline_params():
            bounds = ((80, 150) if key == 'cycle_s' else (2, 4) if key.startswith('passage_')
                      else (.6, 1.4) if key.startswith('share_') else (7, 30) if key.startswith('min_')
                      else (0, math.nextafter(1., 0.)))
            params[key] = trial.suggest_float(key, *bounds)
        with tempfile.TemporaryDirectory() as temp:
            timing = Path(temp)/'plan.xml'
            plan('pm_peak', params, timing)
            stats = [score('pm_peak', seed, timing, temp) for seed in TRAIN_SEEDS]
        trial.set_user_attr('stats', stats)
        if trial.number % 20 == 0:
            print(f'trial {trial.number}: loss={stats[0]["all_requested_delay_s"]:.2f}, unfinished={stats[0]["unfinished"]}, teleports={stats[0]["teleports"]}', flush=True)
        return objective_value(stats, baseline)
    study.optimize(objective, n_trials=count, n_jobs=1, timeout=6500)


def optimize(trials=300):
    if trials < 10:
        raise ValueError('At least ten trials required for top-ten rescoring')
    start = time.monotonic()
    power = subprocess.check_output(['pmset', '-g', 'batt'], text=True)
    workers = min(3 if "drawing from 'AC Power'" in power else 1, trials)
    cfg = p.config()
    baselines = []
    for seed in range(13):
        with tempfile.TemporaryDirectory() as folder:
            baselines.append(score('pm_peak', seed, p.ROOT/'sim/tls_actuated_pm_peak.add.xml', folder))
    with tempfile.TemporaryDirectory() as temp:
        storage = f'sqlite:///{temp}/study.sqlite3'
        study = optuna.create_study(study_name='pm_peak', storage=storage,
                                    sampler=optuna.samplers.TPESampler(seed=0))
        study.enqueue_trial(baseline_params())
        study.enqueue_trial(v2_params())
        with ProcessPoolExecutor(max_workers=workers) as pool:
            jobs = [pool.submit(worker, storage, trials//workers+(i < trials % workers), i,
                                baselines[:len(TRAIN_SEEDS)]) for i in range(workers)]
            for job in jobs:
                job.result(timeout=max(1, 6900-(time.monotonic()-start)))
        completed = [t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE]
        if len(completed) != trials:
            raise RuntimeError(f'Only {len(completed)}/{trials} trials completed within laptop budget')
        study.trials_dataframe().to_csv(p.ROOT/'reports/optimize_v3_trials.csv', index=False)
        finalists = []
        training_feasible = [t for t in completed if feasible(t.user_attrs['stats'], baselines[:len(TRAIN_SEEDS)])]
        candidates = sorted(training_feasible, key=lambda t: t.value)[:10]
        if completed[0] not in candidates:
            candidates.append(completed[0])
        for trial in candidates:
            metrics = []
            for seed in SELECTION_SEEDS:
                with tempfile.TemporaryDirectory() as folder:
                    timing = Path(folder)/'plan.xml'
                    plan('pm_peak', trial.params, timing)
                    metrics.append(score('pm_peak', seed, timing, folder))
            value = objective_value(metrics, baselines[len(TRAIN_SEEDS):])
            finalists.append(dict(trial=trial.number, params=trial.params, stats=metrics,
                                  all_seed_objective=value, feasible=(feasible(trial.user_attrs['stats'], baselines[:len(TRAIN_SEEDS)])
                                                                   and feasible(metrics, baselines[len(TRAIN_SEEDS):]))))
    best = min((t for t in finalists if t['feasible']), key=lambda t: t['all_seed_objective'])
    selected = {'pm_peak': best['stats'], 'night': []}
    for scenario in cfg['scenarios']:
        path = p.ROOT/f'sim/tls_optuna_v3_{scenario}.add.xml'
        timing = plan(scenario, best['params'], path)
        p.write_csv(f'reports/timing_v3_{scenario}.csv', timing)
        if scenario != 'pm_peak':
            for seed in cfg['seeds']:
                with tempfile.TemporaryDirectory() as folder:
                    selected[scenario].append(score(scenario, seed, path, folder))
    result = dict(trials=trials, wall_s=time.monotonic()-start, workers=workers, power=power.strip(),
                  seeds=list(TRAIN_SEEDS), selection_seeds=list(SELECTION_SEEDS), best=best,
                  baseline=baselines, selected=selected, finalists=finalists)
    (p.ROOT/'reports/optimize_v3.json').write_text(json.dumps(result, indent=2)+'\n')
    print(f'optimize: {trials} trials, {result["wall_s"]:.1f} s, {workers} processes; selected trial {best["trial"]}', flush=True)
