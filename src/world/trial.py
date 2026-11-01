"""Dev check and the preregistered held-out test: old timing vs learner plan in the hidden world."""
from concurrent.futures import ThreadPoolExecutor
import json
import statistics
import subprocess
import tempfile
import time
from pathlib import Path

from scipy.stats import wilcoxon

from learner import card, learn, practice, road
from signal_lab import pipeline as p
from . import worlds as w

DEV_ROADS, HELDOUT_ROADS = ('stevens_creek', 'homestead'), ('wolfe', 'deanza')
DEV_SEEDS, DEV_GOBACK_SEEDS = range(300, 310), range(300, 305)
TEST_SEEDS, TEST_GOBACK_SEEDS = range(200, 220), range(220, 230)
METRICS = ('all_requested_delay_s', 'unfinished', 'teleports', 'worst_origin_delay_s')
# Go-back pass mark: the bad plan is undone on at least 80% of seeds; a no-op change on at most 20%.
BAD_MIN, NOOP_MAX = .8, .2
HELDOUT = road.OUT.parent/'learner_heldout'


def run_learner(name, allow_heldout=False):
    """watch -> learn -> practice -> recommend, with wall time per step."""
    if road.load(name)['role'] == 'heldout' and not allow_heldout:
        raise RuntimeError(f'{name} is held out; only the preregistered test may run the learner on it')
    steps = {}
    for step, call in (('watch', w.watch), ('learn', learn.learn), ('practice', practice.practice),
                       ('recommend', card.recommend)):
        start = time.monotonic()
        call(name)
        steps[step] = round(time.monotonic()-start, 1)
    (road.OUT/name/'timing.json').write_text(json.dumps(steps, indent=2)+'\n')
    return steps


def arms(name):
    cfg = road.load(name)
    change = json.loads((road.OUT/name/'card.json').read_text())['decision'] == 'change'
    timings = {'old': road.file(cfg, 'old_timing'), 'learner': road.OUT/name/'plan.add.xml' if change else None}
    if name == 'stevens_creek':
        timings['v5'] = p.ROOT/'sim/tls_optuna_v5_pm_peak.add.xml'
    return cfg, timings


def compare(name, seeds):
    """Paired runs per seed. A 'no change' card means the learner arm is the old timing, so no gain."""
    cfg, timings = arms(name)
    jobs = [(arm, seed) for arm, timing in timings.items() if timing for seed in seeds]
    results = road.many([(cfg, w.routes(name), timings[arm], seed) for arm, seed in jobs])
    rows = [dict(road=name, arm=arm, seed=seed, **{k: s[k] for k in METRICS}) for (arm, seed), (s, _) in zip(jobs, results)]
    if timings['learner'] is None:
        rows += [{**r, 'arm': 'learner'} for r in rows if r['arm'] == 'old']
    return rows


def summary(rows, arm):
    by = lambda a: {r['seed']: r for r in rows if r['arm'] == a}
    old, new = by('old'), by(arm)
    out = {}
    for metric in METRICS:
        values = [new[s][metric] for s in sorted(old)]
        diffs = [new[s][metric]-old[s][metric] for s in sorted(old)]
        test = wilcoxon(diffs, alternative='less') if any(diffs) else None
        out[metric] = dict(mean=statistics.mean(values), sd=statistics.pstdev(values), diff_mean=statistics.mean(diffs),
                           diff_sd=statistics.pstdev(diffs), diff_min=min(diffs), diff_max=max(diffs),
                           p_less=float(test.pvalue) if test else 1.)
    return out


