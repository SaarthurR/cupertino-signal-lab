import os
import csv
import math
import urllib.request
import xml.etree.ElementTree as ET
import yaml
import sumolib
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
TOOLS = Path(os.environ["SUMO_HOME"]) / "tools"
BIN = Path(os.environ["SUMO_HOME"]) / "bin"


def run(args):
    result = subprocess.run(["nice", "-n", "15", *[str(a) for a in args]], cwd=ROOT, text=True, capture_output=True, timeout=7200)
    if result.returncode:
        raise RuntimeError(f"Command failed: {args}\n{result.stdout}\n{result.stderr}")
    return result.stdout


def tool(name, *args):
    return run([sys.executable, TOOLS / name, *args])


def bench():
    with tempfile.TemporaryDirectory() as tmp:
        net = Path(tmp) / "bench.net.xml"
        routes = Path(tmp) / "bench.rou.xml"
        run([BIN / "netgenerate", "--grid", "--grid.number", "3", "--tls.guess", "--tls.default-type", "actuated", "-o", net])
        tool("randomTrips.py", "-n", net, "-r", routes, "-e", "3600", "-p", "2", "--seed", "0", "-o", Path(tmp) / "trips.xml")
        start = time.monotonic()
        output = run([BIN / "sumo", "-n", net, "-r", routes, "-e", "3600", "--no-step-log", "--duration-log.statistics"])
        seconds = time.monotonic() - start
    report = f"# M0 benchmark\n\nOne simulation hour: {seconds:.3f} wall seconds.\n\nInitial scaffold: synthetic 3×3 actuated grid, not the corridor. Re-run after M4 for the actual optimization budget.\n\nLaptop limits: every SUMO/optimization/evaluation/video child runs with `nice -n 15`; serial execution (one simulation, below the maximum three). No job over two hours. Before a run expected over ten minutes, check `pmset -g batt`; battery means one worker. Keep reports + sim below 2 GB and delete large FCD/tripinfo after extraction. Close sumo-gui after video. No GUI has been opened.\n\n```\n{output}\n```\n"
    (ROOT / "reports/bench.md").write_text(report)
    print(f"bench: {seconds:.3f} seconds (synthetic scaffold; corridor benchmark follows M4)")


def pending(**kwargs):
    raise SystemExit("Blocked at M2: VTA sample omits sites 211/217. See reports/data-source-audit.md; later milestones are not implemented.")


build_demand = check_demand = baseline = optimize = eval = dashboard = pending



def config():
    return yaml.safe_load((ROOT / 'config/corridor.yaml').read_text())


