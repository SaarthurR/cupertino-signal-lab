"""Fit-only timing search; freeze the winning PM parameters for night too."""
from concurrent.futures import ProcessPoolExecutor
import csv
import json
import math
from pathlib import Path
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET

import optuna

from . import pipeline as p
from .demand import seconds, summary_stats


def split_greens(cycle, split, rows, main):
    """Mainline share of usable green; reserve every other phase's lower bound."""
    if not 80 <= cycle <= 150 or not .4 <= split <= .8:
        raise ValueError('Cycle/split outside M5 bounds')
    lower = [max(10., float(r['min_green_s'])+1) for r in rows]
    upper = [min(60., float(r['max_green_s'])) for r in rows]
    available = cycle-sum(float(r['yellow_s'])+float(r['red_clear_s']) for r in rows)
    if available < sum(lower) or any(a > b for a, b in zip(lower, upper)):
        raise ValueError('Cycle cannot accommodate bounded greens and clearances')
    greens = lower[:]
    greens[main] = min(upper[main], available-sum(lower)+lower[main], max(lower[main], split*available))
    # Equal non-mainline shares, redistributing only when an input ceiling binds.
    remaining = available-sum(greens)
    active = [i for i in range(len(rows)) if i != main]
    while active and remaining > 1e-9:
        share = remaining/len(active)
        for i in active:
            added = min(share, upper[i]-greens[i])
            greens[i] += added
            remaining -= added
        active = [i for i in active if greens[i] < upper[i]-1e-9]
    return greens


def plan(scenario, params, path):
    root = ET.parse(p.ROOT/f'sim/tls_actuated_{scenario}.add.xml').getroot()
    with open(p.ROOT/'data/processed/timing_inputs.csv') as stream:
        inputs = {(r['sumo_tls_id'], int(r['phase'])): r for r in csv.DictReader(stream)}
    timing = []
    cycle = params['cycle_s']
    for index, logic in enumerate(root.findall('tlLogic')):
        logic.set('programID', 'optuna')
        offset = params[f'offset_{index}']*cycle
        logic.set('offset', str(offset))
        phases = logic.findall('phase')
        indices = [i for i, phase in enumerate(phases) if phase.get('minDur') is not None]
        rows = [inputs[logic.get('id'), i] for i in indices]
        main = next(j for j, i in enumerate(indices) if phases[i].get('name') == 'mainline')
        greens = split_greens(cycle, params[f'split_{index}'], rows, main)
        elapsed = 0.
        for i, row, maximum in zip(indices, rows, greens):
            phases[i].set('duration', str(maximum))
            phases[i].set('maxDur', str(maximum))
            elapsed += maximum
            phases[i].set('latestEnd', str(elapsed))
            elapsed += float(row['yellow_s'])+float(row['red_clear_s'])
            timing.append(dict(sumo_tls_id=logic.get('id'), cycle_s=cycle, offset_s=offset,
                               phase=i, max_green_s=maximum, passage_s=params['passage_s']))
        for param in logic.findall('param'):
            if param.get('key') == 'cycleTime':
                param.set('value', str(cycle))
            if param.get('key') == 'max-gap':
                param.set('value', str(params['passage_s']))
    root.insert(0, ET.Comment('PM-fit Optuna plan; demo assumptions, not city timing'))
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
           '--no-step-log', '--summary-output', folder/'summary.xml', '--tripinfo-output', folder/'trips.xml'])
    stats = summary_stats(folder/'summary.xml')
    trips = [t for t in ET.parse(folder/'trips.xml').getroot().findall('tripinfo')
             if t.get('id') in requested and float(t.get('arrival')) >= 0]
    if not trips:
        raise ValueError('No completed fit vehicles')
    losses = [float(t.get('timeLoss')) for t in trips]
    side = [float(t.get('timeLoss')) for t in trips if requested[t.get('id')]]
    unfinished = len(requested)-len(trips)
    # Full simulated horizon per missing vehicle/teleport; insertion delay is also real delay.
    penalty_s = end-begin+cfg['warmup_s']+1800
    deferred = (sum(float(t.get('departDelay')) for t in trips)
                + penalty_s*(unfinished+stats['teleports']))/len(requested)
    return {**stats, 'requested': len(requested), 'completed': len(trips), 'unfinished': unfinished,
            'mean_time_loss_s': sum(losses)/len(losses),
            'side_time_loss_s': sum(side)/len(side) if side else penalty_s,
            'mean_waiting_count': sum(float(t.get('waitingCount')) for t in trips)/len(trips),
            'deferred_penalty_s': deferred, 'vehicle_penalty_s': penalty_s}


