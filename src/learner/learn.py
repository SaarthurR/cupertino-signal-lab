"""Learn the 15-minute pattern from the feed and build the copy's demand from counts only."""
from collections import defaultdict
import csv
import hashlib
import json
import math
import statistics
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from signal_lab import demand as d, pipeline as p
from . import road

COPY_SEEDS = range(3)
# Conservative screening rules, not a claim of field calibration.
SCREENING = dict(geh_under_5_share=.85, count_error_share=.15,
                 occupancy_mean_abs_diff=10., shared_turn_max_share=.20, watched_days=3)


def read(name, kind):
    days = []
    for day in sorted((road.OUT/name/'feed').glob('seed*')):
        with open(day/f'{kind}.csv') as stream:
            days.append(list(csv.DictReader(stream)))
    return days


def pattern(days, key):
    """Mean and spread across watched days of 15-minute counts per key."""
    if not days or any(not day for day in days):
        raise ValueError('Learning requires nonempty, complete observation days')
    totals, grids = [], []
    for rows in days:
        day = defaultdict(float)
        grid = set()
        for r in rows:
            t, k, count = road.clock(r['window_end']), key(r), float(r['count'])
            if t % 300 or not math.isfinite(count) or count < 0 or str(r.get('ok', '1')) != '1':
                raise ValueError('Learning requires valid five-minute counts; suspect data needs repair')
            if 'occupancy' in r and (not math.isfinite(float(r['occupancy'])) or not 0 <= float(r['occupancy']) <= 100):
                raise ValueError('Occupancy must be finite and between 0 and 100')
            if (t, k) in grid:
                raise ValueError('Duplicate observation window and detector')
            grid.add((t, k))
            day[(t-300)//900*900, k] += count
        times = sorted({t for t, _ in grid})
        keys = {k for _, k in grid}
        if times != list(range(times[0], times[-1]+300, 300)) or len(grid) != len(times)*len(keys):
            raise ValueError('Missing observation windows or detectors; missing is not zero')
        grids.append(grid)
        totals.append(day)
    if any(grid != grids[0] for grid in grids):
        raise ValueError('Observation days must cover the same windows and detectors')
    keys = sorted(set().union(*totals))
    return {k: (statistics.mean(t[k] for t in totals), statistics.pstdev(t[k] for t in totals)) for k in keys}


def turn_bounds(cfg, network, lanes):
    """What lane totals identify: exact lower bounds and shared-lane upper bounds, not guessed turns."""
    owner = exclusive_lanes(network, road.relations(cfg, network))
    rows = []
    for start in sorted({t for t, _ in lanes}):
        for incoming, targets in road.relations(cfg, network).items():
            counts = {lane.getID(): lanes.get((start, lane.getID()), (0, 0))[0]
                      for lane in network.getEdge(incoming).getLanes()}
            total = sum(counts.values())
            for outgoing in sorted(targets):
                lower = sum(c for lane, c in counts.items() if owner.get(lane) == {outgoing})
                uncertain = sum(c for lane, c in counts.items() if outgoing in owner.get(lane, ()) and len(owner[lane]) > 1)
                rows.append(dict(quarter_start_s=start, incoming=incoming, outgoing=outgoing,
                                 min_count=lower, max_count=lower+uncertain,
                                 ambiguous_share=uncertain/total if total else 0.))
    return rows


def quality_gate(report):
    reasons = []
    for key, limit in SCREENING.items():
        value = report.get(key)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value < 0 or (key in ('geh_under_5_share', 'shared_turn_max_share') and value > 1):
            reasons.append(f'Missing or invalid {key}; rebuild and check the copy')
        elif (value < limit if key in ('geh_under_5_share', 'watched_days') else value > limit):
            reasons.append(f'{key}={value:.3f} fails screening limit {limit:g}')
    return dict(passed=not reasons, reasons=reasons, screening_limits=SCREENING,
                label='Development screening only; unobserved demand and turn splits remain uncertain')


def observed_hashes(name):
    out = road.OUT/name
    return {str(path.relative_to(out)): hashlib.sha256(path.read_bytes()).hexdigest()
            for day in sorted((out/'feed').glob('seed*')) for kind in ('feed', 'lanes')
            for path in [day/f'{kind}.csv']}


def complete_days(days, key, expected_keys, begin, end):
    expected = {(t, k) for t in range(begin+300, end+300, 300) for k in expected_keys}
    if not expected or not days or any(len(rows) != len(expected) or
            {(road.clock(r['window_end']), key(r)) for r in rows} != expected for rows in days):
        raise ValueError('Observation days must contain every configured detector and five-minute window')


def exclusive_lanes(network, rels):
    """Lanes whose every signal movement goes to one outgoing edge; their counts are exact turn counts."""
    owner = {}
    for incoming, outs in rels.items():
        for lane in network.getEdge(incoming).getLanes():
            targets = {c.getToLane().getEdge().getID() for c in lane.getOutgoing()} & outs.keys()
            if targets:
                owner[lane.getID()] = targets
    return owner


def count_files(cfg, network, lanes, folder):
    """routeSampler inputs: per-edge counts, plus turn counts where only dedicated lanes serve the turn."""
    rels = road.relations(cfg, network)
    owner = exclusive_lanes(network, rels)
    begin, _ = road.window(cfg)
    edges, turns = defaultdict(lambda: defaultdict(float)), defaultdict(lambda: defaultdict(float))
    for (start, lane), (mean, _) in lanes.items():
        edge = network.getLane(lane).getEdge().getID()
        edges[start][edge] += mean
        if lane in owner and len(owner[lane]) == 1:
            turns[start][edge, next(iter(owner[lane]))] += mean
    shared = {(network.getLane(l).getEdge().getID(), o) for l, targets in owner.items() if len(targets) > 1 for o in targets}
    # Warmup has no feed; it repeats the first watched quarter hour.
    for table in (edges, turns):
        table[begin-cfg['warmup_s']] = dict(table[begin])
    data = ET.Element('data')
    for start in sorted(edges):
        interval = ET.SubElement(data, 'interval', id=str(start), begin=str(start), end=str(start+900))
        for edge, count in sorted(edges[start].items()):
            ET.SubElement(interval, 'edge', id=edge, entered=str(round(count)))
    p.xml_write(data, Path(folder)/'edges.xml')
    d.turn_file({t: {pair: round(c) for pair, c in v.items() if pair not in shared} for t, v in turns.items()},
                Path(folder)/'turns.xml')
    return {pair for pair in (pair for v in turns.values() for pair in v) if pair not in shared}


def learn(name):
    cfg = road.load(name)
    network = road.net(cfg)
    out = road.OUT/name
    lane_days, feed_days = read(name, 'lanes'), read(name, 'feed')
    begin, end = road.window(cfg)
    incoming = road.approaches(cfg, network)
    detectors = ET.parse(road.file(cfg, 'detectors')).getroot()
    lane_ids = {r.get('id')[len('stop_'):] for r in detectors if r.get('id', '').startswith('stop_')
                and network.getLane(r.get('lane')).getEdge().getID() in incoming}
    expected = {lane.getID() for incoming in road.relations(cfg, network)
                for lane in network.getEdge(incoming).getLanes() if lane.allows('passenger')}
    if not expected <= lane_ids:
        raise ValueError('Missing lane detectors; repair the feed before learning')
    complete_days(lane_days, lambda r: r['lane'], lane_ids, begin, end)
    complete_days(feed_days, lambda r: (r['site'], r['approach']), set(incoming.values()), begin, end)
    lanes = pattern(lane_days, lambda r: r['lane'])
    approaches = pattern(feed_days, lambda r: (r['site'], r['approach']))
    bounds = turn_bounds(cfg, network, lanes)
    p.write_csv(out/'turn_bounds.csv', bounds)
    p.write_csv(out/'pattern.csv', [dict(quarter_start_s=t, site=s, approach=a, mean_count=round(m, 2), sd_count=round(sd, 2))
                                    for (t, (s, a)), (m, sd) in approaches.items()])
    copies = []
    for suffix, spread in (('', 0), ('_low', -1), ('_high', 1)):
        counts = {k: (max(0, mean+spread*sd), sd) for k, (mean, sd) in lanes.items()}
        with tempfile.TemporaryDirectory() as temp:
            exact = count_files(cfg, network, counts, temp)
            pairs = {(i, o): (i, o) for i, outs in road.relations(cfg, network).items() for o in outs}
            d.candidate_routes(network, pairs, Path(temp)/'candidates.xml')
            copy_name = f'copy{suffix}.rou.xml'
            log = p.tool('routeSampler.py', '-r', Path(temp)/'candidates.xml', '-d', Path(temp)/'edges.xml',
                         '-t', Path(temp)/'turns.xml', '-o', out/copy_name, '--optimize', 'full', '--seed', 0,
                         '--prefix', 'copy', '-a', 'departLane="best" departSpeed="max"')
            copies.append(copy_name)
    fit = copy_fit(cfg, name, approaches)
    report = dict(road=name, watched_days=len(read(name, 'feed')), quarter_hours=len({t for t, _ in approaches}),
                  exact_turn_relations=len(exact), copy_vehicles=len(ET.parse(out/'copy.rou.xml').getroot().findall('vehicle')),
                  shared_turn_max_share=max(r['ambiguous_share'] for r in bounds), demand_copies=copies,
                  observations_sha256=observed_hashes(name),
                  copies_sha256={filename: hashlib.sha256((out/filename).read_bytes()).hexdigest() for filename in copies},
                  copy_spread='mean and plus/minus one observed count SD; stress cases, not confidence bounds',
                  routesampler_log=log.strip().splitlines()[-6:], **fit)
    report['quality_gate'] = quality_gate(report)
    (out/'learn.json').write_text(json.dumps(report, indent=2)+'\n')
    print(f"learn {name}: {report['copy_vehicles']} copy vehicles; GEH<5 vs feed {fit['geh_under_5_share']:.0%}")
    return report


def copy_fit(cfg, name, watched):
    """Run the copy on old timing and compare its feed to the watched feed."""
    results = road.many([(cfg, road.OUT/name/'copy.rou.xml', road.file(cfg, 'old_timing'), s, True) for s in COPY_SEEDS])
    copy = pattern([rows for _, (rows, _) in results], lambda r: (r['site'], r['approach']))
    occupancy = lambda days: {k: statistics.mean(v) for k, v in _group(days).items()}
    seen, simulated = occupancy(read(name, 'feed')), occupancy([rows for _, (rows, _) in results])
    rows = [dict(quarter_start_s=t, site=s, approach=a, watched=round(m, 1), copy=round(copy[t, (s, a)][0], 1),
                 geh=round(d.geh(m, copy[t, (s, a)][0]), 3),
                 watched_occupancy=round(seen[t, s, a], 2), copy_occupancy=round(simulated[t, s, a], 2))
            for (t, (s, a)), (m, _) in watched.items()]
    p.write_csv(road.OUT/name/'copy_fit.csv', rows)
    total = sum(r['watched'] for r in rows)
    if not rows or total <= 0:
        raise ValueError('Insufficient observed traffic to validate a timing recommendation')
    return dict(geh_under_5_share=sum(r['geh'] < 5 for r in rows)/len(rows),
                count_error_share=sum(abs(r['copy']-r['watched']) for r in rows)/total,
                occupancy_mean_abs_diff=statistics.mean(abs(r['copy_occupancy']-r['watched_occupancy']) for r in rows))


def _group(days):
    groups = defaultdict(list)
    for rows in days:
        for r in rows:
            groups[(road.clock(r['window_end'])-300)//900*900, r['site'], r['approach']].append(float(r['occupancy']))
    return groups
