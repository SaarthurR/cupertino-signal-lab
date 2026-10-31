import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import xml.etree.ElementTree as ET

from signal_lab import evaluate as e, optimize as o, pipeline as p


class V4Tests(unittest.TestCase):
    def test_widened_cycle_and_frozen_legacy_bounds(self):
        self.assertEqual(o.bounds('cycle_s'), (80, 150))
        self.assertEqual(o.bounds('cycle_s', 4), (80, 180))
        params = dict(o.baseline_params(), cycle_s=180)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'plan.xml'
            with self.assertRaises(ValueError):
                o.plan('pm_peak', params, path)
            timing = o.plan('pm_peak', params, path, 4)
            self.assertTrue(all(10 <= r['max_green_s'] <= 60 for r in timing))
            self.assertTrue(all(t.get('programID') == 'optuna_v4'
                                for t in ET.parse(path).getroot().findall('tlLogic')))

    def test_battery_cutoff(self):
        for source, percent, stops in [('Battery', 24, True), ('Battery', 25, False), ('AC', 24, False)]:
            with patch.object(p.subprocess, 'check_output', return_value=f"Now drawing from '{source} Power'\n{percent}%;"):
                if stops:
                    with self.assertRaisesRegex(RuntimeError, 'below 25'):
                        p.check_battery()
                else:
                    p.check_battery()

    def test_sensitivity_uses_side_denominator_and_four_controllers(self):
        row = dict(side_all_requested_delay_s=1000, side_unfinished=2, side_teleports=1, side_requested=3)
        self.assertEqual(e.side_delay(row, 0), 100)
        self.assertEqual(e.side_delay(row, 1800), 1900)
        controllers = ('actuated', 'optuna_v3', 'optuna_v4', 'existing_vta')
        rows = [dict(controller=c, scenario='pm_peak', window='holdout', seed=s, seed_group='v4_final',
                     **{m: 100 if c == 'actuated' else 90 for m in e.TEST_METRICS})
                for c in controllers for s in range(53, 73)]
        tests = e.paired_tests(rows, controllers)
        self.assertEqual({t['controller'] for t in tests}, set(controllers)-{'actuated'})
        self.assertTrue(all(t['n'] == 20 and t['p_value'] < .05 for t in tests))

    def test_final_evaluation_isolated_complete_and_cannot_rerun(self):
        import contextlib
        import csv
        import io
        import json
        cfg = dict(scenarios={'pm_peak': {}, 'night': {}}, time_to_teleport=300, warmup_s=900)
        requested = {'eb': (100, False), 'wb': (100, False), 'side': (100, True)}
        stats = e.metrics(requested, {v: dict(arrival=200, timeLoss=10, departDelay=2, waitingCount=1)
                                     for v in requested}, {'eb': ('eb', 20), 'wb': ('wb', 30)}, [], 100, 200)
        def simulate(scenario, controller, seed, *_):
            return [dict(controller=controller, scenario=scenario, seed=seed, window=w, **stats)
                    for w in (('full', 'holdout') if scenario == 'pm_peak' else ('full',))]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for d in ('sim', 'reports', 'config'):
                (root/d).mkdir()
            for path in ['config/corridor.yaml', 'sim/corridor.net.xml', 'reports/optimize_v4.json',
                         'sim/routes_pm_peak.rou.xml', 'sim/routes_night.rou.xml']:
                (root/path).write_text('fixture')
            for controller in ('actuated', 'optuna_v3', 'optuna_v4', 'existing_vta'):
                for scenario in ('pm_peak', 'night'):
                    (root/f'sim/tls_{controller}_{scenario}.add.xml').write_text('frozen')
            protected = ('results.csv', 'eval.json', 'eval_v3.json')
            for path in protected:
                (root/'reports'/path).write_text('unchanged')
            with patch.object(p, 'ROOT', root), patch.object(p, 'config', return_value=cfg), \
                 patch.object(p, 'check_battery', return_value='battery 95%'), \
                 patch.object(e, 'boundaries', return_value={}), patch.object(e, 'simulate', side_effect=simulate) as run, \
                 patch.object(e, 'save_media') as media, contextlib.redirect_stdout(io.StringIO()):
                e.eval(version=4)
                self.assertEqual(run.call_count, 160)
                self.assertEqual({call.args[2] for call in run.call_args_list}, set(range(53, 73)))
                media.assert_not_called()
                with self.assertRaisesRegex(RuntimeError, 'refusing to rerun'):
                    e.eval(version=4)
            with (root/'reports/results_2024.csv').open() as stream:
                self.assertEqual(len(list(csv.DictReader(stream))), 240)
            provenance = json.loads((root/'reports/eval_v4.json').read_text())
            self.assertEqual(provenance['seeds'], list(range(53, 73)))
            self.assertTrue(all(t['p_value'] == 1 for t in provenance['tests']))
            self.assertTrue(all((root/'reports'/path).read_text() == 'unchanged' for path in protected))

    def test_cli_uses_registered_trial_count(self):
        from signal_lab.__main__ import main
        with patch('sys.argv', ['signal_lab', 'optimize', '--version', '4']), patch.object(o, 'optimize') as run:
            main()
            run.assert_called_once_with(trials=60, version=4, scenario='pm_peak')
        with self.assertRaisesRegex(ValueError, 'exactly 60'):
            o.optimize(trials=300, version=4)
