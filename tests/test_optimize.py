import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import xml.etree.ElementTree as ET

from signal_lab import optimize as o, pipeline as p


class OptimizeTests(unittest.TestCase):
    def test_split_bounds_and_webster_proportions(self):
        with open(p.ROOT/'data/processed/timing_inputs.csv') as stream:
            inputs = list(csv.DictReader(stream))
        for signal in p.config()['signals']:
            rows = [r for r in inputs if r['sumo_tls_id'] == signal['sumo_tls_id']]
            base = [15.+i*5 for i in range(len(rows))]
            for cycle in (80, 117.9, 150):
                for split in (.6, 1., 1.4):
                    greens = o.split_greens(cycle, split, rows, 0, base, 117.9)
                    self.assertLessEqual(sum(greens)+sum(float(r['yellow_s'])+float(r['red_clear_s']) for r in rows), cycle+1e-8)
                    for green, row in zip(greens, rows):
                        self.assertTrue(10 <= green <= 60)
                        self.assertGreater(green, float(row['min_green_s']))
        rows = [dict(min_green_s=7, max_green_s=60, yellow_s=3, red_clear_s=1)]*4
        greens = o.split_greens(100, 1.2, rows, 0, [20, 12, 24, 16], 100)
        self.assertAlmostEqual(greens[2]/greens[1], 2)
        self.assertAlmostEqual(greens[3]/greens[1], 16/12)
        for cycle, split, phases in ((79, 1., rows), (80, .5, rows), (80, 1., rows*10)):
            with self.assertRaises(ValueError):
                o.split_greens(cycle, split, phases, 0, [20]*len(phases), 117.9)

    def test_baseline_is_exactly_representable(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)/'plan.xml'
            o.plan('pm_peak', o.baseline_params(), target)
            old = ET.parse(p.ROOT/'sim/tls_actuated_pm_peak.add.xml').getroot().findall('tlLogic')
            new = ET.parse(target).getroot().findall('tlLogic')
            for before, after in zip(old, new):
                self.assertAlmostEqual(float(before.get('offset')), float(after.get('offset')))
                for a, b in zip(before.findall('phase'), after.findall('phase')):
                    for key in ('duration', 'maxDur', 'latestEnd'):
                        if a.get(key) is not None:
                            self.assertAlmostEqual(float(a.get(key)), float(b.get(key)))
                    for key in ('state', 'next', 'minDur', 'name'):
                        self.assertEqual(a.get(key), b.get(key))
                for a, b in zip(before.findall('param'), after.findall('param')):
                    self.assertEqual(a.get('key'), b.get('key'))
                    if a.get('key') == 'coordinated':
                        self.assertEqual(a.get('value'), b.get('value'))
                    else:
                        self.assertEqual(float(a.get('value')), float(b.get('value')))

    def test_plan_and_timing_contracts(self):
        params = dict(cycle_s=100, passage_s=2.5)
        for i in range(5):
            params.update({f'offset_{i}': .2*i, f'split_{i}': .6})
        for scenario in ('pm_peak', 'night'):
            with tempfile.TemporaryDirectory() as temp:
                target = Path(temp)/'plan.xml'
                timing = o.plan(scenario, params, target)
                old = ET.parse(p.ROOT/f'sim/tls_actuated_{scenario}.add.xml').getroot().findall('tlLogic')
                new = ET.parse(target).getroot().findall('tlLogic')
                self.assertEqual(len(new), 5)
                expected = []
                for index, (before, after) in enumerate(zip(old, new)):
                    self.assertEqual(after.get('id'), before.get('id'))
                    self.assertEqual(after.get('type'), 'actuated')
                    self.assertEqual(after.get('programID'), 'optuna')
                    self.assertAlmostEqual(float(after.get('offset')), 20*index)
                    settings = {r.get('key'): r.get('value') for r in after.findall('param')}
                    self.assertEqual(float(settings['cycleTime']), 100)
                    self.assertEqual(float(settings['max-gap']), 2.5)
                    elapsed = 0
                    for phase, (a, b) in enumerate(zip(before.findall('phase'), after.findall('phase'))):
                        for attr in ('state', 'next', 'minDur', 'name'):
                            self.assertEqual(a.get(attr), b.get(attr))
                        if a.get('minDur') is None:
                            self.assertEqual(a.attrib, b.attrib)
                            continue
                        maximum = float(b.get('maxDur'))
                        self.assertTrue(10 <= maximum <= 60)
                        self.assertGreater(maximum, float(b.get('minDur')))
                        expected.append(dict(sumo_tls_id=after.get('id'), cycle_s=100, offset_s=float(after.get('offset')),
                                             phase=phase, max_green_s=maximum, passage_s=2.5))
                        self.assertTrue(elapsed < float(b.get('latestEnd')) <= 100)
                        elapsed = float(b.get('latestEnd'))
                self.assertEqual(timing, expected)
                p.write_csv(Path(temp)/'timing.csv', timing)
                with open(Path(temp)/'timing.csv') as stream:
                    reader = csv.DictReader(stream)
                    self.assertEqual(reader.fieldnames, ['sumo_tls_id','cycle_s','offset_s','phase','max_green_s','passage_s'])
                    self.assertEqual(len(list(reader)), len(expected))

    def test_persisted_file_contracts(self):
        for scenario in ('pm_peak', 'night'):
            plans = ET.parse(p.ROOT/f'sim/tls_optuna_{scenario}.add.xml').getroot().findall('tlLogic')
            with open(p.ROOT/f'reports/timing_{scenario}.csv') as stream:
                reader = csv.DictReader(stream)
                self.assertEqual(reader.fieldnames, ['sumo_tls_id','cycle_s','offset_s','phase','max_green_s','passage_s'])
                rows = {(r['sumo_tls_id'], int(r['phase'])): r for r in reader}
            self.assertEqual({t.get('id') for t in plans}, {s['sumo_tls_id'] for s in p.config()['signals']})
            seen = set()
            for logic in plans:
                self.assertEqual(logic.get('programID'), 'optuna')
                params = {v.get('key'): v.get('value') for v in logic.findall('param')}
                cycle = float(params['cycleTime'])
                self.assertTrue(80 <= cycle <= 150)
                self.assertTrue(0 <= float(logic.get('offset')) < cycle)
                self.assertTrue(2 <= float(params['max-gap']) <= 4)
                for index, phase in enumerate(logic.findall('phase')):
                    if phase.get('minDur') is None:
                        continue
                    key = logic.get('id'), index
                    seen.add(key)
                    row = rows[key]
                    self.assertEqual(float(row['cycle_s']), cycle)
                    self.assertEqual(float(row['offset_s']), float(logic.get('offset')))
                    self.assertEqual(float(row['max_green_s']), float(phase.get('maxDur')))
                    self.assertEqual(float(row['passage_s']), float(params['max-gap']))
                    self.assertTrue(10 <= float(phase.get('maxDur')) <= 60)
                    self.assertTrue(0 < float(phase.get('latestEnd')) <= cycle)
            self.assertEqual(set(rows), seen)

    def test_fit_routes_no_holdout_and_side_classification(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'routes.xml'
            begin, end, requested = o.fit_routes('pm_peak', path)
            self.assertEqual((begin, end), (59400, 63000))
            vehicles = ET.parse(path).getroot().findall('vehicle')
            self.assertTrue(all(58500 <= float(v.get('depart')) < 63000 for v in vehicles))
            self.assertEqual(set(requested), {v.get('id') for v in vehicles if float(v.get('depart')) >= begin})
            self.assertTrue(any(requested.values()))
            self.assertFalse(all(requested.values()))

    def test_score_penalizes_uninserted_unfinished_and_teleports(self):
        def run(args):
            summary = Path(args[args.index('--summary-output')+1])
            trips = Path(args[args.index('--tripinfo-output')+1])
            summary.write_text('<summary><step teleports="1" inserted="3" running="1" waiting="1"/></summary>')
            trips.write_text('<tripinfos><tripinfo id="done" arrival="1" timeLoss="20" departDelay="30" waitingCount="2"/></tripinfos>')
            self.assertEqual(args[args.index('--seed')+1], 2)
            self.assertEqual(args[args.index('-e')+1], 64800)
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(o, 'fit_routes', return_value=(59400, 63000, {'done': True, 'running': False, 'waiting': False})), patch.object(p, 'run', side_effect=run):
                stats = o.score('pm_peak', 2, 'plan.xml', temp)
        self.assertEqual(stats['unfinished'], 2)
        self.assertEqual(stats['mean_time_loss_s'], 20)
        self.assertEqual(stats['deferred_penalty_s'], (30+1800*3)/3)
        self.assertEqual(o.objective_value(stats, {'side_time_loss_s': 10}), 20+(30+1800*3)/3+8)
