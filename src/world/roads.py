"""Onboard a road from public OpenStreetMap data: net, loops, clearances, signal list. No demand."""
import math
import urllib.request
import xml.etree.ElementTree as ET

import yaml

from signal_lab import pipeline as p

ROADS = p.ROOT/'roads'
COMMON = dict(speed_mph=35, begin='16:30', end='18:30', warmup_s=900, drain_s=1800, time_to_teleport=300)
# Signals pinned by OSM traffic_signals node IDs, south-to-north or west-to-east.
SPECS = {
    'homestead': dict(role='dev', street='Homestead Road', search=(-122.065, 37.333, -122.0, 37.340), signals={
        'Wright Ave': ['11740360782', '11740360781'], 'Mary Ave': ['13976364168'],
        'Kennewick Dr': ['2582851762', '2582851759'],
        'Hollenbeck Ave': ['65436766'], 'Forge Way': ['2583024209', '1106363314']}),
    'wolfe': dict(role='heldout', street='Wolfe Road', search=(-122.0185, 37.321, -122.0105, 37.339), signals={
        'Vallco Pkwy': ['13038607672', '13038607673'], 'I-280 south ramps': ['65406866', '1297872125'],
        'I-280 north ramps': ['13988769694', '13988769693'], 'Pruneridge Ave': ['247385813', '247385812'],
        'Apple Park Way': ['11121665843', '3701140056', '11121665845']}),
    'deanza': dict(role='heldout', street='De Anza Boulevard', search=(-122.035, 37.322, -122.029, 37.339), signals={
        'Lazaneo Dr': ['13044806615', '13044806619'], 'Mariani Ave': ['13044798212', '13044798215'],
        'I-280 south ramps': ['13044790073', '7279196749'], 'I-280 north ramps': ['7279196775', '13044790075']}),
}


def osm_nodes(ids, bbox):
    path = p.ROOT/'data/raw/osm/learner'/f'{"_".join(f"{v:.4f}" for v in bbox)}.osm.xml'
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        url = 'https://api.openstreetmap.org/api/0.6/map?bbox='+','.join(f'{v:.7f}' for v in bbox)
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'signal-lab'}), timeout=90) as r:
            path.write_bytes(r.read())
    nodes = {n.get('id'): n for n in ET.parse(path).getroot().findall('node') if n.get('id') in ids}
    return path, nodes


def build_road(name):
    spec = SPECS[name]
    ids = {i for nodes in spec['signals'].values() for i in nodes}
    # A search strip finds the signal nodes; the 150 m net box comes only from their OSM coordinates.
    _, nodes = osm_nodes(ids, spec['search'])
    if nodes.keys() != ids:
        raise ValueError(f'OSM signal nodes missing: {ids-nodes.keys()}')
    signals = []
    for label, refs in spec['signals'].items():
        lat = sum(float(nodes[r].get('lat')) for r in refs)/len(refs)
        lon = sum(float(nodes[r].get('lon')) for r in refs)/len(refs)
        signals.append(dict(name=label, lat=lat, lon=lon, osm_signal_nodes=refs))
    bbox = (min(s['lon'] for s in signals)-150/88500, min(s['lat'] for s in signals)-150/111320,
            max(s['lon'] for s in signals)+150/88500, max(s['lat'] for s in signals)+150/111320)
    osm, _ = osm_nodes(set(), bbox)
    folder = ROADS/name
    folder.mkdir(parents=True, exist_ok=True)
    # Same netconvert options as the Stevens Creek build; no hand repairs.
    p.tool('osmBuild.py', '-f', osm, '-p', 'net', '-d', folder, '--vehicle-classes', 'passenger', '--netconvert-options=--geometry.remove,--ramps.guess,--tls.guess-signals,--tls.discard-simple,--output.original-names,--output.street-names,--tls.default-type,actuated,--tls.yellow.time,4,--tls.allred.time,1,--junctions.join,--tls.join')
    (folder/'net.netccfg').unlink(missing_ok=True)
    net_path = folder/'net.net.xml'
    net = p.sumolib.net.readNet(str(net_path), withPrograms=True)
    for signal in signals:
        x, y = net.convertLonLat2XY(signal['lon'], signal['lat'])
        near = lambda tls: min(math.dist((x, y), c[0].getEdge().getToNode().getCoord()) for c in tls.getConnections())
        tls = min(net.getTrafficLights(), key=near)
        if near(tls) > 65:
            raise ValueError(f"No SUMO signal near {signal['name']} ({near(tls):.1f} m)")
        signal['sumo_tls_id'] = tls.getID()
    tls_ids = [s['sumo_tls_id'] for s in signals]
    if len(set(tls_ids)) != len(tls_ids):
        raise ValueError(f'Two OSM signals matched one SUMO signal on {name}')
    mainline = sorted(e.getID() for e in net.getEdges() if spec['street'] in e.getName())
    incoming = {c[0].getEdge().getID() for t in tls_ids for c in net.getTLS(t).getConnections()}
    p.xml_write(p.loop_detectors(net_path, net, tls_ids), folder/'detectors.add.xml')
    p.write_csv(folder/'timing_inputs.csv', p.timing_rows(net, tls_ids, COMMON['speed_mph']))
    cfg = dict(name=name, role=spec['role'], street=spec['street'], source='OpenStreetMap (ODbL)',
               bbox=list(bbox), signals=signals, mainline_edges=mainline, side_edges=sorted(incoming-set(mainline)),
               **COMMON, net=f'roads/{name}/net.net.xml', detectors=f'roads/{name}/detectors.add.xml',
               timing_inputs=f'roads/{name}/timing_inputs.csv', old_timing=f'roads/{name}/old_timing.add.xml')
    (folder/'road.yaml').write_text(yaml.safe_dump(cfg, sort_keys=False))
    others = sorted({t.getID() for t in net.getTrafficLights()}-set(tls_ids))
    print(f'build-road {name}: {len(signals)} signals matched; other signals in box: {others}')
    return cfg


def stevens_creek():
    """The existing corridor as a road; same net, loops and clearances, new stale old timing."""
    cfg = p.config()
    road = dict(name='stevens_creek', role='dev', street='Stevens Creek Boulevard', source='OpenStreetMap (ODbL)',
                bbox=cfg['bbox'], signals=[{k: s[k] for k in ('name', 'lat', 'lon', 'osm_signal_nodes', 'sumo_tls_id')}
                                           for s in cfg['signals']],
                mainline_edges=cfg['mainline_edges'], side_edges=cfg['side_edges'], **COMMON,
                net='sim/corridor.net.xml', detectors='sim/detectors.add.xml',
                timing_inputs='data/processed/timing_inputs.csv', old_timing='roads/stevens_creek/old_timing.add.xml')
    (ROADS/'stevens_creek').mkdir(parents=True, exist_ok=True)
    (ROADS/'stevens_creek/road.yaml').write_text(yaml.safe_dump(road, sort_keys=False))
    return road
