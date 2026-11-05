"""Saved console data must retain evaluation provenance and the shared JSON contract."""
import csv
from bisect import bisect_left
import json
import math
from pathlib import Path
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]
PRACTICE_SCORES = {('homestead', 'baseline'): (132.34455068986205, 0), ('homestead', 'proposed'): (75.89342291541692, 0),
                   ('stevens_creek', 'baseline'): (717.6687771704588, 918), ('stevens_creek', 'proposed'): (465.9814077793314, 76)}


class EngineerMetricsTest(unittest.TestCase):
    def test_saved_metrics(self):
        refs = {(r['road'], r['arm']): r for r in csv.DictReader((ROOT/'reports/learner_heldout/results.csv').read_text().splitlines()) if r['seed'] == '200'}
        headline = {'avg_delay_s_per_veh', 'stops_per_veh', 'travel_time_s', 'unfinished_trips', 'vehicles', 'co2_kg', 'fuel_l'}
        approach = {'volume_vph', 'aog_pct', 'split_failures', 'avg_delay_s', 'max_queue_veh'}
        def finite(value):
            if isinstance(value, dict):
                for child in value.values():
                    finite(child)
            elif isinstance(value, list):
                for child in value:
                    finite(child)
            elif isinstance(value, (int, float)):
                self.assertTrue(math.isfinite(value))
        for name in ('wolfe', 'deanza', 'homestead', 'stevens_creek'):
            with self.subTest(road=name):
                path = ROOT/f'dashboard/console/data/{name}/metrics.json'
                self.assertLess(path.stat().st_size, 1_500_000)
                data = json.loads(path.read_text())
                self.assertEqual(set(data), {'road', 'role', 'name', 'window', 'seeds', 'source', 'status', 'corridor', 'signals', 'time_space'})
                self.assertEqual(data['road'], name)
                self.assertEqual(data['seeds'], [200])
                self.assertEqual(data['window'], '16:30-18:30')
                cfg = yaml.safe_load((ROOT/f'roads/{name}/road.yaml').read_text())
                recommendation = json.loads((ROOT/f'reports/learner/{name}/card.json').read_text())
                saved_timings = {s['sumo_tls_id']: s for s in recommendation['signals']}
                self.assertEqual({s['id']: s['name'] for s in data['signals']},
                                 {s['sumo_tls_id']: s['name'] for s in cfg['signals']})
                self.assertIn('SUMO', data['source'])
                self.assertIn('900 s', data['source'])
                self.assertIn('HBEFA', data['source'])
                if name in ('homestead', 'stevens_creek'):
                    self.assertEqual(data['role'], 'practice')
                    self.assertIn('development-road measurement, seed 200; not held-out-road evaluation', data['source'])
                    self.assertNotIn('held-out simulation seed', data['source'])
                else:
                    self.assertEqual(data['role'], 'heldout')
                    self.assertIn('held-out simulation seed 200', data['source'])
                self.assertIn('VTA 2024 counts' if name == 'stevens_creek' else 'synthetic hidden-world demand', data['source'])
                finite(data)
                directions = ('EB', 'WB') if name in ('homestead', 'stevens_creek') else ('NB', 'SB')
                for arm, ref_arm in (('baseline', 'old'), ('proposed', 'learner')):
                    h = data['corridor'][arm]
                    self.assertEqual(set(h), headline)
                    self.assertEqual(set(h['travel_time_s']), set(directions))
                    self.assertTrue(all(v is not None and v > 0 for v in h['travel_time_s'].values()))
                    self.assertGreater(h['co2_kg'], 0)
                    self.assertGreater(h['fuel_l'], 0)
                    if (name, ref_arm) in refs:
                        ref = refs[name, ref_arm]
                        self.assertAlmostEqual(h['avg_delay_s_per_veh'], float(ref['all_requested_delay_s']), places=6)
                        self.assertEqual(h['unfinished_trips'], int(ref['unfinished']))
                    else:  # practice roads have no held-out reference; pin the scores the exporter has always produced
                        self.assertAlmostEqual(h['avg_delay_s_per_veh'], PRACTICE_SCORES[name, arm][0], places=6)
                        self.assertEqual(h['unfinished_trips'], PRACTICE_SCORES[name, arm][1])
                    self.assertGreater(h['vehicles'], h['unfinished_trips'])
                    series = data['corridor']['by15']
                    self.assertEqual(len(series), 8)
                    for point in series:
                        self.assertEqual(set(point[arm]), {'delay_s', 'queue_veh'} | {f'tt_{d.lower()}_s' for d in directions})
                    space = data['time_space'][arm]
                    self.assertEqual(set(space), {'green', 'trajectories'})
                    for direction in ('NB', 'SB', 'EB', 'WB'):
                        self.assertLessEqual(sum(t['dir'] == direction for t in space['trajectories']), 40)
                    for direction in directions:
                        starts = [t['pts'][0][0] for t in space['trajectories'] if t['dir'] == direction]
                        self.assertEqual({int((t-61200)//60) for t in starts}, set(range(10)))
                        self.assertTrue(all(sum(start <= t < start+60 for t in starts) <= 4 for start in range(61200, 61800, 60)))
                    for t in space['trajectories']:
                        self.assertTrue(all(61200 <= p[0] <= 61800 for p in t['pts']))
                    for signal in data['signals']:
                        self.assertEqual(set(signal), {'id', 'name', 'x_m', 'timing', 'approaches', 'by15', 'pcd'})
                        self.assertTrue(signal['name'])
                        self.assertEqual(len(signal['by15']), 8)
                        for point in signal['by15']:
                            self.assertEqual(set(point[arm]), {'delay_s', 'queue_veh', 'aog_pct'})
                        # The approach series split the intersection series: queues add up per 15 minutes.
                        for b, point in enumerate(signal['by15']):
                            self.assertAlmostEqual(point[arm]['queue_veh'], sum(a['by15'][b][arm]['queue_veh'] for a in signal['approaches']), places=6)
                        timing = signal['timing'][arm]
                        self.assertEqual(set(timing), {'cycle_s', 'offset_s', 'phases'})
                        saved = saved_timings[signal['id']]['new' if arm == 'proposed' and recommendation['decision'] == 'change' else 'old']
                        self.assertEqual(timing['cycle_s'], saved['cycle_s'])
                        self.assertEqual(timing['offset_s'], saved['offset_s'])
                        self.assertEqual([(p['phase'], p['green_s']) for p in timing['phases']],
                                         [(p['phase'], p['max_green_s']) for p in saved['greens']])
                        for phase in timing['phases']:
                            self.assertEqual(set(phase), {'phase', 'label', 'green_s', 'yellow_s', 'red_s'})
                            self.assertIsNone(phase['yellow_s'])
                            self.assertIsNone(phase['red_s'])
                        for a in signal['approaches']:
                            self.assertEqual(set(a), {'approach', 'baseline', 'proposed', 'by15'})
                            self.assertEqual([p['t'] for p in a['by15']], [p['t'] for p in signal['by15']])
                            for point in a['by15']:
                                self.assertEqual(set(point[arm]), {'delay_s', 'queue_veh', 'aog_pct'})
                            self.assertEqual(set(a[arm]), approach)
                            self.assertIsInstance(a[arm]['split_failures'], int)
                            self.assertGreaterEqual(a[arm]['split_failures'], 0)
                            if a[arm]['aog_pct'] is not None:
                                self.assertLessEqual(a[arm]['aog_pct'], 100)
                        pcd = signal['pcd'][arm]
                        self.assertEqual(set(pcd), {'arrivals', 'green', 'cycle_starts'})
                        starts = pcd['cycle_starts']
                        self.assertTrue(starts)
                        self.assertEqual(starts, sorted(set(starts)))
                        self.assertTrue(all(58500 < t < 68400 for t in starts))
                        for arrival, into_cycle in pcd['arrivals']:
                            index = bisect_left(starts, arrival-into_cycle-.02)
                            self.assertLess(index, len(starts))
                            self.assertAlmostEqual(arrival-into_cycle, starts[index], delta=.02)
                            self.assertLessEqual(starts[index], arrival+.02)
                            if index+1 < len(starts):
                                self.assertLessEqual(arrival, starts[index+1]+.02)
                        self.assertLessEqual(len(pcd['arrivals']), 3000)
                        self.assertTrue(all(len(p) == 2 and 59400 <= p[0] <= 66600 for p in pcd['arrivals']))
                if name == 'deanza':
                    self.assertEqual(data['status'], 'keep_current')
                    self.assertEqual(data['corridor']['baseline'], data['corridor']['proposed'])
