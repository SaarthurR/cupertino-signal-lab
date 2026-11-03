"""Practice in the copy only: Optuna TPE over bounded max greens, cycle and offsets of the old timing."""
import json
import hashlib
import statistics
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import optuna
from scipy.stats import wilcoxon

from signal_lab import optimize as o, pipeline as p
from . import learn, road

# Development screening rules; the original experiment's artifacts remain frozen.
TRIALS = 150
SEARCH_SEEDS = range(3)
CONFIRM_SEEDS = range(10, 20)
MIN_GAIN = .02  # mean copy gain on confirm seeds, share of old delay
ALPHA = .05  # one-sided paired Wilcoxon on confirm seeds
SIDE_LIMIT = 1.05  # side-street all-requested delay vs old
TELEPORT_MARGIN = 2  # per seed, vs old


def old_params(cfg):
    return o.baseline_params(source=road.file(cfg, 'old_timing'))


def searched(key):
    """Passage times and minimum greens stay as in the old timing."""
    return key == 'cycle_s' or key.startswith(('offset_', 'share_'))


def bounds(key, old_cycle):
    """v5 bounds; the cycle floor drops to the old cycle when that is shorter."""
    if key == 'cycle_s':
        low, high = o.cycle_bounds(5)
        return min(low, old_cycle), max(high, old_cycle)
    return o.bounds(key, 5)


def plan(cfg, params, path):
    """Old timing with new max greens, cycle and offsets; phase order, clearances and minimum greens unchanged."""
    old = old_params(cfg)
    o.plan('pm_peak', {**old, **params}, path, 5, source=road.file(cfg, 'old_timing'),
           inputs=road.file(cfg, 'timing_inputs'), cycle_range=bounds('cycle_s', old['cycle_s']))
    root = ET.parse(path).getroot()
    for child in list(root):
        if child.tag is ET.Comment:
            root.remove(child)
    root.insert(0, ET.Comment('Signal Learner plan, SIMULATED: bounded change to greens and offsets of the old timing'))
    for logic in root.findall('tlLogic'):
        logic.set('programID', 'learner')
    p.xml_write(root, path)


def score(cfg, routes, timing, seeds):
    return [s for s, _ in road.many([(cfg, routes, timing, seed) for seed in seeds])]


def side(stats):
    return sum(s['side_all_requested_delay_s'] or 0 for s in stats)


def feasible(stats, base):
    if not stats or len(stats) != len(base) or any(s['seed'] != b['seed'] for s, b in zip(stats, base)):
        return False
    if len({s['seed'] for s in stats}) != len(stats):
        return False
    groups = set().union(*(s.get('origin_delay_s', {}) for s in base))
    if not groups or any(set(s.get('origin_delay_s', {})) != groups for s in [*stats, *base]):
        return False
    return (all(s['teleports'] <= b['teleports']+TELEPORT_MARGIN and s['unfinished'] <= b['unfinished']
                for s, b in zip(stats, base))
            and side(stats) <= SIDE_LIMIT*side(base)+1e-9
            and all(sum(s['origin_delay_s'][g] for s in stats) <= SIDE_LIMIT*sum(b['origin_delay_s'][g] for b in base)+1e-9
                    for g in groups)
            and all(sum(s[key] for s in stats) <= sum(b[key] for b in base)+1e-9
                    for key in ('all_requested_delay_0_s', 'all_requested_delay_1800_s')))


def primary(stats):
    return statistics.mean(s['all_requested_delay_s'] for s in stats)


