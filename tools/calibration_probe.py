"""Count-preserving demand probe; run from this checkout with PYTHONPATH=src."""
from collections import Counter
import csv
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
from scipy.optimize import lsq_linear
from signal_lab import demand as d, pipeline as p

OUT = p.ROOT / 'reports/calib'


def scheduled(path, mapping):
    counts = Counter()
    wanted = set(mapping.values())
    for v in ET.parse(path).getroot().findall('vehicle'):
        edges = v.find('route').get('edges').split()
        quarter = int(float(v.get('depart')) // 900) * 900
        for pair in zip(edges, edges[1:]):
            if pair in wanted:
                counts[(quarter, *pair)] += 1
    return counts


def score(rows, mapping, counts):
    return sum(d.geh(int(r['vehicles']), counts[(d.seconds(r['interval_start']), *mapping[r['intersection'], r['approach'], r['movement']])]) < 5 for r in rows)


def simulate(name, routes, rows, mapping):
    folder = OUT / name
    folder.mkdir(exist_ok=True)
    detectors, ids = d.turn_detectors(d.network(), mapping, folder)
    stats = d.simulation('pm_peak', folder, routes=routes, additional=detectors)
    (folder/'sumo.log').write_text(stats.pop('log'))
    actual = d.detector_counts(folder/'turn_counts.xml', ids, 59400, 66600)
    plan = scheduled(routes, mapping)
    detail = []
    for r in rows:
        pair = mapping[r['intersection'], r['approach'], r['movement']]
        key = d.seconds(r['interval_start']), *pair
        observed, requested, crossed = int(r['vehicles']), plan[key], actual[key]
        detail.append(dict(**r, requested=requested, crossed=crossed, requested_error=requested-observed,
                           crossed_error=crossed-observed, requested_geh=d.geh(observed, requested),
                           crossed_geh=d.geh(observed, crossed)))
    p.write_csv(folder/'movements.csv', detail)
    measured = [r for r in rows if r['source'] == 'measured']
    holdout = [r for r in measured if r['interval_start'] >= '17:30']
    stats.update(fit_requested=score([r for r in measured if r['interval_start'] < '17:30'], mapping, plan),
                 holdout_requested=score(holdout, mapping, plan), holdout_detector=score(holdout, mapping, actual))
    (folder/'stats.json').write_text(json.dumps(stats, indent=2)+'\n')
    print(name, stats, flush=True)
    # Keep only extracted evidence, not large transient simulation XML.
    for filename in ('summary.xml', 'tripinfo.xml', 'turn_counts.xml'):
        (folder/filename).unlink()
    return stats


def balanced_routes(mapping, rows):
    """Keep every count; allow residuals in both directions instead of hard upper caps."""
    candidates = [r.get('edges').split() for r in ET.parse(p.ROOT/'data/processed/candidate_routes.rou.xml').getroot()]
    pairs = sorted(set(mapping.values()))
    matrix = np.array([[int(pair in list(zip(route, route[1:]))) for route in candidates] for pair in pairs], dtype=float)
    assert matrix.shape[0] == 41 and np.all(matrix.sum(axis=1) > 0)
    counts = d.mapped_counts([r for r in rows if r['interval_start'] < '17:30'], mapping)
    root = ET.Element('routes')
    rng = np.random.default_rng(0)
    residuals = []
    for begin, values in sorted(counts.items()):
        observed = np.array([values[pair] for pair in pairs], dtype=float)
        weights = 1 / np.sqrt(observed + 1)
        fit = lsq_linear(matrix*weights[:, None], observed*weights, bounds=(0, np.inf), method="bvls", tol=1e-10, max_iter=1000)
        assert fit.success, fit.message
        route_counts = np.rint(fit.x).astype(int)
        assert np.all(route_counts >= 0)
        for route, count in zip(candidates, route_counts):
            for depart in rng.uniform(begin, begin+900, count):
                vehicle = ET.SubElement(root, 'vehicle', id=str(len(root)), depart=f'{depart:.2f}', departLane='best', departSpeed='max')
                ET.SubElement(vehicle, 'route', edges=' '.join(route))
        residuals.append(dict(begin=begin, cost=float(fit.cost), maximum_residual=float(np.max(np.abs(matrix@route_counts-observed)))))
    root[:] = sorted(root, key=lambda v: float(v.get('depart')))
    sampled = OUT/'balanced_fit.rou.xml'
    d.p.xml_write(root, sampled)
    output = OUT/'routes_balanced.rou.xml'
    d.extend_fit(sampled, output, 59400, 63000, 66600, 900)
    (OUT/'balanced_fit.json').write_text(json.dumps(residuals, indent=2)+'\n')
    return output


def main():
    OUT.mkdir(exist_ok=True)
    rows, mapping = d.load_counts(), d.movement_map(d.network())
    baseline = simulate('baseline', p.ROOT/'sim/routes_pm_peak.rou.xml', rows, mapping)
    balanced = simulate('balanced', balanced_routes(mapping, rows), rows, mapping)
    (OUT/'comparison.json').write_text(json.dumps(dict(baseline=baseline, balanced=balanced), indent=2)+'\n')


if __name__ == '__main__':
    main()
