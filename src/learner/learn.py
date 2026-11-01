"""Learn the 15-minute pattern from the feed and build the copy's demand from counts only."""
from collections import defaultdict
import csv
import json
import statistics
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from signal_lab import demand as d, pipeline as p
from . import road

COPY_SEEDS = range(3)


def read(name, kind):
    days = []
    for day in sorted((road.OUT/name/'feed').glob('seed*')):
        with open(day/f'{kind}.csv') as stream:
            days.append(list(csv.DictReader(stream)))
    return days


def pattern(days, key):
    """Mean and spread across watched days of 15-minute counts per key."""
    totals = []
    for rows in days:
        day = defaultdict(float)
        for r in rows:
            day[(road.clock(r['window_end'])-300)//900*900, key(r)] += float(r['count'])
        totals.append(day)
    keys = sorted(set().union(*totals))
    return {k: (statistics.mean(t[k] for t in totals), statistics.pstdev(t[k] for t in totals)) for k in keys}


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
    lanes = pattern(read(name, 'lanes'), lambda r: r['lane'])
    approaches = pattern(read(name, 'feed'), lambda r: (r['site'], r['approach']))
    p.write_csv(out/'pattern.csv', [dict(quarter_start_s=t, site=s, approach=a, mean_count=round(m, 2), sd_count=round(sd, 2))
                                    for (t, (s, a)), (m, sd) in approaches.items()])
    with tempfile.TemporaryDirectory() as temp:
        exact = count_files(cfg, network, lanes, temp)
        pairs = {(i, o): (i, o) for i, outs in road.relations(cfg, network).items() for o in outs}
        d.candidate_routes(network, pairs, Path(temp)/'candidates.xml')
        log = p.tool('routeSampler.py', '-r', Path(temp)/'candidates.xml', '-d', Path(temp)/'edges.xml',
                     '-t', Path(temp)/'turns.xml', '-o', out/'copy.rou.xml', '--optimize', 'full', '--seed', 0,
                     '--prefix', 'copy', '-a', 'departLane="best" departSpeed="max"')
    fit = copy_fit(cfg, name, approaches)
    report = dict(road=name, watched_days=len(read(name, 'feed')), quarter_hours=len({t for t, _ in approaches}),
                  exact_turn_relations=len(exact), copy_vehicles=len(ET.parse(out/'copy.rou.xml').getroot().findall('vehicle')),
                  routesampler_log=log.strip().splitlines()[-6:], **fit)
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
    return dict(geh_under_5_share=sum(r['geh'] < 5 for r in rows)/len(rows),
                count_error_share=sum(abs(r['copy']-r['watched']) for r in rows)/sum(r['watched'] for r in rows),
                occupancy_mean_abs_diff=statistics.mean(abs(r['copy_occupancy']-r['watched_occupancy']) for r in rows))


def _group(days):
    groups = defaultdict(list)
    for rows in days:
        for r in rows:
            groups[(road.clock(r['window_end'])-300)//900*900, r['site'], r['approach']].append(float(r['occupancy']))
    return groups
