"""Explicit, serial training-seed look; never called by plan generation or tests."""
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET

from . import pipeline as p
from .demand import movement_map, network, seconds, summary_stats
from .evaluate import boundaries, command, corridor_times, mean, metrics
from .vta_timing import LABEL

DEMAND_BASIS = '2024 De Anza/Stelling L/T/R counts; 2024-based Bandley/Saich estimates; 2018 Mary estimates; U-turn demand excluded'


def movement_delays(path, net, mapping, requested, teleported):
    """Local crossing proxy from route exits, not total-trip loss or HCM control delay."""
    values = defaultdict(list)
    for _, vehicle in ET.iterparse(path):
        if vehicle.tag != 'vehicle':
            continue
        route = vehicle.find('route')
        if vehicle.get('id') in requested and vehicle.get('id') not in teleported and route is not None:
            edges = route.get('edges').split()
            exits = list(map(float, route.get('exitTimes').split()))
            if len(edges) != len(exits):
                raise ValueError('Route exit times do not align with edges')
            for key, (incoming, outgoing) in mapping.items():
                if key[0] not in ('De Anza Blvd', 'Stelling Rd'):
                    continue
                for i in range(len(edges)-1):
                    if (edges[i], edges[i+1]) != (incoming, outgoing):
                        continue
                    entry = exits[i-1] if i else float(vehicle.get('depart'))
                    if entry < 0 or exits[i+1] < entry:
                        continue
                    freeflow = sum(net.getEdge(e).getLength()/net.getEdge(e).getSpeed()
                                   for e in (incoming, outgoing))
                    # Includes junction traversal: external-edge freeflow omits internal connectors.
                    values[key].append(exits[i+1]-entry-freeflow)
        vehicle.clear()
    return values


def compare():
    cfg = p.config()
    begin, end = (seconds(cfg['scenarios']['pm_peak'][k]) for k in ('begin', 'end'))
    requested = {}
    for vehicle in ET.parse(p.ROOT/'sim/routes_pm_peak.rou.xml').getroot().findall('vehicle'):
        edges = vehicle.find('route').get('edges').split()
        approach = next(e for e in edges if e in cfg['mainline_edges'] or e in cfg['side_edges'])
        requested[vehicle.get('id')] = float(vehicle.get('depart')), approach in cfg['side_edges']
    net = network()
    mapping = movement_map(net)
    endpoints = boundaries(cfg)
    rows, local = [], []
    with open(p.ROOT/'data/processed/vta_vistro_results_2024.csv') as stream:
        reported = {(int(r['site_id']), r['direction'], r['movement']): r for r in csv.DictReader(stream)}
    for seed in range(3):
        for controller in ('actuated', 'existing_vta'):
            power = subprocess.check_output(['pmset', '-g', 'batt'], text=True)
            percent = re.search(r'(\d+)%;', power)
            if percent and int(percent[1]) < 25:
                raise RuntimeError('Battery below 25%; comparison stopped')
            if subprocess.run(['pgrep', '-x', 'sumo'], capture_output=True).returncode == 0:
                raise RuntimeError('Another SUMO process is running; retry after it finishes')
            with tempfile.TemporaryDirectory() as folder:
                folder = Path(folder)
                p.run([*command('pm_peak', controller, seed, cfg), '-e', end+1800,
                       '--summary-output', folder/'summary.xml', '--tripinfo-output', folder/'trips.xml',
                       '--tripinfo-output.write-unfinished', 'true', '--vehroute-output', folder/'routes.xml',
                       '--vehroute-output.exit-times', 'true', '--vehroute-output.write-unfinished', 'true',
                       '--error-log', folder/'warnings.txt'])
                teleports = re.findall(r"Teleporting vehicle '([^']+)'", (folder/'warnings.txt').read_text())
                if len(teleports) != summary_stats(folder/'summary.xml')['teleports']:
                    raise ValueError('Teleport warning/summary mismatch')
                trips = {t.get('id'): dict(t.attrib) for t in ET.parse(folder/'trips.xml').getroot().findall('tripinfo')}
                travels = corridor_times(folder/'routes.xml', endpoints, set(cfg['mainline_edges']), set(teleports))
                rows.append(dict(controller=controller, seed=seed, scenario='pm_peak', window='full',
                                 seed_group='training', basis=LABEL, demand_basis=DEMAND_BASIS,
                                 **metrics(requested, trips, travels, teleports, begin, end)))
                cohort = {v for v, (depart, _) in requested.items() if begin <= depart < end}
                delays = movement_delays(folder/'routes.xml', net, mapping, cohort, set(teleports))
                for (site, direction, movement), source in sorted(reported.items()):
                    name = 'De Anza Blvd' if site == 211 else 'Stelling Rd'
                    approach = {'NB': 'S', 'SB': 'N', 'EB': 'W', 'WB': 'E'}[direction]
                    values = delays.get((name, approach, movement), [])
                    local.append(dict(controller=controller, seed=seed, site_id=site, direction=direction,
                                      movement=movement, n=len(values), simulated_segment_excess_s=mean(values),
                                      sample_status='observed' if values else 'no observed crossing; U-turns not mapped' if movement == 'U' else 'no observed crossing',
                                      vistro_hcm_delay_s=source['delay_s_per_vehicle'], vistro_los=source['los'],
                                      metric_note='Completed local crossings excluding teleports; approach+departure excess over external-edge freeflow, not HCM control delay',
                                      basis=LABEL, demand_basis=DEMAND_BASIS))
            print(f'{controller} seed {seed}: full PM training look complete', flush=True)
    p.write_csv('reports/vta_timing_comparison.csv', rows)
    p.write_csv('reports/vta_movement_comparison.csv', local)
    files = ['config/corridor.yaml', 'sim/routes_pm_peak.rou.xml', 'sim/corridor.net.xml',
             'sim/detectors.add.xml', 'sim/tls_actuated_pm_peak.add.xml', 'sim/tls_existing_vta_pm_peak.add.xml',
             'data/processed/vta_timing_2024.csv', 'data/processed/vta_vistro_results_2024.csv',
             'data/processed/tmc.csv', 'data/processed/tmc_sources.csv', 'data/processed/vta_counts_2024.csv']
    provenance = dict(basis=LABEL, demand_basis=DEMAND_BASIS, seeds=[0, 1, 2], window='full PM only', warmup_s=cfg['warmup_s'],
                      drain_s=1800, unfinished_charge_s=900, power=power.strip(),
                      sha256={f: hashlib.sha256((p.ROOT/f).read_bytes()).hexdigest() for f in files})
    (p.ROOT/'reports/vta_timing_run.json').write_text(json.dumps(provenance, indent=2)+'\n')


if __name__ == '__main__':
    compare()
