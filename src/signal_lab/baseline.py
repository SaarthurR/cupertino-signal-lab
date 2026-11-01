"""SUMO's Webster seed and coordinator, converted to detector-actuated plans."""
import csv
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from . import pipeline as p
from .demand import seconds, simulation

LABEL = "textbook coordinated-actuated baseline (not Cupertino's current timing)"


def baseline():
    cfg = p.config()
    logs = []
    for scenario, period in cfg['scenarios'].items():
        logs.extend(actuated(p.ROOT/'sim/corridor.net.xml', p.ROOT/f'sim/routes_{scenario}.rou.xml',
                             seconds(period['begin']), [s['sumo_tls_id'] for s in cfg['signals']],
                             cfg['mainline_edges'], p.ROOT/'data/processed/timing_inputs.csv',
                             f'sim/tls_actuated_{scenario}.add.xml'))
    _report(cfg, logs)


def actuated(net_path, routes, begin, tls_ids, mainline_edges, inputs_path, output):
    """Webster seed on `routes`, made detector-actuated and coordinated; writes `output`, returns tool logs."""
    with open(inputs_path) as stream:
        inputs = {(r['sumo_tls_id'], int(r['phase'])): r for r in csv.DictReader(stream)}
    net = p.sumolib.net.readNet(str(net_path))
    logs = []
    with tempfile.TemporaryDirectory() as temp:
        seed, offsets = Path(temp)/'seed.xml', Path(temp)/'offsets.xml'
        logs.append(p.tool('tlsCycleAdaptation.py', '-n', net_path,
                           '-r', routes, '-b', begin, '-u', '-o', seed))
        root = ET.parse(seed).getroot()
        for logic in root.findall('tlLogic'):
            if logic.get('id') not in tls_ids:
                root.remove(logic)
        if {t.get('id') for t in root.findall('tlLogic')} != set(tls_ids):
            raise ValueError('Webster seed must cover every listed signal')
        cycles = []
        for logic in root.findall('tlLogic'):
            phases = logic.findall('phase')
            greens = [i for i in range(len(phases)) if (logic.get('id'), i) in inputs]
            tls = net.getTLS(logic.get('id'))
            main = max(greens, key=lambda i: sum(phases[i].get('state')[c[2]] == 'G'
                       for c in tls.getConnections() if c[0].getEdge().getID() in mainline_edges))
            logic.set('type', 'actuated')
            logic.set('programID', 'actuated')
            elapsed = 0
            for i, phase in enumerate(phases):
                row = inputs.get((logic.get('id'), i))
                if row:
                    minimum = float(row['min_green_s'])
                    maximum = min(float(row['max_green_s']), max(10, minimum+1, float(phase.get('duration'))))
                    phase.set('minDur', str(minimum))
                    phase.set('maxDur', str(maximum))
                    phase.set('duration', str(maximum))
                    phase.set('name', 'mainline' if i == main else f'phase_{i}')
                else:
                    previous = max(g for g in greens if g < i)
                    row = inputs[logic.get('id'), previous]
                    phase.set('duration', row['yellow_s'] if 'y' in phase.get('state') else row['red_clear_s'])
                if i in greens:
                    elapsed += float(phase.get('duration'))
                    phase.set('latestEnd', str(round(elapsed, 3)))
                    elapsed += float(row['yellow_s']) + float(row['red_clear_s'])
                phase.set('next', str((i+1) % len(phases)))
            cycles.append(elapsed)
            ET.SubElement(logic, 'param', key='detector-gap', value='0.5')
            # Forward skips preserve green order; added clearances also cover skipped left phases.
            order = greens[greens.index(main):] + greens[:greens.index(main)]
            for position, i in enumerate(order):
                targets = ([i] if i == main else [])
                successors = order[position+1:] if i == main else [main] + order[position+1:]
                for target in successors:
                    start = len(logic.findall('phase'))
                    row = inputs[logic.get('id'), i]
                    state = ''.join('y' if c in 'Gg' else 'r' for c in phases[i].get('state'))
                    ET.SubElement(logic, 'phase', duration=row['yellow_s'], state=state, next=str(start+1))
                    ET.SubElement(logic, 'phase', duration=row['red_clear_s'], state='r'*len(state), next=str(target))
                    targets.append(start)
                phases[i].set('next', ' '.join(map(str, targets)))
            for key, value in [('max-gap', inputs[logic.get('id'), main]['passage_s']),
                               ('coordinated', 'true')]:
                ET.SubElement(logic, 'param', key=key, value=value)
        # Clipped Webster greens and engineering clearances must fit one shared background cycle.
        cycle = round(max(cycles), 3)
        for logic in root.findall('tlLogic'):
            ET.SubElement(logic, 'param', key='cycleTime', value=str(cycle))
        # Coordinator reads a linear nominal schedule, not the alternative transition branches.
        nominal = ET.Element('additional')
        for logic in root.findall('tlLogic'):
            fixed = ET.SubElement(nominal, 'tlLogic', id=logic.get('id'), type='static', programID='actuated', offset='0')
            for i, phase in enumerate(logic.findall('phase')):
                if phase.get('minDur') is None:
                    continue
                row = inputs[logic.get('id'), i]
                ET.SubElement(fixed, 'phase', duration=phase.get('duration'), state=phase.get('state'))
                ET.SubElement(fixed, 'phase', duration=row['yellow_s'], state=''.join('y' if c in 'Gg' else 'r' for c in phase.get('state')))
                ET.SubElement(fixed, 'phase', duration=row['red_clear_s'], state='r'*len(phase.get('state')))
        p.xml_write(nominal, seed)
        logs.append(p.tool('tlsCoordinator.py', '-n', net_path,
                           '-r', routes, '-a', seed, '-o', offsets))
        offset_map = {t.get('id'): float(t.get('offset')) % cycle for t in ET.parse(offsets).getroot().findall('tlLogic')}
        if set(offset_map) != {t.get('id') for t in root.findall('tlLogic')}:
            raise ValueError('Coordinator must cover every listed signal')
        for logic in root.findall('tlLogic'):
            logic.set('offset', str(round(offset_map[logic.get('id')], 3)))
        root.insert(0, ET.Comment(LABEL))
        p.xml_write(root, output)
    return logs


