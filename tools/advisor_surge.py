"""One east-surge search. Frozen v5/source routes are never overwritten."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile

import optuna

from signal_lab import feed, optimize as o, pipeline as p


def main():
    folder = p.ROOT/'reports/advisor_surge'
    folder.mkdir(exist_ok=True)
    routes = folder/'routes.xml'
    feed.scenario_routes('east_surge', routes)
    v5 = p.ROOT/'sim/tls_optuna_v5_pm_peak.add.xml'
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
    study.optimize(objective, n_trials=20)
    best = study.best_trial
    candidate = folder/'candidate.add.xml'
    o.plan('pm_peak', best.params, candidate, 5)
    ours, theirs = scores(candidate, range(5, 13)), scores(v5, range(5, 13))
    primary = lambda ss: sum(s['all_requested_delay_s'] for s in ss)/len(ss)
    retained = (best.value < primary(baseline) and o.feasible(ours, theirs)
                and primary(ours) < primary(theirs))
    if retained:
        o.plan('pm_peak', best.params, p.ROOT/'sim/tls_advisor_east_surge.add.xml', 5)
    result = dict(scenario='east_surge', trials=20, train_seeds=list(range(5)),
                  selection_seeds=list(range(5, 13)), trial=best.number, params=best.params,
                  train_primary_s=primary(best.user_attrs['stats']), train_v5_s=primary(baseline),
                  selection_primary_s=primary(ours), selection_v5_s=primary(theirs),
                  retained=retained, selection_feasible=o.feasible(ours, theirs),
                  train_stats=best.user_attrs['stats'], selection_stats=ours, selection_v5_stats=theirs,
                  scope='16:30–17:30 requested cohort plus warmup and drain; no switch modeled')
    (p.ROOT/'reports/advisor_surge.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if not isinstance(v,(dict,list))}), flush=True)


if __name__ == '__main__':
    main()
