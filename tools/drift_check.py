"""Does retuning beat the frozen v5 plan once traffic has lastingly changed? Usage: drift_check.py <case> [trials]"""
from concurrent.futures import ThreadPoolExecutor
import copy
import json
from pathlib import Path
import sys
import tempfile
import xml.etree.ElementTree as ET

import optuna

from signal_lab import feed, optimize as o, pipeline as p

CASES = {'east_growth': (feed.ENTRIES['east_surge'], .3), 'all_drop': (None, -.25)}


def drift_routes(case, output):
    entry, change = CASES[case]
    root = ET.parse(p.ROOT/'sim/routes_pm_peak.rou.xml').getroot()
    before = list(root.findall('vehicle'))
    picked = [v for v in before if entry in (None, v.find('route').get('edges').split()[0])]
    n = round(len(picked)*abs(change))
    for i in range(n):
        vehicle = picked[int((i+.5)*len(picked)/n)]
        if change < 0:
            root.remove(vehicle)
        else:
            clone = copy.deepcopy(vehicle)
            clone.set('id', f'{case}_{i}')
            root.append(clone)
    after = sorted(root.findall('vehicle'), key=lambda v: float(v.get('depart')))
    assert len(after) == len(before)+(n if change > 0 else -n)
    for vehicle in root.findall('vehicle'):
        root.remove(vehicle)
    root.extend(after)
    p.xml_write(root, output)


def main(case, trials=100):
    folder = p.ROOT/f'reports/drift/{case}'
    folder.mkdir(parents=True, exist_ok=True)
    routes = folder/'routes.xml'
    drift_routes(case, routes)
    v5 = p.ROOT/'sim/tls_optuna_v5_pm_peak.add.xml'
    textbook = p.ROOT/'sim/tls_actuated_pm_peak.add.xml'
    def scores(timing, seeds):
        def run(seed):
            with tempfile.TemporaryDirectory() as temp:
                return o.score('pm_peak', seed, timing, temp, routes)
        with ThreadPoolExecutor(max_workers=3) as pool:
            return list(pool.map(run, seeds))
    baseline = scores(v5, range(5))
    study = optuna.create_study(sampler=optuna.samplers.TPESampler(seed=0))
    study.enqueue_trial(json.loads((p.ROOT/'reports/optimize_v5.json').read_text())['best']['params'])
    def objective(trial):
        params = {key: trial.suggest_float(key, *o.bounds(key, 5)) for key in o.baseline_params()}
        with tempfile.TemporaryDirectory() as temp:
            timing = Path(temp)/'plan.xml'
            o.plan('pm_peak', params, timing, 5)
            stats = scores(timing, range(5))
        trial.set_user_attr('stats', stats)
        return o.objective_value(stats, baseline)
    study.optimize(objective, n_trials=trials)
    best = study.best_trial
    candidate = folder/'candidate.add.xml'
    o.plan('pm_peak', best.params, candidate, 5)
    # Seeds 5-12 only: seeds above 102 stay reserved for the closed-loop test.
    ours, stale, book = scores(candidate, range(5, 13)), scores(v5, range(5, 13)), scores(textbook, range(5, 13))
    mean = lambda ss, key: sum(s[key] for s in ss)/len(ss)
    result = dict(case=case, trials=trials, trial=best.number, params=best.params,
                  **{f'{name}_{key}': mean(ss, key) for name, ss in (('retuned', ours), ('stale_v5', stale), ('textbook', book))
                     for key in ('all_requested_delay_s', 'unfinished', 'mainline_travel_eb_s', 'mainline_travel_wb_s')})
    (folder/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main(sys.argv[1], *map(int, sys.argv[2:3]))
