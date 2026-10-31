"""Preregistered simulation experiment; run with caffeinate -i and nice -n 15."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
from statistics import mean
import sys
import time

from scipy.stats import wilcoxon
from signal_lab import advisor as a, closed_loop as c, evaluate as e, feed as f, pipeline as p
from tools.advisor_profiles import signals

ROOT = p.ROOT/'reports/advisor_loop'


def fit_light():
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(lambda seed: c.run('all_drop', seed, 'fixed_v5', ROOT/f'profile_seed{seed}'), range(5)))
    samples = {name: signals(scenario) for name, scenario in
               (('pm', 'calm'), ('night', 'night'), ('east_surge', 'east_surge'))}
    samples['light'] = []
    for seed in range(5):
        # Same detector-file occupancy as the other profiles.
        folder = ROOT/f'profile_seed{seed}'
        _, ids, _ = f.feed_detectors(folder)
        p.write_csv(folder/'feed_file.csv', f.feed_rows(folder/'counts.xml', ids, 59400, 66600))
        rows = a.read_feed(folder/'feed_file.csv')
        for time in sorted({r.window_end for r in rows})[2:]:
            samples['light'].append(a.smooth([r for r in rows if time-3*a.WINDOW < r.window_end <= time]))
    calibration = json.loads(a.CALIBRATION.read_text())
    calibration['profiles'] = list(samples)
    calibration['plans']['light'] = dict(profile='light', path='sim/tls_advisor_light.add.xml')
    for feature in calibration['features']:
        key = tuple(feature['approach'])
        feature['profiles'] = {name: [mean(s[key][j] for s in ss) for j in range(2)] for name, ss in samples.items()}
        feature['scale'] = [max(s[key][j] for ss in samples.values() for s in ss)
                            -min(s[key][j] for ss in samples.values() for s in ss) for j in range(2)]
    calibration['margins'] = {}
    for source, ss in samples.items():
        scores = [a.distances(signal, calibration) for signal in ss]
        calibration['margins'][source] = {target: max(0., max(s[source]-s[target] for s in scores)) for target in samples}
    calibration['provenance'] += '; light: full PM all_drop v5 feed seeds 0–4; same range/margin procedure'
    a.CALIBRATION.write_text(json.dumps(calibration, indent=2)+'\n')


def sanity():
    begin = 59400
    stop = begin+600
    folder = ROOT/'sanity_short'
    rows = c.run('calm', 0, 'fixed_v5', folder, stop=stop)
    _, ids, _ = f.feed_detectors(folder)
    xml = f.feed_rows(folder/'counts.xml', ids, begin, stop)
    assert len(rows) == len(xml)
    errors = []
    for live, disk in zip(rows, xml):
        assert {k: v for k, v in live.items() if k != 'occupancy'} == {k: v for k, v in disk.items() if k != 'occupancy'}, (live, disk)
        errors.append(abs(live['occupancy']-disk['occupancy']))
    error = max(errors)
    assert error <= 3 and mean(errors) <= 1, (error, mean(errors))
    fixed = c.run('calm', 0, 'fixed_v5', ROOT/'sanity_full')
    legacy = e.simulate('pm_peak', 'optuna_v5', 0, p.config(), e.boundaries(p.config()))[0]
    keys = [k for k in legacy if k in fixed and k not in ('controller', 'scenario')]
    assert all(fixed[k] == legacy[k] for k in keys), {k: (fixed[k], legacy[k]) for k in keys if fixed[k] != legacy[k]}
    result = dict(feed_rows=len(rows), max_occupancy_error_pp=error, mean_occupancy_error_pp=mean(errors), metrics_equal=keys)
    (ROOT/'sanity.json').write_text(json.dumps(result, indent=2)+'\n')
    print('SANITY PASSED', result, flush=True)


def paired_results(rows):
    tests = []
    for scenario in c.SCENARIOS:
        arms = {arm: {r['seed']: r for r in rows if r['scenario'] == scenario and r['controller'] == arm}
                for arm in ('fixed_v5', 'advisor')}
        assert set(arms['fixed_v5']) == set(arms['advisor']) == set(range(103, 123))
        diffs = [arms['advisor'][s]['all_requested_delay_s']-arms['fixed_v5'][s]['all_requested_delay_s'] for s in range(103, 123)]
        test = wilcoxon(diffs, alternative='less', method='auto') if any(diffs) else None
        metrics = ('all_requested_delay_s', 'unfinished', 'teleports', 'mainline_travel_eb_s',
                   'mainline_travel_wb_s', 'side_all_requested_delay_s', 'worst_origin_delay_s',
                   'switches', 'recommendations', 'false_switches')
        averages = {arm: {k: mean(r[k] for r in ss.values()) for k in metrics} for arm, ss in arms.items()}
        tests.append(dict(scenario=scenario, n=20, p_value=float(test.pvalue) if test else 1.,
                          statistic=float(test.statistic) if test else 0., means=averages,
                          change={k: averages['advisor'][k]-averages['fixed_v5'][k] for k in metrics}))
    adjusted = 0.
    for rank, test in enumerate(sorted(tests, key=lambda t: t['p_value'])):
        adjusted = max(adjusted, min(1., (4-rank)*test['p_value']))
        test['adjusted_p'] = adjusted
        test['significant'] = adjusted < .05
    return tests


def experiment():
    output = p.ROOT/'reports/results_advisor.csv'
    if output.exists() or (ROOT/'TEST_STARTED').exists():
        raise RuntimeError('Final test already started; refusing rerun')
    calibration = json.loads(a.CALIBRATION.read_text())
    jobs = [(scenario, seed, arm) for scenario in c.SCENARIOS for seed in range(5)
            for arm in ('fixed_v5', 'advisor')]
    def execute(job):
        scenario, seed, arm = job
        row = c.run(scenario, seed, arm, ROOT/f'{scenario}_{seed}_{arm}', calibration)
        print('complete', *job, 'switches', row['switches'], flush=True)
        return row
    with ThreadPoolExecutor(max_workers=3) as pool:
        development = list(pool.map(execute, jobs))
    p.write_csv(ROOT/'development.csv', development)
    files = ['src/signal_lab/advisor.py', 'src/signal_lab/advisor_profiles.json', 'src/signal_lab/closed_loop.py',
             'tools/eval_advisor.py', 'docs/PREREGISTRATION-ADVISOR.md', 'sim/routes_pm_peak.rou.xml',
             'sim/corridor.net.xml', 'config/corridor.yaml']
    files += list({spec['path'] for spec in calibration['plans'].values()})
    hashes = {path: hashlib.sha256((p.ROOT/path).read_bytes()).hexdigest() for path in files}
    (ROOT/'TEST_STARTED').write_text(json.dumps(hashes, indent=2)+'\n')
    start = time.monotonic()
    jobs = [(scenario, seed, arm) for scenario in c.SCENARIOS for seed in range(103, 123)
            for arm in ('fixed_v5', 'advisor')]
    rows = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        for row in pool.map(execute, jobs):
            rows.append(row)
            p.write_csv(output, rows)
    assert len(rows) == 160
    assert hashes == {path: hashlib.sha256((p.ROOT/path).read_bytes()).hexdigest() for path in files}
    result = dict(seeds=list(range(103, 123)), fit_seeds=list(range(5)), workers=3,
                  primary='full PM all_requested_delay_s', alternative='less', alpha=.05,
                  correction='Holm across four scenarios', tests=paired_results(rows), sha256=hashes,
                  sanity=json.loads((ROOT/'sanity.json').read_text()), wall_s=time.monotonic()-start,
                  disruption='All five programs restart at phase 0 and nominal phase duration. Configured offsets retained; phase continuity and immediate coordination lost. Abrupt clearance/green truncation possible. Not field-deployable.',
                  logs='reports/advisor_loop/<scenario>_<seed>_<arm>/events.jsonl',
                  development_switches=sum(r['switches'] for r in development))
    (p.ROOT/'reports/eval_advisor.json').write_text(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__':
    {'sanity': sanity, 'fit': fit_light, 'test': experiment}[sys.argv[1]]()
