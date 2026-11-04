"""A road as the learner sees it: map, signal list, loops, old timing. Simulation is SUMO, never a real signal."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
import re
import tempfile
import xml.etree.ElementTree as ET

import yaml

from signal_lab import evaluate as e, feed as f, pipeline as p
from signal_lab.demand import seconds, summary_stats

OUT = p.ROOT/'reports/learner'
MAX_SIMS = 3


def load(name):
    return yaml.safe_load((p.ROOT/'roads'/name/'road.yaml').read_text())


def file(cfg, key):
    return p.ROOT/cfg[key]


def net(cfg):
    return p.sumolib.net.readNet(str(file(cfg, 'net')))


def window(cfg):
    return seconds(cfg['begin']), seconds(cfg['end'])


def clock(window_end):
    """Feed timestamp to simulation seconds."""
    return int((datetime.fromisoformat(window_end)-f.CLOCK).total_seconds())


def approaches(cfg, network):
    """Incoming signal edge -> (site, originating compass leg); N means southbound, as in the feed."""
    out = {}
    for signal in cfg['signals']:
        for lane, _, _ in network.getTLS(signal['sumo_tls_id']).getConnections():
            edge = lane.getEdge()
            (x0, y0), (x1, y1) = edge.getFromNode().getCoord(), edge.getToNode().getCoord()
            dx, dy = x0-x1, y0-y1
            out[edge.getID()] = signal['name'], ('E' if dx > 0 else 'W') if abs(dx) > abs(dy) else ('N' if dy > 0 else 'S')
    return out


def relations(cfg, network):
    """Signal turn relations (incoming edge -> {outgoing edge: l/s/r}); U-turns are assumed to carry no demand."""
    out = {}
    for signal in cfg['signals']:
        for lane, outgoing, _ in network.getTLS(signal['sumo_tls_id']).getConnections():
            if not lane.allows('passenger') or not outgoing.allows('passenger'):
                continue
            for c in lane.getOutgoing():
                if c.getToLane() == outgoing and c.getDirection() in 'slrLR':
                    out.setdefault(lane.getEdge().getID(), {})[outgoing.getEdge().getID()] = c.getDirection().lower()
    return out


def feed_detectors(cfg, network, folder):
    edges = approaches(cfg, network)
    root, ids = ET.Element('additional'), {}
    for detector in ET.parse(file(cfg, 'detectors')).getroot():
        edge = network.getLane(detector.get('lane')).getEdge().getID()
        if edge in edges and detector.get('id').startswith(('stop_', 'upstream_')):
            detector.set('freq', '300')
            detector.set('file', str(Path(folder)/'counts.xml'))
            root.append(detector)
            ids[detector.get('id')] = edges[edge]
    p.xml_write(root, Path(folder)/'detectors.add.xml')
    return Path(folder)/'detectors.add.xml', ids


def lane_rows(path, ids, begin, end):
    """Stop-line count per lane and five-minute window, as a controller log would give."""
    return sorted((dict(window_end=(f.CLOCK+timedelta(seconds=float(i.get('end')))).isoformat(),
                        site=ids[i.get('id')][0], approach=ids[i.get('id')][1], lane=i.get('id')[len('stop_'):],
                        count=int(i.get('nVehEntered')))
                   for i in ET.parse(path).getroot().findall('interval')
                   if i.get('id').startswith('stop_') and begin <= float(i.get('begin')) and float(i.get('end')) <= end),
                  key=lambda r: (r['window_end'], r['lane']))


def simulate(cfg, routes, timing, seed, feed=False, additional=(), timeout=7200, runner=None):
    """One PM run: metrics charged as in evaluate (900 s per unfinished trip and teleport); optional feed rows.
    runner(args, timeout) replaces the SUMO subprocess, e.g. to step the same command through libsumo."""
    begin, end = window(cfg)
    network = net(cfg)
    with tempfile.TemporaryDirectory() as folder:
        folder = Path(folder)
        detectors, ids = feed_detectors(cfg, network, folder)
        (runner or p.run)([p.BIN/'sumo', '-n', file(cfg, 'net'), '-r', routes,
               '-a', ','.join(map(str, [detectors, timing, *additional])),
               '-b', begin-cfg['warmup_s'], '-e', end+cfg['drain_s'], '--seed', seed,
               '--time-to-teleport', cfg['time_to_teleport'], '--no-step-log', '--aggregate-warnings', -1,
               '--error-log', folder/'warnings.txt', '--summary-output', folder/'summary.xml',
               '--tripinfo-output', folder/'trips.xml', '--tripinfo-output.write-unfinished', 'true'], timeout=timeout)
        teleports = re.findall(r"Teleporting vehicle '([^']+)'", (folder/'warnings.txt').read_text())
        if len(teleports) != summary_stats(folder/'summary.xml')['teleports']:
            raise ValueError('Teleport warning/summary mismatch')
        trips = {t.get('id'): dict(t.attrib) for t in ET.parse(folder/'trips.xml').getroot().findall('tripinfo')}
        counted = set(cfg['mainline_edges']) | set(cfg['side_edges'])
        requested, origins = {}, {}
        for vehicle in ET.parse(routes).getroot().iter('vehicle'):
            origin = next(edge for edge in vehicle.find('route').get('edges').split() if edge in counted)
            requested[vehicle.get('id')] = float(vehicle.get('depart')), origin in cfg['side_edges']
            origins[vehicle.get('id')] = float(vehicle.get('depart')), origin
        stats = e.metrics(requested, trips, {}, teleports, begin, end)
        groups = e.origin_delays(origins, trips, teleports, begin, end)
        stats.update(seed=seed, worst_origin_delay_s=max(groups.values()), origin_delay_s=groups)
        rows = (f.feed_rows(folder/'counts.xml', ids, begin, end), lane_rows(folder/'counts.xml', ids, begin, end)) if feed else None
    return stats, rows


def many(jobs):
    """Run (cfg, routes, timing, seed, ...) jobs, at most three simulations at once."""
    with ThreadPoolExecutor(max_workers=MAX_SIMS) as pool:
        return list(pool.map(lambda job: simulate(*job), jobs))