def objective_value(stats, baseline):
    return (stats['mean_time_loss_s'] + stats['deferred_penalty_s']
            + max(0., stats['side_time_loss_s']-1.2*baseline['side_time_loss_s']))


def worker(storage, count, worker_seed, baseline):
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.load_study(study_name='pm_peak', storage=storage,
                              sampler=optuna.samplers.TPESampler(seed=worker_seed))
    def objective(trial):
        params = {'cycle_s': trial.suggest_float('cycle_s', 80, 150),
                  'passage_s': trial.suggest_float('passage_s', 2, 4)}
        for index in range(len(p.config()['signals'])):
            params[f'offset_{index}'] = trial.suggest_float(f'offset_{index}', 0, math.nextafter(1., 0.))
            params[f'split_{index}'] = trial.suggest_float(f'split_{index}', .4, .8)
        with tempfile.TemporaryDirectory() as temp:
            timing = Path(temp)/'plan.xml'
            plan('pm_peak', params, timing)
            stats = score('pm_peak', p.config()['seeds'][0], timing, temp)
        trial.set_user_attr('stats', stats)
        if trial.number % 20 == 0:
            print(f'trial {trial.number}: loss={stats["mean_time_loss_s"]:.2f}, unfinished={stats["unfinished"]}, teleports={stats["teleports"]}', flush=True)
        return objective_value(stats, baseline)
    study.optimize(objective, n_trials=count, n_jobs=1, timeout=6500)


def optimize(trials=200):
    if trials < 5:
        raise ValueError('At least five trials required for top-five rescoring')
    start = time.monotonic()
    power = subprocess.check_output(['pmset', '-g', 'batt'], text=True)
    workers = min(3 if "drawing from 'AC Power'" in power else 1, trials)
    cfg = p.config()
    baselines = {}
    for scenario in cfg['scenarios']:
        baselines[scenario] = []
        for seed in cfg['seeds']:
            with tempfile.TemporaryDirectory() as temp:
                baselines[scenario].append(score(scenario, seed, p.ROOT/f'sim/tls_actuated_{scenario}.add.xml', temp))
    with tempfile.TemporaryDirectory() as temp:
        storage = f'sqlite:///{temp}/study.sqlite3'
        study = optuna.create_study(study_name='pm_peak', storage=storage,
                                    sampler=optuna.samplers.TPESampler(seed=0))
        with ProcessPoolExecutor(max_workers=workers) as pool:
            jobs = [pool.submit(worker, storage, trials//workers+(i < trials % workers), i,
                                baselines['pm_peak'][0]) for i in range(workers)]
            for job in jobs:
                job.result(timeout=max(1, 6900-(time.monotonic()-start)))
        completed = [t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE]
        if len(completed) != trials:
            raise RuntimeError(f'Only {len(completed)}/{trials} trials completed within laptop budget')
        study.trials_dataframe().to_csv(p.ROOT/'reports/optimize_trials.csv', index=False)
        finalists = []
        for trial in sorted(completed, key=lambda t: t.value)[:5]:
            metrics = []
            for seed in cfg['seeds']:
                with tempfile.TemporaryDirectory() as folder:
                    timing = Path(folder)/'plan.xml'
                    plan('pm_peak', trial.params, timing)
                    metrics.append(score('pm_peak', seed, timing, folder))
            values = [objective_value(s, b) for s, b in zip(metrics, baselines['pm_peak'])]
            finalists.append(dict(trial=trial.number, params=trial.params, stats=metrics,
                                  all_seed_objective=sum(values)/len(values)))
    best = min(finalists, key=lambda t: t['all_seed_objective'])
    selected = {'pm_peak': best['stats'], 'night': []}
    for scenario in cfg['scenarios']:
        path = p.ROOT/f'sim/tls_optuna_{scenario}.add.xml'
        timing = plan(scenario, best['params'], path)
        p.write_csv(f'reports/timing_{scenario}.csv', timing)
        if scenario != 'pm_peak':
            for seed in cfg['seeds']:
                with tempfile.TemporaryDirectory() as folder:
                    selected[scenario].append(score(scenario, seed, path, folder))
    result = dict(trials=trials, wall_s=time.monotonic()-start, workers=workers, power=power.strip(),
                  seeds=cfg['seeds'], best=best, baseline=baselines, selected=selected, finalists=finalists)
    (p.ROOT/'reports/optimize.json').write_text(json.dumps(result, indent=2)+'\n')
    print(f'optimize: {trials} trials, {result["wall_s"]:.1f} s, {workers} processes; selected trial {best["trial"]}', flush=True)
