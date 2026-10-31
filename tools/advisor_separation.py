"""Summarize the already generated v5 PM scenario feeds, seeds 1–4."""
import csv
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]


def rolling(scenario, seed):
    groups = defaultdict(list)
    with open(ROOT/f'reports/feed/{scenario}_seed{seed}/feed.csv') as stream:
        for row in csv.DictReader(stream):
            groups[row['site'], row['approach']].append(row)
    return {(key, datetime.fromisoformat(rows[i]['window_end'])):
            tuple(mean(float(r[m]) for r in rows[i-2:i+1]) for m in ('count', 'occupancy'))
            for key, rows in groups.items() for i in range(2, len(rows))}


def main():
    calm = [rolling('calm', s) for s in range(1, 5)]
    lines = ['# Advisor separation: simulated counts', '',
             'All five scenarios ran with frozen v5 PM, seeds 1–4 (seed 0 also supplies replay fixtures and profile calibration).',
             'Each signal is the trailing three-window mean: counts are vehicles per five minutes;',
             'occupancy is percent. Differences below are scenario mean minus calm mean at 17:15.',
             'Noise is the calm max-minus-min across four seeds at that same time.',
             'Detectable means all four scenario values lie outside all four calm values, the absolute',
             'mean difference exceeds the calm range, and this holds in the same direction for two',
             'consecutive windows of the same channel. Minutes are from 17:00, including the hold.',
             'This is a descriptive fit-seed separation test, not an out-of-sample accuracy claim.', '',
             '| Scenario | First separation | During 17:00–17:30? |',
             '|---|---:|---|']
    details = []
    start = datetime.fromisoformat('2026-10-31T17:00:00-07:00')
    for scenario in ('south_surge', 'east_surge', 'drop', 'sensor_failure'):
        other = [rolling(scenario, s) for s in range(1, 5)]
        assert all(set(c) == set(calm[0]) for c in calm+other), 'Unpaired feed windows'
        if scenario == 'sensor_failure':
            assert other == calm, 'Failure scenario unexpectedly changed traffic'
        firsts = []
        details += ['', f'## {scenario}', '',
                    '| Approach | Count Δ / noise | Occupancy Δ pp / noise pp | First separation, min (channel) |',
                    '|---|---:|---:|---|']
        for approach in sorted({k[0] for k in calm[0]}):
            hits = []
            for j, metric in enumerate(('count', 'occupancy')):
                previous = None
                for key in sorted(k for k in calm[0] if k[0] == approach and k[1] > start):
                    a, b = [c[key][j] for c in calm], [c[key][j] for c in other]
                    delta, noise = mean(b)-mean(a), max(a)-min(a)
                    direction = 1 if min(b) > max(a) else -1 if max(b) < min(a) else 0
                    if direction and abs(delta) > noise:
                        if previous == (key[1]-timedelta(minutes=5), direction):
                            hits.append(((key[1]-start).total_seconds()/60, metric))
                            break
                        previous = key[1], direction
                    else:
                        previous = None
            first = min(hits) if hits else None
            if first:
                firsts.append(first[0])
            key = approach, start+timedelta(minutes=15)
            values = []
            for j in range(2):
                a, b = [c[key][j] for c in calm], [c[key][j] for c in other]
                values.append(f'{mean(b)-mean(a):+.2f} / {max(a)-min(a):.2f}')
            details.append(f'| {approach[0]} {approach[1]} | {values[0]} | {values[1]} | '
                           + (f'{first[0]:g} ({first[1]})' if first else 'none')+' |')
        earliest = min(firsts) if firsts else None
        lines.append(f'| {scenario} | {earliest:g} min | {"yes" if earliest <= 30 else "no"} |'
                     if earliest else f'| {scenario} | none | no |')
    lines += ['', 'East surge is the one surge selected for tuning. South surge is excluded from the',
              'advisor: no repeatable separation during the change; late effects first appear at 18:00,',
              '30 minutes after the requested surge ends. Drop is distinguishable but is not night demand.',
              'Sensor failure has exactly calm traffic; only De Anza N quality flags differ (1/17 rows).',
              'It is excluded as a traffic profile. The advisor masks suspect rows; it refuses a window',
              'only when more than 25% are bad, or required coverage/freshness is absent.',
              'No threshold or profile uses seeds above 4. All runs used caffeinate -i, nice -n 15,',
              'and at most three concurrent SUMO runs.']
    (ROOT/'reports/advisor_separation.md').write_text('\n'.join(lines+details)+'\n')


if __name__ == '__main__':
    main()
