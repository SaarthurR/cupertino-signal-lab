import tempfile
import unittest
from pathlib import Path

from signal_lab import evaluate as e, pipeline as p


class EvaluateTests(unittest.TestCase):
    def test_scheduled_cohorts_include_delayed_and_uninserted_demand(self):
        requested = {'warm': (99, False), 'late': (100, True), 'missing': (110, False),
                     'running': (115, False), 'next': (120, False)}
        trips = {vid: dict(arrival=200, timeLoss=loss, waitingCount=2, departDelay=30)
                 for vid, loss in [('warm', 1000), ('late', 20), ('next', 900)]}
        trips['running'] = dict(arrival=-1, timeLoss=100)
        travels = {'warm': ('eb', 900), 'late': ('eb', 50), 'running': ('wb', 60)}
        stats = e.metrics(requested, trips, travels, ['warm', 'late', 'late'], 100, 120)
        self.assertEqual((stats['requested'], stats['completed'], stats['unfinished']), (3, 1, 2))
        self.assertAlmostEqual(stats['all_vehicle_delay_s'], (50+1800*(2+2))/3)
        self.assertAlmostEqual(stats['all_vehicle_delay_zero_unfinished_s'], (50+1800*2)/3)
        self.assertEqual(stats['mean_time_loss_s'], 20)
        self.assertEqual(stats['side_time_loss_s'], 20)
        self.assertEqual(stats['mean_waiting_count'], 2)
        self.assertEqual((stats['teleports'], stats['teleported_vehicles']), (2, 1))
        self.assertEqual(stats['mainline_travel_eb_s'], 50)
        self.assertEqual(stats['mainline_travel_wb_s'], 60)

    def test_corridor_entry_exit_and_teleport_exclusion(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'routes.xml'
            path.write_text('''<routes>
            <vehicle id="east" depart="5"><route edges="side a b c after" exitTimes="10 20 40 70 100"/></vehicle>
            <vehicle id="west" depart="8"><route edges="c b a" exitTimes="20 30 60"/></vehicle>
            <vehicle id="teleport" depart="5"><route edges="a b c" exitTimes="10 20 30"/></vehicle>
            <vehicle id="partial" depart="5"><route edges="a b c" exitTimes="10 -1 -1"/></vehicle>
            <vehicle id="detour" depart="5"><route edges="a side c" exitTimes="10 20 30"/></vehicle>
            </routes>''')
            times = e.corridor_times(path, {'eb': ('a', 'c'), 'wb': ('c', 'a')}, {'a', 'b', 'c'}, {'teleport'})
        self.assertEqual(times, {'east': ('eb', 60), 'west': ('wb', 52)})

    def test_real_boundaries_and_identical_sumo_conditions(self):
        cfg = p.config()
        endpoints = e.boundaries(cfg)
        self.assertEqual(set(endpoints), {'eb', 'wb'})
        for pair in endpoints.values():
            self.assertTrue(set(pair) <= set(cfg['mainline_edges']))
        a = e.command('pm_peak', 'actuated', 3, cfg)
        b = e.command('pm_peak', 'optuna', 3, cfg)
        differing = [(x, y) for x, y in zip(a, b) if x != y]
        self.assertEqual(len(differing), 1)
        self.assertIn('tls_actuated_pm_peak', differing[0][0])
        self.assertIn('tls_optuna_pm_peak', differing[0][1])
        self.assertEqual(a[a.index('--time-to-teleport')+1], 300)
        self.assertEqual(a[a.index('-b')+1], 58500)

    def test_paired_wilcoxon_separates_fit_seeds_and_handles_ties(self):
        rows = [dict(controller=c, scenario='night', window='full', seed=s,
                     seed_group='fit_used' if s < 3 else 'out_of_sample',
                     mean_time_loss_s=10 if c == 'actuated' else 9)
                for c in e.CONTROLLERS for s in e.SEEDS]
        for row in rows:
            row.update({m: row['mean_time_loss_s'] for m in (
                'all_vehicle_delay_s', 'all_vehicle_delay_zero_unfinished_s',
                'unfinished', 'mainline_travel_eb_s', 'mainline_travel_wb_s')})
        tests = [t for t in e.paired_tests(rows) if t['metric'] == 'mean_time_loss_s']
        self.assertEqual([t['n'] for t in tests], [13, 10])
        self.assertAlmostEqual(tests[1]['p_value'], 1/1024)
        for row in rows:
            for key in ('mean_time_loss_s', 'all_vehicle_delay_s',
                        'all_vehicle_delay_zero_unfinished_s', 'unfinished',
                        'mainline_travel_eb_s', 'mainline_travel_wb_s'):
                row[key] = 10
        self.assertTrue(all(t['p_value'] == 1 for t in e.paired_tests(rows)))
        with self.assertRaisesRegex(ValueError, 'Unpaired'):
            e.paired_tests(rows[:-1])
