"""One-factor training-seed diagnostics; temporary plans never become candidates."""
import copy
from pathlib import Path
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET

from . import pipeline as p
from .demand import seconds, summary_stats
from .evaluate import boundaries, command, corridor_times, metrics


def plans():
    vta = ET.parse(p.ROOT/'sim/tls_existing_vta_pm_peak.add.xml').getroot()
    textbook = ET.parse(p.ROOT/'sim/tls_actuated_pm_peak.add.xml').getroot()
    cfg = p.config()
    for index in (0, 3):
        root = copy.deepcopy(vta)
        tls = cfg['signals'][index]['sumo_tls_id']
        old = next(t for t in root if t.tag == 'tlLogic' and t.get('id') == tls)
        root.remove(old)
        root.append(copy.deepcopy(next(t for t in textbook if t.tag == 'tlLogic' and t.get('id') == tls)))
        yield f'textbook_at_{index}', root
    root = copy.deepcopy(vta)
    for index, delta in ((0, 6), (3, 8)):
        logic = next(t for t in root if t.tag == 'tlLogic' and t.get('id') == cfg['signals'][index]['sumo_tls_id'])
        phases = logic.findall('phase')
        for key in ('duration', 'maxDur'):
            phases[3].set(key, str(float(phases[3].get(key))+delta))
        for i in (3, 6, 9):
            phases[i].set('latestEnd', str(float(phases[i].get('latestEnd'))+delta))
    yield 'longer_EW_pair_diagnostic', root
    root = copy.deepcopy(vta)
    for index in (1, 2, 4):
        logic = next(t for t in root if t.tag == 'tlLogic' and t.get('id') == cfg['signals'][index]['sumo_tls_id'])
        cycle = float(next(v.get('value') for v in logic.findall('param') if v.get('key') == 'cycleTime'))
        logic.set('offset', str((float(logic.get('offset'))+cycle/2) % cycle))
    yield 'neighbour_offsets_half_cycle', root


def probe():
    (p.ROOT/'reports/fit').mkdir(parents=True, exist_ok=True)
    cfg = p.config()
    begin, end = [seconds(cfg['scenarios']['pm_peak'][k]) for k in ('begin', 'end')]
    requested = {}
    for v in ET.parse(p.ROOT/'sim/routes_pm_peak.rou.xml').getroot():
        edges = v.find('route').get('edges').split()
        approach = next(e for e in edges if e in cfg['mainline_edges'] or e in cfg['side_edges'])
        requested[v.get('id')] = float(v.get('depart')), approach in cfg['side_edges']
    rows = []
    for name, plan in plans():
        power = subprocess.check_output(['pmset', '-g', 'batt'], text=True)
        percent = re.search(r'(\d+)%;', power)
        if percent and int(percent[1]) < 25:
            raise RuntimeError('Battery below 25%; probe stopped')
        if subprocess.run(['pgrep', '-x', 'sumo'], capture_output=True).returncode == 0:
            raise RuntimeError('Another SUMO is running')
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            p.xml_write(plan, folder/'plan.xml')
            args = command('pm_peak', 'existing_vta', 0, cfg)
            args[args.index('-a')+1] = f'{p.ROOT}/sim/detectors.add.xml,{folder}/plan.xml'
            log = p.run([*args, '-e', end+1800, '--summary-output', folder/'summary.xml',
                         '--tripinfo-output', folder/'trips.xml', '--tripinfo-output.write-unfinished', 'true',
                         '--vehroute-output', folder/'routes.xml', '--vehroute-output.exit-times', 'true',
                         '--vehroute-output.write-unfinished', 'true', '--error-log', folder/'warnings.txt'])
            warnings = (folder/'warnings.txt').read_text()
            (p.ROOT/f'reports/fit/probe_{name}.log').write_text(log+'\n'+warnings)
            teleports = re.findall(r"Teleporting vehicle '([^']+)'", warnings)
            assert len(teleports) == summary_stats(folder/'summary.xml')['teleports']
            trips = {t.get('id'): dict(t.attrib) for t in ET.parse(folder/'trips.xml').getroot()}
            travels = corridor_times(folder/'routes.xml', boundaries(cfg), set(cfg['mainline_edges']), set(teleports))
            rows.append(dict(probe=name, seed=0, window='full PM training diagnostic',
                             **metrics(requested, trips, travels, teleports, begin, end)))
        p.write_csv('reports/fit/eb_probes.csv', rows)
        print(name, rows[-1]['mainline_travel_eb_s'], rows[-1]['unfinished'], flush=True)


if __name__ == '__main__':
    probe()