def practice(name, trials=TRIALS, search_seeds=SEARCH_SEEDS, confirm_seeds=CONFIRM_SEEDS, sampler=None):
    search_seeds, confirm_seeds = tuple(search_seeds), tuple(confirm_seeds)
    if (not isinstance(trials, int) or isinstance(trials, bool) or trials <= 0 or
            any(not seeds or len(set(seeds)) != len(seeds) or
                any(not isinstance(s, int) or isinstance(s, bool) or s < 0 for s in seeds)
                for seeds in (search_seeds, confirm_seeds)) or set(search_seeds) & set(confirm_seeds)):
        raise ValueError('Use positive trials and nonempty, unique, disjoint search/confirmation seeds')
    cfg = road.load(name)
    out, start = road.OUT/name, time.monotonic()
    copy, old_timing = out/'copy.rou.xml', road.file(cfg, 'old_timing')
    old = old_params(cfg)
    report_path = out/'learn.json'
    report = json.loads(report_path.read_text()) if report_path.exists() else {}
    gate = learn.quality_gate(report)
    copies = report.get('demand_copies', [])
    if copies != ['copy.rou.xml', 'copy_low.rou.xml', 'copy_high.rou.xml'] or any(not (out/p).is_file() for p in copies):
        gate['passed'] = False
        gate['reasons'].append('Missing count-spread stress copies; rebuild the copy before searching')
    elif report.get('copies_sha256') != {filename: hashlib.sha256((out/filename).read_bytes()).hexdigest() for filename in copies}:
        gate['passed'] = False
        gate['reasons'].append('Copy files changed since the fit check; rebuild and validate them')
    try:
        same_observations = report.get('observations_sha256') == learn.observed_hashes(name)
    except OSError as exc:
        same_observations = False
        gate['reasons'].append(f'Cannot verify observation files: {exc}')
    if not same_observations:
        gate['passed'] = False
        gate['reasons'].append('Observation files changed or lack validation hashes; relearn before searching')
    if not gate['passed']:
        plan(cfg, old, out/'plan.add.xml')
        result = dict(road=name, trials=0, best_trial=0, clear_gain=False, confirm_old=[], confirm_new=[],
                      search_seeds=list(search_seeds),
                      confirm_diffs_s=[], confirm_seeds=list(confirm_seeds), confirm_gain=0., confirm_p=1.,
                      confirm_feasible=False, quality_gate=gate, params=old, old_params=old,
                      wall_s=time.monotonic()-start)
        (out/'practice.json').write_text(json.dumps(result, indent=2)+'\n')
        p.write_csv(out/'trials.csv', [dict(trial=0, decision='no search: insufficient copy evidence')])
        print(f'practice {name}: no search; copy screening failed')
        return result
    base = score(cfg, copy, old_timing, search_seeds)
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    sampler = sampler or optuna.samplers.TPESampler(seed=0)
    study = optuna.create_study(sampler=sampler)
    study.enqueue_trial({k: v for k, v in old.items() if searched(k)})

    def objective(trial):
        params = {k: trial.suggest_float(k, *bounds(k, old['cycle_s'])) for k in old if searched(k)}
        with tempfile.TemporaryDirectory() as temp:
            timing = Path(temp)/'plan.xml'
            try:
                plan(cfg, params, timing)
            except ValueError:
                return 1e9  # cycle cannot hold the bounded greens and clearances
            stats = score(cfg, copy, timing, search_seeds)
        trial.set_user_attr('stats', stats)
        return primary(stats) if feasible(stats, base) else 1e9
    study.optimize(objective, n_trials=trials)
    best = study.best_trial
    plan(cfg, best.params, out/'plan.add.xml')
    before = score(cfg, copy, old_timing, confirm_seeds)
    after = before if best.number == 0 else score(cfg, copy, out/'plan.add.xml', confirm_seeds)
    diffs = [a['all_requested_delay_s']-b['all_requested_delay_s'] for a, b in zip(after, before)]
    test = wilcoxon(diffs, alternative='less') if any(diffs) else None
    base_mean = primary(before)
    gain = -statistics.mean(diffs)/base_mean if base_mean else 0.
    p_value = float(test.pvalue) if test else 1.
    clear = best.number != 0 and gain >= MIN_GAIN and p_value < ALPHA and feasible(after, before)
    stress = []
    if clear:
        for filename in copies[1:]:
            a = score(cfg, out/filename, old_timing, confirm_seeds)
            b = score(cfg, out/filename, out/'plan.add.xml', confirm_seeds)
            delta = [n['all_requested_delay_s']-o['all_requested_delay_s'] for n, o in zip(b, a)]
            base_mean = primary(a)
            stress_gain = -statistics.mean(delta)/base_mean if base_mean else 0.
            stress_p = float(wilcoxon(delta, alternative='less').pvalue) if any(delta) else 1.
            passed = stress_gain >= MIN_GAIN and stress_p < ALPHA and feasible(b, a)
            stress.append(dict(copy=filename, gain=stress_gain, p=stress_p, feasible=feasible(b, a), passed=passed))
        clear = all(s['passed'] for s in stress)
    if not clear and best.number != 0:
        (out/'plan.add.xml').replace(out/'rejected_candidate.add.xml')
        plan(cfg, old, out/'plan.add.xml')
    result = dict(road=name, trials=trials, search_seeds=list(search_seeds), confirm_seeds=list(confirm_seeds),
                  best_trial=best.number, best_search_delay_s=best.value, old_search_delay_s=primary(base),
                  params=best.params, selected_params=best.params if clear else {k: v for k, v in old.items() if searched(k)},
                  old_params={k: v for k, v in old.items() if searched(k)},
                  confirm_old=before, confirm_new=after, confirm_diffs_s=diffs, confirm_gain=gain,
                  confirm_p=p_value, confirm_feasible=feasible(after, before), clear_gain=clear,
                  quality_gate=gate, stress_copies=stress,
                  settings=dict(min_gain=MIN_GAIN, alpha=ALPHA, side_limit=SIDE_LIMIT, teleport_margin=TELEPORT_MARGIN,
                                sampler=type(sampler).__name__, max_parallel_sims=road.MAX_SIMS),
                  wall_s=time.monotonic()-start)
    (out/'practice.json').write_text(json.dumps(result, indent=2)+'\n')
    study.trials_dataframe().drop(columns=['user_attrs_stats'], errors='ignore').to_csv(out/'trials.csv', index=False)
    print(f'practice {name}: best trial {best.number}, copy gain {gain:.1%}, p={p_value:.3g}, clear={clear}')
    return result
