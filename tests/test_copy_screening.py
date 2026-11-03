import json
import hashlib
from pathlib import Path
import tempfile
import unittest
import shutil
import subprocess
import sys
from unittest import mock

from learner import learn, practice, road
from world import worlds


class CopyScreeningTests(unittest.TestCase):
    def test_quality_rejects_missing_nonfinite_and_unacceptable_fit(self):
        good = dict(geh_under_5_share=.9, count_error_share=.1, watched_days=3,
                    occupancy_mean_abs_diff=5., shared_turn_max_share=.1)
        self.assertTrue(learn.quality_gate(good)['passed'])
        for key, value in [('geh_under_5_share', .8), ('count_error_share', .53),
                           ('occupancy_mean_abs_diff', 12.), ('shared_turn_max_share', .5),
                           ('geh_under_5_share', 1.1), ('count_error_share', float('nan'))]:
            with self.subTest(key=key, value=value):
                self.assertFalse(learn.quality_gate({**good, key: value})['passed'])
        self.assertFalse(learn.quality_gate({})['passed'])

    def test_observation_gaps_duplicates_suspect_and_mismatched_days_are_not_zero(self):
        rows = [dict(window_end=f'2026-10-31T16:{m}:00-07:00', lane='a', count='2') for m in (35, 40, 45)]
        self.assertEqual(learn.pattern([rows], lambda r: r['lane'])[(59400, 'a')][0], 6)
        for days in ([], [[]], [[rows[0], rows[2]]], [rows+[rows[0]]],
                     [rows, rows[:-1]], [[{**rows[0], 'count': 'nan'}]],
                     [[{**rows[0], 'ok': '0'}]], [[{**rows[0], 'count': '-1'}]]):
            with self.subTest(days=days), self.assertRaises(ValueError):
                learn.pattern(days, lambda r: r['lane'])

    def test_shared_lane_bounds_do_not_invent_turn_counts(self):
        cfg = road.load('homestead')
        net = road.net(cfg)
        rels = road.relations(cfg, net)
        owner = learn.exclusive_lanes(net, rels)
        lanes = {(59400, lane): (10., 0.) for lane in owner}
        bounds = learn.turn_bounds(cfg, net, lanes)
        self.assertTrue(any(r['max_count'] > r['min_count'] for r in bounds))
        for r in bounds:
            self.assertGreaterEqual(r['min_count'], 0)
            self.assertGreaterEqual(r['max_count'], r['min_count'])
            self.assertTrue(0 <= r['ambiguous_share'] <= 1)

    def test_full_coverage_requires_endpoints_and_every_expected_detector(self):
        rows = [dict(window_end=f'2026-10-31T16:{m}:00-07:00', lane=k, count='2')
                for m in (35, 40, 45) for k in ('a', 'b')]
        learn.complete_days([rows], lambda r: r['lane'], {'a', 'b'}, 59400, 60300)
        for incomplete in (rows[2:], rows[:-2], [r for r in rows if r['lane'] == 'a']):
            with self.assertRaises(ValueError):
                learn.complete_days([incomplete], lambda r: r['lane'], {'a', 'b'}, 59400, 60300)

    def test_a_candidate_must_pass_each_count_spread_stress_case(self):
        base = [dict(seed=i, teleports=0, unfinished=0, side_all_requested_delay_s=20.,
                     all_requested_delay_s=100., origin_delay_s={'a': 100.},
                     all_requested_delay_0_s=100., all_requested_delay_1800_s=100.) for i in range(10)]
        better = [{**s, 'all_requested_delay_s': 50., 'origin_delay_s': {'a': 50.},
                   'all_requested_delay_0_s': 50., 'all_requested_delay_1800_s': 50.} for s in base]
        harmed = [{**s, 'origin_delay_s': {'a': 110.}} for s in better]
        for low, expected in ((better, True), (harmed, False)):
            with tempfile.TemporaryDirectory() as temp, mock.patch.object(road, 'OUT', Path(temp)), \
                    mock.patch.object(road, 'load', return_value={}), mock.patch.object(road, 'file', return_value=Path('old')), \
                    mock.patch.object(practice, 'old_params', return_value={'cycle_s': 90.}), \
                    mock.patch.object(practice, 'plan', side_effect=lambda cfg, params, path: Path(path).write_text(json.dumps(params))), \
                    mock.patch.object(practice.optuna, 'create_study') as create, \
                    mock.patch.object(practice, 'score', side_effect=[base, base, better, base, low, base, better]):
                out = Path(temp)/'test'; out.mkdir()
                names = ['copy.rou.xml', 'copy_low.rou.xml', 'copy_high.rou.xml']
                for name in names:
                    (out/name).write_text('<routes/>')
                (out/'learn.json').write_text(json.dumps(dict(geh_under_5_share=1., count_error_share=0., watched_days=3,
                    occupancy_mean_abs_diff=0., shared_turn_max_share=0., demand_copies=names, observations_sha256={},
                    copies_sha256={name: hashlib.sha256((out/name).read_bytes()).hexdigest() for name in names})))
                create.return_value.best_trial = mock.Mock(number=1, params={'cycle_s': 100.}, value=50.)
                result = practice.practice('test')
                self.assertEqual(result['clear_gain'], expected)
                self.assertEqual(len(result['stress_copies']), 2)
                self.assertTrue((out/'plan.add.xml').exists())
                self.assertEqual((out/'rejected_candidate.add.xml').exists(), not expected)
                self.assertEqual(json.loads((out/'plan.add.xml').read_text())['cycle_s'], 100. if expected else 90.)
                if not expected:
                    self.assertEqual(json.loads((out/'rejected_candidate.add.xml').read_text())['cycle_s'], 100.)

    def test_bad_copy_prevents_any_optimization_or_simulation(self):
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(road, 'OUT', Path(temp)), \
                mock.patch.object(road, 'load', return_value={}), mock.patch.object(road, 'file', return_value=Path('old')), \
                mock.patch.object(practice, 'old_params', return_value={'cycle_s': 90.}), \
                mock.patch.object(practice, 'plan'), mock.patch.object(practice, 'score') as score, \
                mock.patch.object(practice.optuna, 'create_study') as study:
            (Path(temp)/'test').mkdir()
            result = practice.practice('test')
            self.assertFalse(result['clear_gain'])
            self.assertFalse(result['quality_gate']['passed'])
            self.assertEqual(result['trials'], 0)
            score.assert_not_called()
            study.assert_not_called()

    def test_feasibility_checks_each_origin_unfinished_and_penalty_sensitivity(self):
        base = [dict(seed=0, teleports=0, unfinished=0, side_all_requested_delay_s=20.,
                     origin_delay_s={'main': 100., 'side': 20.},
                     all_requested_delay_0_s=60., all_requested_delay_1800_s=60.)]
        self.assertTrue(practice.feasible(base, base))
        for edit in ({'origin_delay_s': {'main': 110., 'side': 10.}}, {'unfinished': 1},
                     {'all_requested_delay_1800_s': 61.}, {'all_requested_delay_0_s': 61.},
                     {'seed': 1}, {'origin_delay_s': {'main': 90.}}):
            self.assertFalse(practice.feasible([{**base[0], **edit}], base), edit)
        self.assertFalse(practice.feasible([], base))
        self.assertFalse(practice.feasible(base*2, base*2))

    def test_search_and_confirmation_seeds_are_unique_disjoint_and_valid(self):
        for search, confirm in (([0], [10, 10]), ([0, 0], [10]), ([0], [0]), ([], [10]), ([0], [-1])):
            with self.assertRaisesRegex(ValueError, 'unique, disjoint'):
                practice.practice('not-loaded', search_seeds=search, confirm_seeds=confirm)

    def test_changed_copy_files_invalidate_previous_quality_evidence(self):
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(road, 'OUT', Path(temp)), \
                mock.patch.object(road, 'load', return_value={}), mock.patch.object(road, 'file', return_value=Path('old')), \
                mock.patch.object(practice, 'old_params', return_value={'cycle_s': 90.}), \
                mock.patch.object(practice, 'plan'), mock.patch.object(practice, 'score') as score:
            out = Path(temp)/'test'; out.mkdir()
            names = ['copy.rou.xml', 'copy_low.rou.xml', 'copy_high.rou.xml']
            for name in names:
                (out/name).write_text('<routes/>')
            report = dict(geh_under_5_share=1., count_error_share=0., watched_days=3,
                          occupancy_mean_abs_diff=0., shared_turn_max_share=0., demand_copies=names,
                          observations_sha256={}, copies_sha256={name: hashlib.sha256((out/name).read_bytes()).hexdigest() for name in names})
            (out/'learn.json').write_text(json.dumps(report))
            (out/'copy.rou.xml').write_text('<routes>changed</routes>')
            result = practice.practice('test')
            self.assertFalse(result['quality_gate']['passed'])
            self.assertIn('Copy files changed', '; '.join(result['quality_gate']['reasons']))
            score.assert_not_called()

    def test_cli_rejects_missing_road_and_mutation_of_original_test_roads(self):
        for args in (['run'], ['build-world', '--road', 'wolfe'], ['build-road', '--road', 'deanza'],
                     ['watch', '--road', '../elsewhere'], ['heldout-test', '--road', 'homestead']):
            result = subprocess.run([sys.executable, '-m', 'tools.learner', *args], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2, args)
            self.assertIn('error:', result.stderr)

    def test_facts_export_handles_blocked_forecasts_and_labels_rejected_candidates(self):
        from tools import learner_story
        original = road.OUT
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ('wolfe', 'deanza', 'homestead', 'stevens_creek'):
                target = root/'learner'/name; target.mkdir(parents=True)
                for filename in ('practice.json', 'card.json', 'timing.json'):
                    if (original/name/filename).exists():
                        shutil.copyfile(original/name/filename, target/filename)
            (root/'learner/homestead/practice.json').write_text(json.dumps(dict(clear_gain=False, best_trial=0,
                confirm_old=[], confirm_seeds=[], quality_gate={'passed': False}, wall_s=0)))
            (root/'learner/homestead/card.json').write_text('{"decision":"no change"}')
            with mock.patch.object(road, 'OUT', root/'learner'), mock.patch.object(learner_story, 'OUT', root/'facts'), \
                    mock.patch.object(learner_story, 'rel', side_effect=lambda p: str(p)):
                learner_story.facts()
            facts = {(r['road'], r['name']): r['value'] for r in json.loads((root/'facts/facts.json').read_text())['facts']}
            self.assertFalse(facts['homestead', 'copy_forecast_available'])
            self.assertNotIn(('homestead', 'copy_old_delay'), facts)
            self.assertEqual(facts['deanza', 'predicted_change'], 0)
            self.assertLess(facts['deanza', 'rejected_candidate_predicted_change'], 0)

    def test_unique_trips_are_not_signal_turn_passages(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ('truth.xml', 'learner/test/copy.rou.xml'):
                p = root/name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text('<routes><vehicle id="a" depart="0"><route edges="a b c"/></vehicle>'
                             '<vehicle id="warmup" depart="-1"><route edges="a b c"/></vehicle></routes>')
            with mock.patch.object(worlds, 'TRUTH', root/'truth'), mock.patch.object(road, 'OUT', root/'learner'), \
                    mock.patch.object(road, 'load', return_value={}), mock.patch.object(road, 'window', return_value=(0, 900)), \
                    mock.patch.object(road, 'net', return_value=None), \
                    mock.patch.object(road, 'relations', return_value={'a': {'b': 's'}, 'b': {'c': 's'}}), \
                    mock.patch.object(worlds, 'routes', return_value=root/'truth.xml'):
                result = worlds.truth_fit('test')
            self.assertEqual(result['truth_unique_trips'], 1)
            self.assertEqual(result['truth_turn_passages'], 2)
            self.assertEqual(result['copy_unique_trips'], 1)
            self.assertEqual(result['copy_turn_passages'], 2)


if __name__ == '__main__':
    unittest.main()
