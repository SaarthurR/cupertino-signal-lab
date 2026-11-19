"""Practice in the copy only: Optuna TPE over bounded max greens, cycle and offsets of the old timing."""
import json
import math
import statistics
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import optuna
from scipy.stats import wilcoxon

from signal_lab import optimize as o, pipeline as p
from . import learn, road

# Frozen learner settings; docs/PREREGISTRATION-LEARNER.md quotes these.
TRIALS = 150
SEARCH_SEEDS = range(3)
CONFIRM_SEEDS = range(10, 20)
MIN_GAIN = .02  # mean copy gain on confirm seeds, share of old delay
ALPHA = .05  # one-sided paired Wilcoxon on confirm seeds
SIDE_LIMIT = 1.05  # side-street all-requested delay vs old
APPROACH_LIMIT = 1.05  # each origin approach on each matched simulation seed
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
    return (bool(stats) and len(stats) == len(base)
            and all(s['seed'] == b['seed'] and s['teleports'] <= b['teleports']+TELEPORT_MARGIN
                    for s, b in zip(stats, base))
            and side(stats) <= SIDE_LIMIT*side(base)+1e-9 and not regressions(stats, base))


def regressions(stats, base):
    """Identify approaches that worsen beyond the limit or cannot be compared."""
    failed = set()
    for new, old in zip(stats, base, strict=True):
        before, after = old['origin_delay_s'], new['origin_delay_s']
        if not before or before.keys() != after.keys():
            raise ValueError('A paired run is missing origin-approach scores')
        for origin, a in before.items():
            b = after[origin]
            if not all(math.isfinite(v) and v >= 0 for v in (a, b)):
                raise ValueError('Invalid origin-approach score')
            if b > APPROACH_LIMIT*a+1e-9:
                failed.add(origin)
    return sorted(failed)


def primary(stats):
    return statistics.mean(s['all_requested_delay_s'] for s in stats)


def current(cfg, out):
    result = json.loads((out/'practice.json').read_text())
    fit = learn.current_fit(cfg, out)
    if (result.get('fit_sha256') != learn.digest(out/'learn.json')
            or result.get('fit_failures', []) != learn.fit_failures(fit)
            or (not result.get('fit_failures') and result.get('plan_sha256') != learn.digest(out/'plan.add.xml'))):
        raise ValueError('Practice inputs or plan changed. Run practice again.')
    return result


def practice(name, trials=TRIALS, search_seeds=SEARCH_SEEDS, confirm_seeds=CONFIRM_SEEDS):
    cfg = road.load(name)
    search_seeds, confirm_seeds = tuple(search_seeds), tuple(confirm_seeds)
    if trials < 1 or not search_seeds or not confirm_seeds or len(set(search_seeds+confirm_seeds)) != len(search_seeds+confirm_seeds):
        raise ValueError('Practice needs a trial and distinct seeds for search and confirmation')
    out, start = road.OUT/name, time.monotonic()
    copy, old_timing = out/'copy.rou.xml', road.file(cfg, 'old_timing')
    fit_path = out/'learn.json'
    fit_sha256 = learn.digest(fit_path)
    failures = learn.fit_failures(learn.current_fit(cfg, out))
    if failures:
        result = dict(road=name, fit_sha256=fit_sha256, fit_failures=failures, trials=0,
                      clear_gain=False, confirm_old=[], confirm_new=[])
        (out/'practice.json').write_text(json.dumps(result, indent=2)+'\n')
        print(f"practice {name}: no search; copy failed {', '.join(failures)}")
        return result
    old = old_params(cfg)
    base = score(cfg, copy, old_timing, search_seeds)
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(sampler=optuna.samplers.TPESampler(seed=0))
    study.enqueue_trial({k: v for k, v in old.items() if searched(k)})

    def objective(trial):
        params = {k: trial.suggest_float(k, *bounds(k, old['cycle_s'])) for k in old if searched(k)}
        if trial.number == 0:
            return primary(base)
        with tempfile.TemporaryDirectory() as temp:
            timing = Path(temp)/'plan.xml'
            try:
                plan(cfg, params, timing)
            except ValueError:
                return 1e9  # cycle cannot hold the bounded greens and clearances
            stats = score(cfg, copy, timing, search_seeds)
        return primary(stats) if feasible(stats, base) else 1e9
    study.optimize(objective, n_trials=trials)
    best = study.best_trial
    before = score(cfg, copy, old_timing, confirm_seeds)
    with tempfile.TemporaryDirectory(dir=out) as temp:
        candidate = Path(temp)/'plan.xml'
        if best.number == 0:
            candidate.write_bytes(old_timing.read_bytes())
        else:
            plan(cfg, best.params, candidate)
        after = before if best.number == 0 else score(cfg, copy, candidate, confirm_seeds)
        learn.current_fit(cfg, out)
        if fit_sha256 != learn.digest(fit_path):
            raise ValueError('Copy or fit changed during practice. Run practice again.')
        plan_sha256 = learn.digest(candidate)
        candidate.replace(out/'plan.add.xml')
    diffs = [a['all_requested_delay_s']-b['all_requested_delay_s'] for a, b in zip(after, before)]
    test = wilcoxon(diffs, alternative='less') if any(diffs) else None
    old_delay = primary(before)
    gain = -statistics.mean(diffs)/old_delay if old_delay > 0 else 0.
    p_value = float(test.pvalue) if test else 1.
    clear = best.number != 0 and gain >= MIN_GAIN and p_value < ALPHA and feasible(after, before)
    result = dict(road=name, fit_sha256=fit_sha256, plan_sha256=plan_sha256,
                  approach_regressions=regressions(after, before), trials=trials,
                  search_seeds=list(search_seeds), confirm_seeds=list(confirm_seeds),
                  best_trial=best.number, best_search_delay_s=best.value, old_search_delay_s=primary(base),
                  params=best.params, old_params={k: v for k, v in old.items() if searched(k)},
                  confirm_old=before, confirm_new=after, confirm_diffs_s=diffs, confirm_gain=gain,
                  confirm_p=p_value, confirm_feasible=feasible(after, before), clear_gain=clear,
                  settings=dict(min_gain=MIN_GAIN, alpha=ALPHA, side_limit=SIDE_LIMIT, teleport_margin=TELEPORT_MARGIN,
                                sampler='TPE seed 0', max_parallel_sims=road.MAX_SIMS),
                  wall_s=time.monotonic()-start)
    (out/'practice.json').write_text(json.dumps(result, indent=2)+'\n')
    study.trials_dataframe().to_csv(out/'trials.csv', index=False)
    print(f'practice {name}: best trial {best.number}, copy gain {gain:.1%}, p={p_value:.3g}, clear={clear}')
    return result
