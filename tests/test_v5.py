import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import xml.etree.ElementTree as ET

from signal_lab import evaluate as e, optimize as o, pipeline as p


def finalist(trial, train, selection, worst, feasible=True):
    return dict(trial=trial, train_primary_s=train, selection_primary_s=selection,
                worst_origin_change_s=worst, feasible=feasible)


class V5Tests(unittest.TestCase):
    def test_tiebreak_band_and_v4_fallback(self):
        pool = [finalist(0, 500, 500, 0), finalist(2, 300, 300, 80), finalist(7, 290, 290, 120),
                finalist(8, 310, 292, 40), finalist(9, 100, 100, 0, feasible=False)]
        self.assertEqual(o.select_v5(pool)[0]['trial'], 8)
        self.assertEqual(o.select_v5(pool, 2), (pool[1], 'v4_fallback'))
        self.assertEqual(o.select_v5(pool[:3], 2), (pool[2], 'lowest'))
        self.assertEqual(o.select_v5([pool[0]], 2), (pool[0], 'lowest'))

    def test_origin_delay_matches_primary_numerator(self):
        origins = {'a': (0, 'x'), 'b': (0, 'x'), 'c': (0, 'y'), 'late': (99, 'y')}
        trips = {'a': dict(arrival=5, timeLoss=10, departDelay=2), 'b': dict(arrival=-1, timeLoss=0, departDelay=0)}
        self.assertEqual(e.origin_delays(origins, trips, ['a', 'a'], 0, 10), {'x': (12+1800+900)/2, 'y': 900})
        stats = [dict(origin_delay_s={'x': 10, 'y': 5}), dict(origin_delay_s={'x': 30})]
        self.assertEqual(o.worst_origin_change(stats, [dict(origin_delay_s={'x': 15, 'y': 7})]), 5)

    def test_night_space_reproduces_night_textbook(self):
        self.assertEqual(o.bounds('cycle_s', 5, 'night'), (66.9, 180))
        self.assertEqual(o.bounds('cycle_s', 5), (80, 180))
        params = o.baseline_params('night')
        textbook = ET.parse(p.ROOT/'sim/tls_actuated_night.add.xml').getroot().findall('tlLogic')
        with tempfile.TemporaryDirectory() as folder:
            o.plan('night', params, Path(folder)/'plan.xml', 5)
            planned = ET.parse(Path(folder)/'plan.xml').getroot().findall('tlLogic')
        for ours, theirs in zip(planned, textbook):
            self.assertEqual(ours.get('programID'), 'optuna_v5')
            self.assertEqual([float(x.get('maxDur')) for x in ours.findall('phase') if x.get('minDur')],
                             [float(x.get('maxDur')) for x in theirs.findall('phase') if x.get('minDur')])
        with self.assertRaises(ValueError):
            o.plan('pm_peak', dict(o.baseline_params(), cycle_s=70), Path(folder)/'x.xml', 5)

    def test_v5_cli_and_trial_guard(self):
        from signal_lab import __main__ as main
        for scenario, trials in o.V5_TRIALS.items():
            with patch('sys.argv', ['signal_lab', 'optimize', '--version', '5', '--scenario', scenario]), \
                 patch.object(o, 'optimize') as run:
                main.main()
                run.assert_called_once_with(trials=trials, version=5, scenario=scenario)
            with self.assertRaisesRegex(ValueError, 'preregistration'):
                o.optimize(trials=trials+1, version=5, scenario=scenario)
