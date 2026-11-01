"""Practice in the copy only: Optuna TPE over bounded max greens, cycle and offsets of the old timing."""
import json
import statistics
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import optuna
from scipy.stats import wilcoxon

from signal_lab import optimize as o, pipeline as p
from . import road

# Frozen learner settings; docs/PREREGISTRATION-LEARNER.md quotes these.
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
    return [{k: v for k, v in s.items() if k != 'origin_delay_s'}
            for s, _ in road.many([(cfg, routes, timing, seed) for seed in seeds])]


def side(stats):
    return sum(s['side_all_requested_delay_s'] or 0 for s in stats)


def feasible(stats, base):
    return (all(s['teleports'] <= b['teleports']+TELEPORT_MARGIN for s, b in zip(stats, base))
            and side(stats) <= SIDE_LIMIT*side(base)+1e-9)


def primary(stats):
    return statistics.mean(s['all_requested_delay_s'] for s in stats)


def practice(name, trials=TRIALS, search_seeds=SEARCH_SEEDS, confirm_seeds=CONFIRM_SEEDS):
    cfg = road.load(name)
    out, start = road.OUT/name, time.monotonic()
    copy, old_timing = out/'copy.rou.xml', road.file(cfg, 'old_timing')
    old = old_params(cfg)
    base = score(cfg, copy, old_timing, search_seeds)
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(sampler=optuna.samplers.TPESampler(seed=0))
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
    gain = -statistics.mean(diffs)/primary(before)
    p_value = float(test.pvalue) if test else 1.
    clear = best.number != 0 and gain >= MIN_GAIN and p_value < ALPHA and feasible(after, before)
    result = dict(road=name, trials=trials, search_seeds=list(search_seeds), confirm_seeds=list(confirm_seeds),
                  best_trial=best.number, best_search_delay_s=best.value, old_search_delay_s=primary(base),
                  params=best.params, old_params={k: v for k, v in old.items() if searched(k)},
                  confirm_old=before, confirm_new=after, confirm_diffs_s=diffs, confirm_gain=gain,
                  confirm_p=p_value, confirm_feasible=feasible(after, before), clear_gain=clear,
                  settings=dict(min_gain=MIN_GAIN, alpha=ALPHA, side_limit=SIDE_LIMIT, teleport_margin=TELEPORT_MARGIN,
                                sampler='TPE seed 0', max_parallel_sims=road.MAX_SIMS),
                  wall_s=time.monotonic()-start)
    (out/'practice.json').write_text(json.dumps(result, indent=2)+'\n')
    study.trials_dataframe().drop(columns=['user_attrs_stats'], errors='ignore').to_csv(out/'trials.csv', index=False)
    print(f'practice {name}: best trial {best.number}, copy gain {gain:.1%}, p={p_value:.3g}, clear={clear}')
    return result