def _report(cfg, logs):
    results = []
    for scenario in cfg['scenarios']:
        with tempfile.TemporaryDirectory() as temp:
            stat = simulation(scenario, temp)
        results.append(f'| {scenario} | {stat["inserted"]} | {stat["teleports"]} | {stat["running"]} | {stat["waiting"]} | {stat["mean_time_loss_s"]:.3f} | {stat["completed_after_warmup"]} |')
    (p.ROOT/'reports/M4-REPORT.md').write_text(f'# M4 baseline\n\n{LABEL}\n\nWebster unified-cycle seed uses the first scenario hour; greens are bounded by timing_inputs.csv min/max (60 s ceiling from section 6.4; longer Webster greens are clipped). Yellow/red clearances use the same inputs. The common background cycle is the longest resulting nominal plan including full clearances (Webster seed adjusted to engineering bounds). Forward phase skips have full yellow/all-red clearances; mainline self-successor rests without changing color. Offsets come from tlsCoordinator on the linear nominal schedules, excluding alternative transition branches. SUMO supplies built-in loop actuation with a 0.5 s detector gap: default upstream loops miss vehicles spawned on short boundary lanes; stop-bar loops at 1 m miss cars stopped at red.\n\nReference: https://sumo.dlr.de/docs/Simulation/Traffic_Lights.html#dynamic_phase_selection_phase_skipping\n\n## Scenario runs (seed 0)\n\nTime loss averages completed trips departing within the scenario, excludes warmup departures, and includes a 30-minute drain. Inserted/teleports include warmup and drain; unfinished trips are absent from the mean.\n\n| Scenario | Inserted | Teleports | Running after drain | Waiting to insert | Mean time loss (s) | Completed after warmup |\n|---|---:|---:|---:|---:|---:|---:|\n'+'\n'.join(results)+'\n\n## Tool output\n```\n'+'\n'.join(logs)+'\n```\n')
    print(f'baseline: {LABEL}; both scenarios written')
