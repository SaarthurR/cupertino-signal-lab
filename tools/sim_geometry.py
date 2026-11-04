"""Export each road's SUMO lane geometry to a compact JSON for the console map: python -m tools.sim_geometry."""
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'dashboard/console/geo'


def flat(shape):
    return [round(float(v), 1) for point in shape.split() for v in point.split(',')]


def export(road):
    """Lanes, junction areas and, per traffic light, each incoming lane's stop line with its signal link indices."""
    cfg = yaml.safe_load((ROOT/'roads'/road/'road.yaml').read_text())
    net = ET.parse(ROOT/cfg['net']).getroot()
    shapes = {lane.get('id'): lane.get('shape') for lane in net.iter('lane')}
    lanes = [dict(xy=flat(lane.get('shape')), w=round(float(lane.get('width', 3.2)), 1),
                  main=edge.get('id') in cfg['mainline_edges'])
             for edge in net.findall('edge') if edge.get('function') != 'internal'
             for lane in edge.findall('lane')]
    signals = []
    for signal in cfg['signals']:
        stops = {}
        for c in net.findall('connection'):
            if c.get('tl') == signal['sumo_tls_id']:
                stops.setdefault(f"{c.get('from')}_{c.get('fromLane')}", []).append(int(c.get('linkIndex')))
        signals.append(dict(name=signal['name'], tls=signal['sumo_tls_id'],
                            stops=[dict(xy=flat(shapes[lane])[-4:], links=sorted(set(idx))) for lane, idx in stops.items()]))
    x0, y0, x1, y1 = map(float, net.find('location').get('convBoundary').split(','))
    return dict(road=road, street=cfg['street'], bounds=[x0, y0, x1, y1], lanes=lanes,
                junctions=[flat(j.get('shape')) for j in net.findall('junction') if j.get('shape') and j.get('type') != 'internal'],
                internal=[flat(lane.get('shape')) for edge in net.findall('edge')
                          if edge.get('function') == 'internal' for lane in edge.findall('lane')],
                signals=signals)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for road in ('wolfe', 'deanza'):
        path = OUT/f'{road}.json'
        path.write_text(json.dumps(export(road), separators=(',', ':')))
        print(path.relative_to(ROOT), path.stat().st_size, 'bytes')


if __name__ == '__main__':
    main()
