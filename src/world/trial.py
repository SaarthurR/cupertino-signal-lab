"""Dev check and the preregistered held-out test: old timing vs learner plan in the hidden world."""
from concurrent.futures import as_completed, ThreadPoolExecutor
import csv
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
ARM_ORDER = {'old': 0, 'learner': 1, 'v5': 2, 'fresh': 3}


def _write_json(path, value):
    path = Path(path)
    temp = path.with_name(path.name+'.tmp')
    temp.write_text(json.dumps(value, indent=2)+'\n')
    temp.replace(path)


def _write_csv(path, rows):
    path = Path(path)
    temp = path.with_name(path.name+'.tmp')
    p.write_csv(temp, rows)
    temp.replace(path)


def _row_key(row):
    return row['road'], ARM_ORDER.get(row['arm'], len(ARM_ORDER)), row['seed']


def run_learner(name, allow_heldout=False, completed=None, on_step=None):
    """watch -> learn -> practice -> recommend, with wall time per step."""
    if road.load(name)['role'] == 'heldout' and not allow_heldout:
        raise RuntimeError(f'{name} is held out; only the preregistered test may run the learner on it')
    steps = dict(completed or {})
    for step, call in (('watch', w.watch), ('learn', learn.learn), ('practice', practice.practice),
                       ('recommend', card.recommend)):
        if step in steps:
            continue
        start = time.monotonic()
        call(name)
        steps[step] = round(time.monotonic()-start, 1)
        if on_step:
            on_step(step, steps[step])
    (road.OUT/name/'timing.json').write_text(json.dumps(steps, indent=2)+'\n')
    return steps


def arms(name):
    cfg = road.load(name)
    if name in HELDOUT_ROADS:
        change = json.loads((road.OUT/name/'card.json').read_text())['decision'] == 'change'
        selected = road.OUT/name/'plan.add.xml' if change else None
    else:
        selected = card.selected_plan(name, cfg)
    timings = {'old': road.file(cfg, 'old_timing'), 'learner': selected}
    fresh = w.TRUTH/name/'fresh_timing.add.xml'
    if fresh.exists():
        timings['fresh'] = fresh
    if name == 'stevens_creek':
        timings['v5'] = p.ROOT/'sim/tls_optuna_v5_pm_peak.add.xml'
    return cfg, timings


def _read_rows(path):
    if not path or not Path(path).exists():
        return []
    with open(path) as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        row['seed'] = int(row['seed'])
        for metric in METRICS:
            row[metric] = int(row[metric]) if metric in ('unfinished', 'teleports') else float(row[metric])
    return rows


def compare(name, seeds, checkpoint=None):
    """Paired runs per seed. A 'no change' card means the learner arm is the old timing, so no gain."""
    cfg, timings = arms(name)
    rows = _read_rows(checkpoint)
    for seed in seeds:
        present = {(r['arm'], r['seed']) for r in rows if r['road'] == name}
        jobs = [(arm, seed) for arm, timing in timings.items() if timing and (arm, seed) not in present]
        results = road.many([(cfg, w.routes(name), timings[arm], seed) for arm, seed in jobs]) if jobs else []
        rows += [dict(road=name, arm=arm, seed=seed, **{k: s[k] for k in METRICS})
                 for (arm, seed), (s, _) in zip(jobs, results)]
        if timings['learner'] is None and ('learner', seed) not in present:
            rows.append({**next(r for r in rows if r['road'] == name and r['arm'] == 'old' and r['seed'] == seed),
                         'arm': 'learner'})
        if checkpoint:
            _write_csv(checkpoint, sorted(rows, key=_row_key))
    return sorted((r for r in rows if r['road'] == name and r['seed'] in seeds), key=_row_key)


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


def alarm_summary(runs, seeds):
    """Compare alarms with measured harm in an independently scored no-op pair."""
    seeds = set(seeds)
    pairs = {(r['program'], r['seed']): r for r in runs}
    if not seeds or len(pairs) != len(runs) or pairs.keys() != {(arm, s) for arm in ('bad', 'noop') for s in seeds}:
        raise ValueError('Alarm evaluation needs every paired bad and no-op run exactly once')
    score = 'all_requested_delay_s'
    bad = [pairs['bad', s] for s in sorted(seeds)]
    noop = [pairs['noop', s] for s in sorted(seeds)]
    harmful = [r for r, control in zip(bad, noop) if r['held'][score] > control['held'][score]]
    harmless = [r for r in bad if r not in harmful]
    detected = sum(r['alarm'] for r in harmful)
    false_alarms = sum(r['alarm'] for r in noop)
    other_false_alarms = sum(r['alarm'] for r in harmless)
    restore = all(r['program_changes'] for r in runs)
    return dict(pairs=len(seeds), harmful=len(harmful), detected=detected, noop_alarms=false_alarms,
                harmless_candidates=len(harmless), harmless_candidate_alarms=other_false_alarms,
                improves_harmful=sum(r['with_rule'][score] < r['held'][score] for r in harmful),
                restoration_verified=restore,
                passed=restore and bool(harmful) and detected/len(harmful) >= BAD_MIN
                and false_alarms/len(noop) <= NOOP_MAX
                and (not harmless or other_false_alarms/len(harmless) <= NOOP_MAX))