def write_csv(path, rows):
    rows = list(rows)
    with open(ROOT / path, 'w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def xml_write(root, path):
    ET.indent(root)
    ET.ElementTree(root).write(ROOT / path, encoding='utf-8', xml_declaration=True)


def build_net():
    cfg = config()
    raw = ROOT / 'data/raw/osm'
    raw.mkdir(parents=True, exist_ok=True)
    discovery = raw / 'discovery.osm.xml'
    if not discovery.exists():
        # Cupertino search envelope; coordinates below come only from OSM nodes.
        with urllib.request.urlopen('https://api.openstreetmap.org/api/0.6/map?bbox=-122.06,37.32,-122.03,37.33', timeout=60) as response:
            discovery.write_bytes(response.read())
    osm = ET.parse(discovery).getroot()
    nodes = {n.get('id'): n for n in osm.findall('node')}
    streets = {}
    for way in osm.findall('way'):
        tags = {t.get('k'): t.get('v') for t in way.findall('tag')}
        if 'highway' in tags:
            streets.setdefault(tags.get('name', ''), set()).update(n.get('ref') for n in way.findall('nd'))
    main = streets['Stevens Creek Boulevard']
    signal_nodes = [n for n in nodes.values() if any(t.get('k') == 'highway' and t.get('v') == 'traffic_signals' for t in n.findall('tag'))]
    for signal in cfg['signals']:
        expanded = signal['name'].replace('Blvd', 'Boulevard').replace('Dr', 'Drive').replace('Rd', 'Road').replace('Ave', 'Avenue')
        shared = set().union(*(ids & main for name, ids in streets.items() if expanded in name))
        if not shared:
            raise ValueError(f"OSM intersection not found: {signal['name']}")
        lat = sum(float(nodes[n].get('lat')) for n in sorted(shared)) / len(shared)
        lon = sum(float(nodes[n].get('lon')) for n in sorted(shared)) / len(shared)
        nearby = [n for n in signal_nodes if math.hypot((float(n.get('lat'))-lat)*111320, (float(n.get('lon'))-lon)*88500) < 65]
        if not nearby:
            raise ValueError(f"No OSM signal nodes near {signal['name']}")
        signal.update(lat=lat, lon=lon, osm_signal_nodes=[n.get('id') for n in nearby])
    cfg['bbox'] = [min(s['lon'] for s in cfg['signals'])-150/88500, min(s['lat'] for s in cfg['signals'])-150/111320, max(s['lon'] for s in cfg['signals'])+150/88500, max(s['lat'] for s in cfg['signals'])+150/111320]
    path = raw / 'corridor.osm.xml'
    if not path.exists():
        bbox = ','.join(f'{v:.7f}' for v in cfg['bbox'])
        # Overpass returns HTTP 406 here; official OSM map API supplies the same OSM primitives.
        with urllib.request.urlopen('https://api.openstreetmap.org/api/0.6/map?bbox=' + bbox, timeout=60) as response:
            path.write_bytes(response.read())
    tool('osmBuild.py', '-f', path, '-p', 'corridor', '-d', ROOT / 'sim', '--vehicle-classes', 'passenger', '--netconvert-options=--geometry.remove,--ramps.guess,--tls.guess-signals,--tls.discard-simple,--output.original-names,--output.street-names,--tls.default-type,actuated,--tls.yellow.time,4,--tls.allred.time,1,--osm.turn-lanes,--junctions.join,--tls.join')
    net = sumolib.net.readNet(str(ROOT / 'sim/corridor.net.xml'), withPrograms=True)
    for signal in cfg['signals']:
        x,y = net.convertLonLat2XY(signal['lon'], signal['lat'])
        tls = min(net.getTrafficLights(), key=lambda tls: min(math.dist((x,y), c[0].getEdge().getToNode().getCoord()) for c in tls.getConnections()))
        distance = min(math.dist((x,y), c[0].getEdge().getToNode().getCoord()) for c in tls.getConnections())
        if distance > 65:
            raise ValueError(f"No SUMO TLS near {signal['name']} ({distance:.1f}m)")
        signal['sumo_tls_id'] = tls.getID()
    assert len({s['sumo_tls_id'] for s in cfg['signals']}) == 5
    cfg['mainline_edges'] = [e.getID() for e in net.getEdges() if e.getName() == 'Stevens Creek Boulevard']
    cfg['side_edges'] = sorted({c[0].getEdge().getID() for s in cfg['signals'] for c in net.getTLS(s['sumo_tls_id']).getConnections()} - set(cfg['mainline_edges']))
    (ROOT / 'config/corridor.yaml').write_text(yaml.safe_dump(cfg, sort_keys=False))
    detectors = ET.Element('additional')
    controlled_lanes = {c[0].getID() for signal in cfg['signals'] for c in net.getTLS(signal['sumo_tls_id']).getConnections()}
    with tempfile.TemporaryDirectory() as tmp:
        for label, distance in [('stop', 1), ('upstream', 40)]:
            output = Path(tmp) / f'{label}.xml'
            tool('output/generateTLSE1Detectors.py', '-n', ROOT / 'sim/corridor.net.xml', '-d', distance, '-f', 900, '-r', '/dev/null', '-o', output)
            for detector in ET.parse(output).getroot():
                if detector.tag in ('e1Detector', 'inductionLoop') and detector.get('lane') in controlled_lanes:
                    detector.set('id', f'{label}_{detector.get("lane")}')
                    detector.set('pos', str(max(0, net.getLane(detector.get('lane')).getLength()-distance)))
                    detectors.append(detector)
    timing = []
    for signal in cfg['signals']:
        tls = net.getTLS(signal['sumo_tls_id'])
        program = next(iter(tls.getPrograms().values()))
        for i,phase in enumerate(program.getPhases()):
            if not any(c in phase.state for c in 'Gg') or 'y' in phase.state:
                continue
            conns = [c for c in tls.getConnections() if phase.state[c[2]] == 'G']
            through = any(v.getDirection() == 's' for c in conns for v in c[0].getOutgoing() if v.getToLane() == c[1])
            width = max((math.dist(c[0].getShape()[-1],c[1].getShape()[0]) for c in conns), default=15)*3.28084
            timing.append(dict(sumo_tls_id=tls.getID(),phase=i,movement='through' if through else 'protected_left',speed_mph=cfg['speed_mph'],grade=0,width_ft=round(width,1),yellow_s=max(3,math.ceil((1+1.467*cfg['speed_mph']/20)*10)/10),red_clear_s=max(1,round((width+20)/(1.467*cfg['speed_mph']),1)),min_green_s=7 if through else 5,max_green_s=40,passage_s=3,basis='Demo assumption, not city timing; OSM net geometry width, level grade'))
    xml_write(detectors, 'sim/detectors.add.xml')
    write_csv('data/processed/timing_inputs.csv', timing)
    configuration = ET.Element('configuration')
    inputs = ET.SubElement(configuration, 'input')
    ET.SubElement(inputs, 'net-file', value='corridor.net.xml')
    ET.SubElement(inputs, 'additional-files', value='detectors.add.xml')
    ET.SubElement(ET.SubElement(configuration, 'processing'), 'time-to-teleport', value=str(cfg['time_to_teleport']))
    xml_write(configuration, 'sim/corridor.sumocfg')
    run([BIN/'sumo','-c',ROOT/'sim/corridor.sumocfg','-e','1','--no-step-log'])
    print('build-net: all five OSM signals matched; network loads')
