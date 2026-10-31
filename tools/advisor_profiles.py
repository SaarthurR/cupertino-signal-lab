"""Fit advisor profiles/margins on seeds 0–4 only, from simulated counts."""
from concurrent.futures import ThreadPoolExecutor
import json
from statistics import mean

from signal_lab import advisor as a, demand as d, evaluate, feed, pipeline as p


def night(seed):
    cfg = p.config()
    begin, end = map(d.seconds, ('23:00', '24:00'))
    folder = p.ROOT/f'reports/feed/night_seed{seed}'
    folder.mkdir(exist_ok=True)
    detectors, ids, unmapped = feed.feed_detectors(folder)
    args = evaluate.command('night', 'optuna_v5', seed, cfg)
    args[args.index('-a')+1] = f'{detectors},{p.ROOT}/sim/tls_optuna_v5_night.add.xml'
    (folder/'sumo.log').write_text(p.run([*args, '-e', end]))
    p.write_csv(folder/'feed.csv', feed.feed_rows(folder/'counts.xml', ids, begin, end))
    (folder/'metadata.json').write_text(json.dumps(dict(seed=seed, simulated_counts=True,
                                                       controller='optuna_v5_night', unmapped=unmapped))+'\n')


def signals(scenario):
    result = []
    for seed in range(5):
        rows = a.read_feed(p.ROOT/f'reports/feed/{scenario}_seed{seed}/feed.csv')
        for time in sorted({r.window_end for r in rows})[2:]:
            if scenario == 'east_surge' and not '17:15' <= time.strftime('%H:%M') <= '17:30':
                continue
            result.append(a.smooth([r for r in rows if time-3*a.WINDOW < r.window_end <= time]))
    return result


def main():
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(night, range(5)))
    samples = {name: signals(scenario) for name, scenario in
               (('pm', 'calm'), ('night', 'night'), ('east_surge', 'east_surge'))}
    approaches = sorted(samples['pm'][0])
    features = []
    for key in approaches:
        profiles = {name: [mean(s[key][j] for s in ss) for j in range(2)] for name, ss in samples.items()}
        # A measured range keeps count and occupancy units comparable without guessed weights.
        scale = [max(s[key][j] for ss in samples.values() for s in ss)
                 - min(s[key][j] for ss in samples.values() for s in ss) for j in range(2)]
        features.append(dict(approach=key, profiles=profiles, scale=scale))
    plans = dict(v5_pm=dict(profile='pm', path='sim/tls_optuna_v5_pm_peak.add.xml'),
                 v5_night=dict(profile='night', path='sim/tls_optuna_v5_night.add.xml'),
                 textbook=dict(profile='pm', path='sim/tls_actuated_pm_peak.add.xml'))
    surge = json.loads((p.ROOT/'reports/advisor_surge.json').read_text())
    if surge['retained']:
        plans['east_surge'] = dict(profile='east_surge', path='sim/tls_advisor_east_surge.add.xml')
    result = dict(seeds=list(range(5)), profiles=list(samples), plans=plans, features=features,
                  provenance='Simulated counts; PM full window, night full window, east surge 17:15–17:30; v5 timing',
                  margins={})
    for source, ss in samples.items():
        scores = [a.distances(signal, result) for signal in ss]
        result['margins'][source] = {target: max(0., max(s[source]-s[target] for s in scores)) for target in samples}
    a.CALIBRATION.write_text(json.dumps(result, indent=2)+'\n')
    print('Profiles/margins frozen from seeds 0–4 only')
    for scenario in ('calm', 'south_surge', 'east_surge', 'drop', 'sensor_failure', 'night'):
        decisions = list(a.replay(a.read_feed(p.ROOT/f'reports/feed/{scenario}_seed0/feed.csv'), result))
        changes = [(r['window_end'], r['plan']) for r in decisions if r['plan']]
        if scenario == 'calm':
            assert not changes, 'False recommendation on fit seed-0 calm'
        if scenario == 'east_surge':
            assert any(r.get('profile') == 'east_surge' and r['margin'] > r['threshold']
                       for r in decisions), 'Seed-0 surge not detected'
        print(scenario, changes, 'east-profile windows:', sum(r.get('profile') == 'east_surge' for r in decisions))


if __name__ == '__main__':
    main()
