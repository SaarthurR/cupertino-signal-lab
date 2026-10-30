"""A conservative projection of Vistro inputs onto the existing SUMO stages."""
import csv
import xml.etree.ElementTree as ET

from . import pipeline as p
from .demand import movement_map, network

LABEL = "Timing inputs in VTA's 2024 CMP model, not a confirmed city controller sheet"
# Existing paired stages cannot reproduce independent rings or the De Anza lag.
GROUPS = {211: {7: (1, 5), 5: (2, 6), 2: (3, 7), 0: (8, 4)},
          217: {2: (1, 5), 0: (2, 6), 5: (3,), 7: (4,)}}


def timing_rows():
    with open(p.ROOT/'data/processed/vta_timing_2024.csv', newline='') as stream:
        return list(csv.DictReader(stream))


def source_issues(rows):
    """Expose source contradictions rather than silently repairing transcription."""
    issues = []
    for site in (211, 217):
        selected = [r for r in rows if int(r['site_id']) == site]
        cycle = float(selected[0]['cycle_s'])
        for ring in (1, 2):
            total = sum(float(r['split_s']) for r in selected if int(r['ring']) == ring)
            # Stelling's second ring is inactive during the two split side approaches (p.5).
            if site == 217 and ring == 2:
                total += sum(float(r['split_s']) for r in selected if r['control_type'] == 'Split')
            if total != cycle:
                issues.append(f'{site} ring {ring}: splits {total:g} s != cycle {cycle:g} s')
        for row in selected:
            if float(row['max_green_s'])+float(row['amber_s'])+float(row['all_red_s']) > float(row['split_s']):
                issues.append(f"{site} SG {row['signal_group']}: reported maximum green plus clearance exceeds split")
            if float(row['walk_s'])+float(row['ped_clearance_s']) > float(row['max_green_s']):
                issues.append(f"{site} SG {row['signal_group']}: walk plus pedestrian clearance exceeds reported maximum green")
    return issues


def existing_vta():
    """Write only the new PM plan; never regenerate textbook or frozen plans."""
    rows = timing_rows()
    root = ET.parse(p.ROOT/'sim/tls_actuated_pm_peak.add.xml').getroot()
    cfg = p.config()
    net = network()
    movements = movement_map(net)
    mapped = []
    for site, stages in GROUPS.items():
        source = {int(r['signal_group']): r for r in rows if int(r['site_id']) == site}
        first = next(iter(source.values()))
        signal = next(s for s in cfg['signals'] if s['name'] == first['intersection'])
        old = next(t for t in root.findall('tlLogic') if t.get('id') == signal['sumo_tls_id'])
        cycle = float(first['cycle_s'])
        # First stage starts SG1 (first lead green in ring 1), matching the source reference.
        logic = ET.Element('tlLogic', id=old.get('id'), type='actuated', programID='existing_vta', offset=first['offset_s'])
        elapsed = 0.
        clearances = {}
        for textbook_phase, groups in stages.items():
            selected = [source[g] for g in groups]
            split = min(float(r['split_s']) for r in selected)
            yellow = max(float(r['amber_s']) for r in selected)
            red = max(float(r['all_red_s']) for r in selected)
            # shortcut: shorter paired split and full clearances, replace with verified ring logic later.
            maximum = split-yellow-red
            minimum = max(float(r['min_green_s']) for r in selected)
            if not 0 < minimum < maximum:
                raise ValueError(f'{site} stage {textbook_phase} cannot fit its minimum and clearances')
            state = old.findall('phase')[textbook_phase].get('state').replace('g', 'r')
            if site == 217 and textbook_phase in (5, 7):
                # Vistro uses separate NB/SB split approaches, not simultaneous opposing lefts.
                approach = 'S' if textbook_phase == 5 else 'N'
                pairs = {pair for (name, leg, _), pair in movements.items()
                         if name == signal['name'] and leg == approach}
                links = {link for a, b, link in net.getTLS(signal['sumo_tls_id']).getConnections()
                         if (a.getEdge().getID(), b.getEdge().getID()) in pairs}
                state = ''.join('G' if link in links else 'r' for link in range(len(state)))
            index = len(logic.findall('phase'))
            recall = any(r['maximum_recall'] == 'Yes' for r in selected)
            if recall:
                main = index
            ET.SubElement(logic, 'phase', duration=str(maximum), state=state, minDur=str(minimum),
                          maxDur=str(maximum), latestEnd=str(round(elapsed+maximum, 6)),
                          name='recall_rest' if recall else f'phase_{index}')
            ET.SubElement(logic, 'phase', duration=str(yellow), state=''.join('y' if c == 'G' else 'r' for c in state))
            ET.SubElement(logic, 'phase', duration=str(red), state='r'*len(state))
            elapsed += split
            clearances[index] = yellow, red
            mapped.append(dict(site_id=site, sumo_tls_id=logic.get('id'), phase=index, textbook_phase=textbook_phase,
                               signal_groups=';'.join(map(str, groups)), cycle_s=cycle, offset_s=float(first['offset_s']),
                               applied_split_s=split, min_green_s=minimum, max_green_s=maximum,
                               yellow_s=yellow, red_clear_s=red, basis=LABEL))
        if elapsed > cycle:
            raise ValueError(f'{site}: mapped stage splits exceed source cycle')
        # Same forward-skip / recall-rest construction as baseline.py; every skip clears fully.
        phases = logic.findall('phase')
        indices = list(clearances)
        order = indices[indices.index(main):]+indices[:indices.index(main)]
        for index, phase in enumerate(phases):
            phase.set('next', str((index+1) % len(phases)))
        for position, index in enumerate(order):
            phase = phases[index]
            targets = [index] if index == main else []
            successors = order[position+1:] if index == main else [main]+order[position+1:]
            for target in successors:
                start = len(logic.findall('phase'))
                yellow, red = clearances[index]
                state = ''.join('y' if c == 'G' else 'r' for c in phase.get('state'))
                ET.SubElement(logic, 'phase', duration=str(yellow), state=state, next=str(start+1))
                ET.SubElement(logic, 'phase', duration=str(red), state='r'*len(state), next=str(target))
                targets.append(start)
            phase.set('next', ' '.join(map(str, targets)))
        for key, value in [('detector-gap', .5), ('max-gap', min(float(r['vehicle_extension_s']) for r in source.values())),
                           ('coordinated', 'true'), ('cycleTime', cycle)]:
            ET.SubElement(logic, 'param', key=key, value=str(value))
        for row in mapped:
            if row['site_id'] == site:
                row.update(nominal_slack_s=cycle-elapsed)
        root.insert(list(root).index(old), logic)
        root.remove(old)
    for logic in root.findall('tlLogic'):
        logic.set('programID', 'existing_vta')
    root.insert(0, ET.Comment(LABEL+'; conservative stage projection; see docs/vta-timing.md'))
    root.insert(1, ET.Comment('Bandley, Saich and Mary retain textbook timings and cycle: source sites have different cycles'))
    p.xml_write(root, 'sim/tls_existing_vta_pm_peak.add.xml')
    p.write_csv('reports/timing_existing_vta_pm_peak.csv', mapped)
    print('\n'.join(source_issues(rows)))
    print('existing_vta: '+LABEL)


if __name__ == '__main__':
    existing_vta()