def go_back(name, seeds):
    """Bad plan and a no-op change applied at 17:00; the learner's rule reads the feed and may go back."""
    cfg = road.load(name)
    with tempfile.TemporaryDirectory() as temp:
        plans = {'bad': Path(temp)/'bad.xml', 'noop': Path(temp)/'noop.xml'}
        w.bad_plan(cfg, plans['bad'])
        w.noop_plan(cfg, plans['noop'])
        with ThreadPoolExecutor(max_workers=road.MAX_SIMS) as pool:
            runs = list(pool.map(lambda job: w.check_run(name, plans[job[0]], *job), [(k, s) for k in plans for s in seeds]))
    rate = lambda k: statistics.mean(r['go_back'] for r in runs if r['program'] == k)
    mean = lambda k, arm: statistics.mean(r[arm]['all_requested_delay_s'] for r in runs if r['program'] == k)
    return dict(runs=runs, bad_go_back_rate=rate('bad'), noop_go_back_rate=rate('noop'),
                bad_held_delay_s=mean('bad', 'held'), bad_with_rule_delay_s=mean('bad', 'with_rule'),
                passed=rate('bad') >= BAD_MIN and rate('noop') <= NOOP_MAX
                and mean('bad', 'with_rule') < mean('bad', 'held'))


def dev_check(name):
    if name not in DEV_ROADS:
        raise ValueError('Dev check runs on dev roads only')
    start = time.monotonic()
    rows = compare(name, DEV_SEEDS)
    result = dict(road=name, seeds=list(DEV_SEEDS), arms={a: summary(rows, a) for a in {r['arm'] for r in rows} if a != 'old'},
                  old=summary(rows, 'old'), go_back=go_back(name, DEV_GOBACK_SEEDS), copy_vs_truth=w.truth_fit(name))
    result['wall_s'] = time.monotonic()-start
    out = w.TRUTH/name
    out.mkdir(parents=True, exist_ok=True)
    p.write_csv(out/'dev_check.csv', rows)
    (out/'dev_check.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


def holm(p_values):
    order = sorted(range(len(p_values)), key=p_values.__getitem__)
    adjusted, running = [0.]*len(p_values), 0.
    for rank, i in enumerate(order):
        running = max(running, min(1., (len(p_values)-rank)*p_values[i]))
        adjusted[i] = running
    return adjusted


def frozen_since_preregistration():
    """Learner, world and test code must be unchanged since the preregistration commit."""
    commit = subprocess.check_output(['git', 'log', '-1', '--format=%H', '--', 'docs/PREREGISTRATION-LEARNER.md'],
                                     cwd=p.ROOT, text=True).strip()
    if not commit:
        raise RuntimeError('Preregistration is not committed')
    changed = subprocess.run(['git', 'diff', '--quiet', commit, '--', 'src', 'roads', 'tools/learner.py'], cwd=p.ROOT)
    if changed.returncode:
        raise RuntimeError(f'Code or roads changed since preregistration {commit[:7]}; refusing')
    return commit


def heldout_test():
    """The one preregistered run. Refuses once any result exists."""
    if HELDOUT.exists():
        raise RuntimeError(f'Held-out results already exist in {HELDOUT}; refusing to rerun')
    commit = frozen_since_preregistration()
    HELDOUT.mkdir(parents=True)
    start, rows, roads = time.monotonic(), [], {}
    for name in HELDOUT_ROADS:
        road_start = time.monotonic()
        w.build_world(name)
        steps = run_learner(name, allow_heldout=True)
        pairs = compare(name, TEST_SEEDS)
        rows += pairs
        p.write_csv(HELDOUT/'results.csv', rows)
        roads[name] = dict(decision=json.loads((road.OUT/name/'card.json').read_text())['decision'],
                           learner=summary(pairs, 'learner'), go_back=go_back(name, TEST_GOBACK_SEEDS),
                           copy_vs_truth=w.truth_fit(name), steps_s=steps, wall_s=time.monotonic()-road_start)
    primary = [roads[n]['learner']['all_requested_delay_s']['p_less'] for n in HELDOUT_ROADS]
    for name, adjusted in zip(HELDOUT_ROADS, holm(primary)):
        roads[name]['holm_p'] = adjusted
        roads[name]['learner_beat_old'] = adjusted < .05
    result = dict(preregistration_commit=commit, seeds=list(TEST_SEEDS), goback_seeds=list(TEST_GOBACK_SEEDS),
                  roads=roads, wall_s=time.monotonic()-start)
    (HELDOUT/'results.json').write_text(json.dumps(result, indent=2)+'\n')
    return result
