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
from .evaluate import boundaries, corridor_times, metrics, origin_delays

TRAIN_SEEDS = range(5)
SELECTION_SEEDS = range(5, 13)
CONSTRAINT_METRICS = ('side_all_requested_delay_s', 'mainline_travel_eb_s', 'mainline_travel_wb_s')

def split_greens(cycle, split, rows, main, baseline_greens, baseline_cycle, max_cycle=150, min_cycle=80):
    """Scale Webster greens, using bounded phase shares and retaining nominal slack."""
    if not min_cycle <= cycle <= max_cycle or (not isinstance(split, list) and not .6 <= split <= 1.4):
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


def baseline_params(scenario='pm_peak'):
    logics = ET.parse(p.ROOT/f'sim/tls_actuated_{scenario}.add.xml').getroot().findall('tlLogic')
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


def plan(scenario, params, path, version=3):
    root = ET.parse(p.ROOT/f'sim/tls_actuated_{scenario}.add.xml').getroot()
    with open(p.ROOT/'data/processed/timing_inputs.csv') as stream:
        inputs = {(r['sumo_tls_id'], int(r['phase'])): r for r in csv.DictReader(stream)}
    timing = []
    cycle = params['cycle_s']
    for index, logic in enumerate(root.findall('tlLogic')):
        logic.set('programID', f'optuna_v{version}')
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
                              [float(phases[i].get('maxDur')) for i in indices], baseline_cycle,
                              *reversed(cycle_bounds(version, scenario)))
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
    root.insert(0, ET.Comment(f'PM-fit Optuna v{version} plan; demo assumptions, not city timing'))
    p.xml_write(root, path)
    return timing


def fit_routes(scenario, path, routes_source=None):
    """Exclude holdout departures even during the drain; keep routes/IDs unchanged."""
    cfg = p.config()
    period = cfg['scenarios'][scenario]
    begin, end = map(seconds, period.get('fit', [period['begin'], period['end']]))
    root = ET.parse(routes_source or p.ROOT/f'sim/routes_{scenario}.rou.xml').getroot()
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
            requested[vehicle.get('id')] = approach
    if not requested:
        raise ValueError('No requested scenario vehicles')
    p.xml_write(root, path)
    return begin, end, requested


def score(scenario, seed, timing, folder, routes_source=None):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    begin, end, approaches = fit_routes(scenario, folder/'routes.xml', routes_source)
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
    stats = metrics({v: (begin, a in cfg['side_edges']) for v, a in approaches.items()}, trips, travels, teleports, begin, end)
    stats['origin_delay_s'] = origin_delays({v: (begin, a) for v, a in approaches.items()}, trips, teleports, begin, end)
    return stats


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


def cycle_bounds(version=3, scenario='pm_peak'):
    # 66.9 s is the night textbook cycle and the shortest every signal can hold.
    return 66.9 if version >= 5 and scenario == 'night' else 80, 180 if version >= 4 else 150


def bounds(key, version=3, scenario='pm_peak'):
    """The v3 search space, in one place so write-ups cannot drift from the search."""
    return (cycle_bounds(version, scenario) if key == 'cycle_s' else (2, 4) if key.startswith('passage_')
            else (.6, 1.4) if key.startswith('share_') else (7, 30) if key.startswith('min_')
            else (0, math.nextafter(1., 0.)))


def worker(storage, count, worker_seed, baseline, version=3, scenario='pm_peak'):
    train_seeds = range(3) if version == 4 else TRAIN_SEEDS
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.load_study(study_name='pm_peak', storage=storage,
                              sampler=optuna.samplers.TPESampler(seed=worker_seed))
    def objective(trial):
        params = {}
        for key in baseline_params(scenario):
            params[key] = trial.suggest_float(key, *bounds(key, version, scenario))
        with tempfile.TemporaryDirectory() as temp:
            timing = Path(temp)/'plan.xml'
            plan(scenario, params, timing, version)
            stats = [score(scenario, seed, timing, temp) for seed in train_seeds]
        trial.set_user_attr('stats', stats)
        if trial.number % 20 == 0:
            print(f'trial {trial.number}: loss={stats[0]["all_requested_delay_s"]:.2f}, unfinished={stats[0]["unfinished"]}, teleports={stats[0]["teleports"]}', flush=True)
        return objective_value(stats, baseline)
    study.optimize(objective, n_trials=count, n_jobs=1, timeout=6500)