def go_back(name, seeds, checkpoint=None):
    """Bad plan and a no-op change applied at 17:00; the learner's rule reads the feed and may go back."""
    cfg = road.load(name)
    seeds = tuple(seeds)
    runs = json.loads(Path(checkpoint).read_text()) if checkpoint and Path(checkpoint).exists() else []
    if any('alarm' not in r or not r.get('program_changes') for r in runs):
        raise ValueError('Legacy alarm checkpoint. Use a new output path.')
    with tempfile.TemporaryDirectory() as temp:
        plans = {'bad': Path(temp)/'bad.xml', 'noop': Path(temp)/'noop.xml'}
        w.bad_plan(cfg, plans['bad'])
        w.noop_plan(cfg, plans['noop'])
        with ThreadPoolExecutor(max_workers=road.MAX_SIMS) as pool:
            done = {(r['road'], r['program'], r['seed']) for r in runs}
            futures = {pool.submit(w.check_run, name, plans[k], k, s): (k, s)
                       for k in plans for s in seeds if (name, k, s) not in done}
            error = None
            for future in as_completed(futures):
                try:
                    runs.append(future.result())
                    if checkpoint:
                        _write_json(checkpoint, sorted(runs, key=lambda r: (r['road'], r['program'], r['seed'])))
                except Exception as exc:
                    error = error or exc
            if error:
                raise error
    selected = sorted((r for r in runs if r['road'] == name and r['seed'] in seeds),
                      key=lambda r: (r['program'], r['seed']))
    return dict(runs=selected, **alarm_summary(selected, seeds))


def dev_check(name):
    if name not in DEV_ROADS:
        raise ValueError('Dev check runs on dev roads only')
    start = time.monotonic()
    out = w.TRUTH/name
    w.fresh_plan(name)
    rows = compare(name, DEV_SEEDS)
    arm_names = [a for a in ('v5', 'learner', 'fresh') if any(r['arm'] == a for r in rows)]
    result = dict(road=name, seeds=list(DEV_SEEDS), arms={a: summary(rows, a) for a in arm_names},
                  old=summary(rows, 'old'), go_back=go_back(name, DEV_GOBACK_SEEDS),
                  copy_vs_truth=w.truth_fit(name))
    result['wall_s'] = time.monotonic()-start
    out.mkdir(parents=True, exist_ok=True)
    p.write_csv(out/'dev_check.csv', sorted(rows, key=_row_key))
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
    if changed.returncode == 1:
        raise RuntimeError(f'Code or roads changed since preregistration {commit[:7]}; refusing')
    if changed.returncode:
        raise RuntimeError('Could not verify frozen code')
    untracked = subprocess.check_output(
        ['git', 'ls-files', '--others', '--exclude-standard', '--', 'src', 'roads', 'tools/learner.py'],
        cwd=p.ROOT, text=True).splitlines()
    if untracked:
        raise RuntimeError(f'Untracked code or road file {untracked[0]}; refusing')
    return commit


def heldout_test():
    """The one preregistered run. Completed runs refuse; interrupted runs resume from checkpoints."""
    final = HELDOUT/'results.json'
    if final.exists():
        raise RuntimeError(f'Held-out results already exist in {HELDOUT}; refusing to rerun')
    commit = frozen_since_preregistration()
    progress_path = HELDOUT/'progress.json'
    if HELDOUT.exists() and not progress_path.exists():
        raise RuntimeError(f'Unknown held-out files already exist in {HELDOUT}; refusing')
    HELDOUT.mkdir(parents=True, exist_ok=True)
    if progress_path.exists():
        progress = json.loads(progress_path.read_text())
        if progress['preregistration_commit'] != commit:
            raise RuntimeError('Frozen commit changed during an interrupted held-out run; refusing')
    else:
        progress = dict(preregistration_commit=commit, seeds=list(TEST_SEEDS),
                        goback_seeds=list(TEST_GOBACK_SEEDS), roads={})
        _write_json(progress_path, progress)

    def save():
        _write_json(progress_path, progress)

    start, rows, roads = time.monotonic(), [], {}
    for name in HELDOUT_ROADS:
        state = progress['roads'].setdefault(name, dict(steps_s={}))
        save()
        road_result = HELDOUT/f'{name}.json'
        if state.get('complete') and road_result.exists():
            roads[name] = json.loads(road_result.read_text())
            continue
        road_start = time.monotonic()
        if not state.get('world_built'):
            w.build_world(name)
            state['world_built'] = True
            save()

        def step_done(step, wall_s):
            state['steps_s'][step] = wall_s
            save()

        steps = run_learner(name, allow_heldout=True, completed=state['steps_s'], on_step=step_done)
        if not state.get('fresh_timing_built'):
            w.fresh_plan(name)
            state['fresh_timing_built'] = True
            save()
        pairs = compare(name, TEST_SEEDS, HELDOUT/'results.csv')
        rows += pairs
        roads[name] = dict(decision=json.loads((road.OUT/name/'card.json').read_text())['decision'],
                           learner=summary(pairs, 'learner'), fresh=summary(pairs, 'fresh'),
                           go_back=go_back(name, TEST_GOBACK_SEEDS, HELDOUT/'go_back.json'),
                           copy_vs_truth=w.truth_fit(name), steps_s=steps, wall_s=time.monotonic()-road_start)
        _write_json(road_result, roads[name])
        state['complete'] = True
        save()
    primary = [roads[n]['learner']['all_requested_delay_s']['p_less'] for n in HELDOUT_ROADS]
    for name, adjusted in zip(HELDOUT_ROADS, holm(primary)):
        roads[name]['holm_p'] = adjusted
        roads[name]['learner_beat_old'] = adjusted < .05
    result = dict(preregistration_commit=commit, seeds=list(TEST_SEEDS), goback_seeds=list(TEST_GOBACK_SEEDS),
                  roads=roads, wall_s=time.monotonic()-start)
    _write_json(final, result)
    return result
