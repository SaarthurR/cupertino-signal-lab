"""One-shot fresh synthetic validation: python -m tools.validate_learner.

Geometry is public OSM; all traffic is synthetic. Fixed profiles are reported separately,
not treated as independent observed days. Existing research reports are never written.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import statistics
import sys
import time

import optuna

from learner import card, learn, practice, road
from signal_lab import baseline, pipeline as p
from world import roads, worlds

OUT = p.ROOT/'reports/repair_validation'
SPECS = {
    'validation_bubb': dict(role='heldout', street='Bubb Road', search=(-122.056, 37.300, -122.049, 37.317),
                           signals={'North signal': ['65566258'], 'South signal': ['65645389']}),
    'validation_stelling': dict(role='heldout', street='South Stelling Road', search=(-122.043, 37.300, -122.039, 37.318),
                               signals={'North signal': ['13044640725', '13044640726'], 'South signal': ['65566742']}),
}
WORLD_SEEDS = dict(zip(SPECS, (31010, 31011)))
WATCH_PROFILES = tuple(range(5000, 5010))
WATCH_DRIVERS = tuple(range(1000, 1010))
TEST_PROFILES = tuple(range(6000, 6003))
TEST_DRIVERS = tuple(range(7000, 7010))
SEARCH_SEEDS = tuple(range(3))
CONFIRM_SEEDS = tuple(range(10, 20))
METRICS = ('all_requested_delay_s', 'all_requested_delay_0_s', 'all_requested_delay_1800_s',
           'unfinished', 'teleports', 'worst_origin_delay_s')
_ACTIVE = None
_HOOK_INSTALLED = False


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')
    temp.replace(path)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes():
    files = sorted((p.ROOT/'src').rglob('*.py'))+[Path(__file__).resolve()]
    return {str(path.resolve().relative_to(p.ROOT.resolve())): digest(path) for path in files}


def refuse_repeat():
    if OUT.is_symlink():
        raise RuntimeError('Validation output must not be a symbolic link')
    if OUT.exists() and any(OUT.iterdir()):
        raise RuntimeError(f'Validation files already exist in {OUT}; refusing to overwrite or retry')
    for name in SPECS:
        if (roads.ROADS/name).exists() or (worlds.WORLDS/name).exists():
            raise RuntimeError(f'Fresh road inputs already exist for {name}; refusing to overwrite')


def protocol(trials, inputs=True, prepared=None, failures=None):
    if trials < 1:
        raise ValueError('trials must be positive')
    if not 1 <= road.MAX_SIMS <= 3:
        raise ValueError('Validation requires at most three parallel simulations')
    files = {}
    prepared = list(SPECS) if prepared is None else prepared
    for name in prepared if inputs else ():
        cfg = road.load(name)
        paths = [roads.ROADS/name/'road.yaml', worlds.routes(name)]
        paths += [road.file(cfg, key) for key in ('net', 'old_timing', 'detectors', 'timing_inputs')]
        paths += sorted((OUT/'evaluation_inputs'/name).glob('*'))
        files.update({str(path.relative_to(p.ROOT)): digest(path) for path in paths})
    for name in (failures or {}) if inputs else ():
        for path in sorted((roads.ROADS/name).rglob('*')):
            if path.is_file():
                files[str(path.relative_to(p.ROOT))] = digest(path)
    return dict(label='FRESH SYNTHETIC VALIDATION' if trials == 150 else 'SMOKE ONLY: not the independent 150-trial test',
                roads=SPECS, prepared_roads=prepared, preparation_failures=failures or {},
                world_seeds=WORLD_SEEDS, source_sha256=source_hashes(), input_sha256=files,
                trials_per_sampler=trials, samplers={'tpe': 'TPESampler(seed=0)', 'random': 'RandomSampler(seed=0)'},
                watch_profiles=list(WATCH_PROFILES), watch_driver_seeds=list(WATCH_DRIVERS),
                test_profiles=list(TEST_PROFILES), test_driver_seeds=list(TEST_DRIVERS),
                search_seeds=list(SEARCH_SEEDS), confirm_seeds=list(CONFIRM_SEEDS),
                screening_limits=learn.SCREENING, max_parallel_sims=road.MAX_SIMS, child_nice=15,
                metrics=dict(primary_900_s='all_requested_delay_s', sensitivity_0_s='all_requested_delay_0_s',
                             sensitivity_1800_s='all_requested_delay_1800_s', individual_origins='origin_delay_s'),
                rollback_criteria=dict(bad_min=.8, noop_max=.2, rule_delay_must_improve_bad=True),
                limits='Up to two preregistered OSM geometries; unsupported geometry is reported, not silently removed. '
                       'Synthetic per-origin factors, three fixed evaluation profiles. '
                       'Descriptive paired means only; no city or field improvement claim. '
                       'Mean +/- watched count SD copies are stress cases, not confidence intervals.')


def verify_frozen(frozen):
    if source_hashes() != frozen['source_sha256']:
        raise RuntimeError('Source changed after protocol freeze; validation cannot be reported as frozen')
    for relative, expected in frozen['input_sha256'].items():
        if digest(p.ROOT/relative) != expected:
            raise RuntimeError(f'Frozen input changed: {relative}')


@contextmanager
def learner_output(folder):
    """Confine learner outputs and reject reads of hidden demand or other report roots."""
    global _ACTIVE, _HOOK_INSTALLED
    if not _HOOK_INSTALLED:
        def audit(event, args):
            if _ACTIVE is None or event != 'open' or not isinstance(args[0], (str, bytes, Path)):
                return
            path = Path(os.fsdecode(args[0])).resolve()
            protected = (worlds.WORLDS.resolve(), (p.ROOT/'reports').resolve())
            if any(path == root or root in path.parents for root in protected) and not (path == _ACTIVE or _ACTIVE in path.parents):
                raise PermissionError(f'Learner attempted to access hidden or unrelated reports: {path}')
        sys.addaudithook(audit)
        _HOOK_INSTALLED = True
    previous, active = road.OUT, _ACTIVE
    road.OUT, _ACTIVE = folder, folder.resolve()
    try:
        yield
    finally:
        road.OUT, _ACTIVE = previous, active


def paired_summary(rows, arm):
    """Describe matched seeds in one fixed profile, with individual origin groups retained."""
    old = {r['seed']: r['metrics'] for r in rows if r['arm'] == 'old'}
    new = {r['seed']: r['metrics'] for r in rows if r['arm'] == arm}
    if not old or old.keys() != new.keys():
        raise ValueError('Summary requires complete paired seeds')
    if len(old) != sum(r['arm'] == 'old' for r in rows) or len(new) != sum(r['arm'] == arm for r in rows):
        raise ValueError('Duplicate paired seeds')
    groups = set().union(*(s['origin_delay_s'] for s in old.values()))
    if any(set(s['origin_delay_s']) != groups for s in [*old.values(), *new.values()]):
        raise ValueError('Origin groups must match across every paired run')

    def describe(values, prior):
        diffs = [a-b for a, b in zip(values, prior)]
        return dict(mean=statistics.mean(values), old_mean=statistics.mean(prior),
                    diff_mean=statistics.mean(diffs), diff_min=min(diffs), diff_max=max(diffs),
                    per_seed_diff={str(seed): diff for seed, diff in zip(sorted(old), diffs)})
    summary = {key: describe([new[s][key] for s in sorted(old)], [old[s][key] for s in sorted(old)]) for key in METRICS}
    summary['origin_delay_s'] = {g: describe([new[s]['origin_delay_s'][g] for s in sorted(old)],
                                            [old[s]['origin_delay_s'][g] for s in sorted(old)]) for g in sorted(groups)}
    return summary


def rollback_summary(runs):
    by = lambda program: {r['seed']: r for r in runs if r['program'] == program}
    bad, noop = by('bad'), by('noop')
    if not bad or bad.keys() != noop.keys() or len(runs) != 2*len(bad):
        raise ValueError('Rollback summary requires unique paired bad/no-op seeds')
    bad_rate = statistics.mean(r['go_back'] for r in bad.values())
    noop_rate = statistics.mean(r['go_back'] for r in noop.values())
    paired = [dict(seed=s, bad_rule_vs_held_s=bad[s]['with_rule']['all_requested_delay_s']-bad[s]['held']['all_requested_delay_s'],
                   bad_rule_vs_noop_s=bad[s]['with_rule']['all_requested_delay_s']-noop[s]['held']['all_requested_delay_s'],
                   noop_rule_vs_noop_s=noop[s]['with_rule']['all_requested_delay_s']-noop[s]['held']['all_requested_delay_s'],
                   undo_after_change_s=(bad[s]['time_s']-bad[s]['change_s']) if bad[s]['go_back'] else None)
              for s in sorted(bad)]
    improvement = statistics.mean(r['bad_rule_vs_held_s'] for r in paired)
    return dict(bad_go_back_rate=bad_rate, noop_go_back_rate=noop_rate, paired=paired,
                mean_bad_rule_vs_held_s=improvement,
                mean_bad_rule_vs_noop_s=statistics.mean(r['bad_rule_vs_noop_s'] for r in paired),
                mean_noop_rule_vs_noop_s=statistics.mean(r['noop_rule_vs_noop_s'] for r in paired),
                passed=bad_rate >= .8 and noop_rate <= .2 and improvement < 0)


def prepare():
    roads.SPECS.update(SPECS)
    worlds.SEEDS.update(WORLD_SEEDS)
    prepared, failures = [], {}
    for name in SPECS:
        print(f'prepare {name}', flush=True)
        try:
            roads.build_road(name)
            worlds.build_world(name)
            cfg = road.load(name)
            folder = OUT/'evaluation_inputs'/name
            folder.mkdir(parents=True)
            for seed in (*WATCH_PROFILES, *TEST_PROFILES):
                factors = worlds.stale_routes(cfg, worlds.routes(name), seed, folder/f'{seed}.rou.xml')
                write(folder/f'{seed}.factors.json', factors)
            prepared.append(name)
        except (OSError, ValueError, RuntimeError) as exc:
            failures[name] = dict(error_type=type(exc).__name__, error=str(exc))
            write(OUT/'preparation_failures.json', failures)
            print(f'{name}: preparation failed, retained as evidence: {exc}', flush=True)
    if not prepared:
        raise RuntimeError('No fresh road passed preparation; see preparation_failures.json')
    return prepared, failures


def watch(name):
    cfg = road.load(name)
    observed = OUT/'observed'
    for day, (profile, driver) in enumerate(zip(WATCH_PROFILES, WATCH_DRIVERS)):
        _, (feed, lanes) = road.simulate(cfg, OUT/'evaluation_inputs'/name/f'{profile}.rou.xml',
                                        road.file(cfg, 'old_timing'), driver, True)
        folder = observed/name/'feed'/f'seed{day}'
        folder.mkdir(parents=True)
        p.write_csv(folder/'feed.csv', feed)
        p.write_csv(folder/'lanes.csv', lanes)
    with learner_output(observed):
        return learn.learn(name)


def strategies(name, trials):
    selections, decisions = {}, {}
    for strategy, sampler in [('tpe', optuna.samplers.TPESampler(seed=0)), ('random', optuna.samplers.RandomSampler(seed=0))]:
        folder = OUT/'strategies'/strategy
        shutil.copytree(OUT/'observed'/name, folder/name)
        print(f'{name}: {strategy}, {trials} trials unless copy screening blocks search', flush=True)
        with learner_output(folder):
            result = practice.practice(name, trials=trials, search_seeds=SEARCH_SEEDS, confirm_seeds=CONFIRM_SEEDS, sampler=sampler)
            recommendation = card.recommend(name)
        decisions[strategy] = dict(decision=recommendation['decision'], quality_gate=result['quality_gate'],
                                   trials=result['trials'], confirm_gain=result['confirm_gain'],
                                   confirm_p=result['confirm_p'], stress_copies=result.get('stress_copies', []))
        selections[strategy] = folder/name/'plan.add.xml' if recommendation['decision'] == 'change' else road.file(road.load(name), 'old_timing')
    return selections, decisions


def evaluate(name, selections):
    cfg = road.load(name)
    result = {}
    for profile in TEST_PROFILES:
        print(f'{name}: evaluate fixed profile {profile}', flush=True)
        demand = OUT/'evaluation_inputs'/name/f'{profile}.rou.xml'
        folder = OUT/'evaluation'/name/str(profile)
        folder.mkdir(parents=True)
        fresh = folder/'fresh.add.xml'
        baseline.actuated(road.file(cfg, 'net'), demand, road.window(cfg)[0],
                          [s['sumo_tls_id'] for s in cfg['signals']], cfg['mainline_edges'],
                          road.file(cfg, 'timing_inputs'), fresh)
        timings = dict(old=road.file(cfg, 'old_timing'), **selections, fresh=fresh)
        rows = []
        for seed in TEST_DRIVERS:
            paths = list(dict.fromkeys(timings.values()))
            metrics = road.many([(cfg, demand, path, seed) for path in paths])
            by_path = {path: stats for path, (stats, _) in zip(paths, metrics)}
            rows.extend(dict(seed=seed, arm=arm, metrics=by_path[path]) for arm, path in timings.items())
            write(folder/'metrics.json', rows)
        bad, noop = folder/'bad.add.xml', folder/'noop.add.xml'
        worlds.bad_plan(cfg, bad)
        worlds.noop_plan(cfg, noop)
        jobs = [(program, path, seed) for seed in TEST_DRIVERS for program, path in [('bad', bad), ('noop', noop)]]
        runs = []
        previous = road.OUT
        road.OUT = OUT/'strategies/tpe'
        try:
            with ThreadPoolExecutor(max_workers=road.MAX_SIMS) as pool:
                futures = [pool.submit(worlds.check_run, name, path, program, seed, demand=demand) for program, path, seed in jobs]
                for future in futures:
                    runs.append(future.result())
                    write(folder/'rollback.json', runs)
        finally:
            road.OUT = previous
        result[str(profile)] = dict(arms={arm: paired_summary(rows, arm) for arm in timings},
                                    rollback=rollback_summary(runs))
        write(folder/'summary.json', result[str(profile)])
    return result


def run(trials=150):
    if trials < 1:
        raise ValueError('trials must be positive')
    refuse_repeat()
    OUT.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    try:
        write(OUT/'protocol.json', dict(protocol(trials, inputs=False), preparation_only=True))
        prepared, failures = prepare()
        frozen = protocol(trials, prepared=prepared, failures=failures)
        write(OUT/'protocol.json', frozen)
        results = {}
        for name in prepared:
            verify_frozen(frozen)
            print(f'{name}: observe ten synthetic demand profiles', flush=True)
            fit = watch(name)
            selections, decisions = strategies(name, trials)
            verify_frozen(frozen)
            results[name] = dict(copy_screening=fit['quality_gate'], strategies=decisions,
                                 fixed_test_profiles=evaluate(name, selections))
            write(OUT/f'{name}.json', results[name])
        verify_frozen(frozen)
        final = dict(label=frozen['label'], protocol_sha256=digest(OUT/'protocol.json'), roads=results,
                     wall_s=time.monotonic()-start, limits=frozen['limits'])
        write(OUT/'results.json', final)
        return final
    except Exception as exc:
        write(OUT/'failure.json', dict(error_type=type(exc).__name__, error=str(exc), wall_s=time.monotonic()-start))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trials', type=int, default=150, help='positive trial count; values other than 150 are SMOKE ONLY')
    args = parser.parse_args()
    run(args.trials)


if __name__ == '__main__':
    main()
