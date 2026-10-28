import csv
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from signal_lab import pipeline as p, demand as d
from signal_lab.baseline import LABEL


class BaselineTests(unittest.TestCase):
    def test_plans_and_clearance_paths(self):
        with open(p.ROOT/'data/processed/timing_inputs.csv') as stream:
            inputs = {(r['sumo_tls_id'], int(r['phase'])): r for r in csv.DictReader(stream)}
        for scenario in ('pm_peak', 'night'):
            path = p.ROOT/f'sim/tls_actuated_{scenario}.add.xml'
            self.assertIn(LABEL, path.read_text())
            plans = ET.parse(path).getroot().findall('tlLogic')
            self.assertEqual({t.get('id') for t in plans}, {s['sumo_tls_id'] for s in p.config()['signals']})
            cycles = set()
            for logic in plans:
                params = {v.get('key'): v.get('value') for v in logic.findall('param')}
                self.assertEqual(logic.get('type'), 'actuated')
                self.assertEqual(params['coordinated'], 'true')
                self.assertEqual(float(params['max-gap']), 3)
                cycle = float(params['cycleTime'])
                cycles.add(cycle)
                self.assertTrue(0 <= float(logic.get('offset')) < cycle)
                phases = logic.findall('phase')
                greens = [i for i, phase in enumerate(phases) if 'y' not in phase.get('state') and 'G' in phase.get('state')]
                main = next(i for i in greens if phases[i].get('name') == 'mainline')
                order = greens[greens.index(main):]+greens[:greens.index(main)]
                for i in greens:
                    phase = phases[i]
                    row = inputs[logic.get('id'), i]
                    self.assertEqual(float(phase.get('minDur')), float(row['min_green_s']))
                    self.assertLess(float(phase.get('minDur')), float(phase.get('maxDur')))
                    self.assertLessEqual(float(phase.get('maxDur')), float(row['max_green_s']))
                    self.assertTrue(0 < float(phase.get('latestEnd')) <= cycle)
                    for successor in map(int, phase.get('next').split()):
                        if successor == i:
                            self.assertEqual(i, main)
                            continue
                        yellow = phases[successor]
                        red = phases[int(yellow.get('next'))]
                        target = int(red.get('next'))
                        self.assertEqual(yellow.get('state'), ''.join('y' if c in 'Gg' else 'r' for c in phase.get('state')))
                        self.assertEqual(red.get('state'), 'r'*len(phase.get('state')))
                        self.assertEqual(float(yellow.get('duration')), float(row['yellow_s']))
                        self.assertEqual(float(red.get('duration')), float(row['red_clear_s']))
                        self.assertTrue(target == main or order.index(target) > order.index(i))
            self.assertEqual(len(cycles), 1)

    def night_states(self, folder, cars):
        root = ET.Element('routes')
        for tls_id, incoming, outgoing in cars:
            vehicle = ET.SubElement(root, 'vehicle', id=tls_id, depart='84600', departLane='best')
            ET.SubElement(vehicle, 'route', edges=f'{incoming} {outgoing}')
        routes = folder/'routes.xml'
        p.xml_write(root, routes)
        extra = ET.Element('additional')
        for signal in p.config()['signals']:
            ET.SubElement(extra, 'timedEvent', type='SaveTLSStates', source=signal['sumo_tls_id'], dest=str(folder/'states.xml'))
        p.xml_write(extra, folder/'output.xml')
        p.run([p.BIN/'sumo', '-n', p.ROOT/'sim/corridor.net.xml', '-r', routes,
               '-a', f'{p.ROOT}/sim/detectors.add.xml,{p.ROOT}/sim/tls_actuated_night.add.xml,{folder}/output.xml',
               '-b', '81900', '-e', '86400', '--no-step-log', '--tripinfo-output', folder/'trips.xml', '--summary-output', folder/'summary.xml'])
        self.assertEqual(d.summary_stats(folder/'summary.xml')['teleports'], 0)
        return ET.parse(folder/'states.xml').getroot(), ET.parse(folder/'trips.xml').getroot()

    def test_night_mainline_rests_for_hour_without_side_cars(self):
        plans = ET.parse(p.ROOT/'sim/tls_actuated_night.add.xml').getroot()
        main = {t.get('id'): next(phase.get('state') for phase in t.findall('phase') if phase.get('name') == 'mainline') for t in plans}
        mapping = d.movement_map(d.network())
        through = [(s['sumo_tls_id'], *mapping[s['name'], 'E', 'T']) for s in p.config()['signals']]
        for cars in ([], through):
            with tempfile.TemporaryDirectory() as temp:
                states, trips = self.night_states(Path(temp), cars)
                self.assertEqual(len(trips), len(cars))
                hour = [s for s in states if float(s.get('time')) >= 82800]
                self.assertEqual(len(hour), 3600*5)
                self.assertTrue(all(s.get('state') == main[s.get('id')] for s in hour))

    def test_night_side_green_only_after_side_car(self):
        net = d.network()
        mapping = d.movement_map(net)
        cars, indices = [], {}
        for signal in p.config()['signals']:
            key = next(k for k in mapping if k[0] == signal['name'] and k[1] in ('N', 'S') and k[2] in ('L', 'T'))
            incoming, outgoing = mapping[key]
            tls_id = signal['sumo_tls_id']
            cars.append((tls_id, incoming, outgoing))
            indices[tls_id] = {c[2] for c in net.getTLS(tls_id).getConnections()
                               if c[0].getEdge().getID() == incoming and c[1].getEdge().getID() == outgoing}
        with tempfile.TemporaryDirectory() as temp:
            states, trips = self.night_states(Path(temp), cars)
            self.assertEqual(len(trips), 5, 'All five called movements must complete')
            for tls_id, links in indices.items():
                served = [float(s.get('time')) for s in states if s.get('id') == tls_id and float(s.get('time')) >= 82800
                          and any(s.get('state')[i] in 'Gg' for i in links)]
                self.assertTrue(served, tls_id)
                self.assertGreaterEqual(min(served), 84600, tls_id)