V5_TRIALS = {'pm_peak': 600, 'night': 200}


def origin_means(stats):
    groups = {}
    for s in stats:
        for origin, delay in s['origin_delay_s'].items():
            groups.setdefault(origin, []).append(delay)
    return {o: sum(v)/len(v) for o, v in groups.items()}


def worst_origin_change(stats, baseline):
    ours, theirs = origin_means(stats), origin_means(baseline)
    return max(ours[o]-theirs[o] for o in theirs)


def select_v5(finalists, v4_trial=None):
    """Lowest selection primary, tiebroken within 1% by worst origin group; v4 kept unless beaten on both cohorts."""
    pool = [f for f in finalists if f['feasible']]
    lowest = min(f['selection_primary_s'] for f in pool)
    best = min((f for f in pool if f['selection_primary_s'] <= 1.01*lowest), key=lambda f: f['worst_origin_change_s'])
    v4 = next((f for f in pool if f['trial'] == v4_trial), None)
    if v4 and best is not v4 and not (best['train_primary_s'] < v4['train_primary_s']
                                      and best['selection_primary_s'] < v4['selection_primary_s']):
        return v4, 'v4_fallback'
    return best, 'tiebreak_band' if best['selection_primary_s'] > lowest else 'lowest'


def optimize(trials=300, version=3, scenario='pm_peak', resume=False):
    """resume: v5 timeout contingency; select from the saved study's completed trials, no more search."""
    train_seeds = range(3) if version == 4 else TRAIN_SEEDS
    name = f'v{version}' + ('_night' if scenario == 'night' else '')
    if version == 4 and trials != 60:
        raise ValueError("V4 preregistration requires exactly 60 trials")
    if version == 5 and trials != V5_TRIALS[scenario] and not resume:
        raise ValueError(f'V5 preregistration requires exactly {V5_TRIALS[scenario]} {scenario} trials')
    if version != 5 and scenario != 'pm_peak':
        raise ValueError('Only v5 tunes a separate night plan')
    if trials < 10:
        raise ValueError('At least ten trials required for top-ten rescoring')
    if version >= 4 and (p.ROOT/f'reports/optimize_{name}.json').exists():
        raise RuntimeError(f'Frozen {name} already exists; refusing to retune')
    start = time.monotonic()
    power = subprocess.check_output(['pmset', '-g', 'batt'], text=True)
    workers = 1 if version == 4 else min(3 if "drawing from 'AC Power'" in power else 1, trials)
    cfg = p.config()
    baselines = []
    for seed in range(13):
        with tempfile.TemporaryDirectory() as folder:
            baselines.append(None if version == 4 and seed in (3, 4) else
                             score(scenario, seed, p.ROOT/f'sim/tls_actuated_{scenario}.add.xml', folder))
    selection_baselines = [baselines[s] for s in SELECTION_SEEDS]
    with tempfile.TemporaryDirectory() as temp:
        database = p.ROOT/f'reports/optimize_{name}.sqlite3' if version >= 4 else Path(temp)/'study.sqlite3'
        storage = f'sqlite:///{database}'
        study = (optuna.load_study if resume else optuna.create_study)(
            study_name='pm_peak', storage=storage, sampler=optuna.samplers.TPESampler(seed=0))
        frozen = lambda v: json.loads((p.ROOT/f'reports/optimize_v{v}.json').read_text())['best']['params']
        enqueued = ([baseline_params(scenario)] if scenario == 'night' else
                    [baseline_params(), frozen(3), frozen(4)] if version == 5 else
                    [baseline_params(), frozen(3) if version == 4 else v2_params()])
        for params in [] if resume else enqueued:
            study.enqueue_trial(params)
        # SQLite ignores row locks, so parallel workers can both claim one queued trial; run the queue here.
        if not resume:
            worker(storage, len(enqueued), 0, baselines[:len(train_seeds)], version, scenario)
        remaining = 0 if resume else trials-len(enqueued)
        with ProcessPoolExecutor(max_workers=workers) as pool:
            jobs = [] if resume else [pool.submit(worker, storage, remaining//workers+(i < remaining % workers), i,
                                baselines[:len(train_seeds)], version, scenario) for i in range(workers)]
            for job in jobs:
                job.result(timeout=max(1, 6900-(time.monotonic()-start)))
        completed = [t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE]
        trials = len(completed) if resume else trials
        if len(completed) != trials:
            raise RuntimeError(f'Only {len(completed)}/{trials} trials completed within laptop budget')
        study.trials_dataframe().to_csv(p.ROOT/f'reports/optimize_{name}_trials.csv', index=False)
        finalists = []
        training_feasible = [t for t in completed if feasible(t.user_attrs['stats'], baselines[:len(train_seeds)])]
        candidates = sorted(training_feasible, key=lambda t: t.value)[:10]
        for trial in completed[:len(enqueued) if version == 5 else 1]:
            if trial not in candidates:
                candidates.append(trial)
        for trial in candidates:
            metrics = []
            for seed in SELECTION_SEEDS:
                with tempfile.TemporaryDirectory() as folder:
                    timing = Path(folder)/'plan.xml'
                    plan(scenario, trial.params, timing, version)
                    metrics.append(score(scenario, seed, timing, folder))
            value = objective_value(metrics, selection_baselines)
            train = trial.user_attrs['stats']
            finalists.append(dict(trial=trial.number, params=trial.params, stats=metrics,
                                  all_seed_objective=value, feasible=(feasible(train, baselines[:len(train_seeds)])
                                                                   and feasible(metrics, selection_baselines)),
                                  train_primary_s=sum(s['all_requested_delay_s'] for s in train)/len(train),
                                  selection_primary_s=sum(s['all_requested_delay_s'] for s in metrics)/len(metrics),
                                  worst_origin_change_s=worst_origin_change(metrics, selection_baselines)
                                  if 'origin_delay_s' in metrics[0] else None))
    if version == 5:
        best, rule = select_v5(finalists, 2 if scenario == 'pm_peak' else None)
    else:
        best, rule = min((t for t in finalists if t['feasible']), key=lambda t: t['all_seed_objective']), 'lowest'
    selected = {'pm_peak': best['stats'], 'night': []} if scenario == 'pm_peak' else {scenario: best['stats']}
    for target in ([scenario] if version == 5 else cfg['scenarios']):
        path = p.ROOT/f'sim/tls_optuna_v{version}_{target}.add.xml'
        timing = plan(target, best['params'], path, version)
        p.write_csv(f'reports/timing_v{version}_{target}.csv', timing)
        if target != 'pm_peak' and version < 4:
            for seed in cfg['seeds']:
                with tempfile.TemporaryDirectory() as folder:
                    selected[target].append(score(target, seed, path, folder))
    result = dict(trials=trials, wall_s=time.monotonic()-start, workers=workers, power=power.strip(),
                  scenario=scenario, seeds=list(train_seeds), selection_seeds=list(SELECTION_SEEDS),
                  enqueued=len(enqueued), selection_rule=rule, best=best, resumed_from_saved_study=resume,
                  preregistered_trials=V5_TRIALS[scenario] if version == 5 else trials,
                  baseline=baselines, selected=selected, finalists=finalists)
    (p.ROOT/f'reports/optimize_{name}.json').write_text(json.dumps(result, indent=2)+'\n')
    print(f'optimize: {trials} trials, {result["wall_s"]:.1f} s, {workers} processes; selected trial {best["trial"]} ({rule})', flush=True)
