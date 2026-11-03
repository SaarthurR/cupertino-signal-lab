"""Validation runner contract checks; these tests never launch SUMO or fetch OSM."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from tools import validate_learner as v


class ProtocolTests(unittest.TestCase):
    def test_fresh_names_only_and_disjoint_fixed_seed_cohorts(self):
        with mock.patch.object(v, 'source_hashes', return_value={'src/a.py': 'abc'}):
            protocol = v.protocol(150, inputs=False)
        self.assertEqual(set(protocol['roads']), {'validation_bubb', 'validation_stelling'})
        self.assertFalse(set(protocol['roads']) & {'homestead', 'stevens_creek', 'wolfe', 'deanza'})
        self.assertTrue(all(s['role'] == 'heldout' for s in protocol['roads'].values()))
        self.assertEqual(protocol['world_seeds'], {'validation_bubb': 31010, 'validation_stelling': 31011})
        cohorts = [protocol[key] for key in ('watch_profiles', 'watch_driver_seeds', 'test_profiles',
                                            'test_driver_seeds', 'search_seeds', 'confirm_seeds')]
        for i, cohort in enumerate(cohorts):
            self.assertEqual(len(cohort), len(set(cohort)))
            for other in cohorts[i+1:]:
                self.assertFalse(set(cohort) & set(other))
        self.assertEqual(protocol['source_sha256'], {'src/a.py': 'abc'})
        self.assertEqual(protocol['trials_per_sampler'], 150)
        self.assertEqual(protocol['rollback_criteria']['bad_min'], .8)
        self.assertEqual(protocol['rollback_criteria']['noop_max'], .2)
        self.assertEqual(len(protocol['test_profiles']), 3)
        self.assertEqual(len(protocol['test_driver_seeds']), 10)

    def test_smoke_label_and_invalid_trial_count(self):
        with mock.patch.object(v, 'source_hashes', return_value={}):
            self.assertIn('SMOKE ONLY', v.protocol(1, inputs=False)['label'])
            self.assertNotIn('SMOKE', v.protocol(150, inputs=False)['label'])
            for trials in (0, -1):
                with self.assertRaises(ValueError):
                    v.protocol(trials, inputs=False)

    def test_hashes_include_nested_source_and_runner_and_detect_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            src, runner = root/'src/learner/a.py', root/'tools/validate_learner.py'
            src.parent.mkdir(parents=True)
            runner.parent.mkdir()
            src.write_text('source')
            runner.write_text('runner')
            with mock.patch.object(v.p, 'ROOT', root), mock.patch.object(v, '__file__', str(runner)):
                hashes = v.source_hashes()
                self.assertEqual(set(hashes), {'src/learner/a.py', 'tools/validate_learner.py'})
                self.assertEqual(hashes['src/learner/a.py'], hashlib.sha256(b'source').hexdigest())
                frozen = dict(source_sha256=hashes, input_sha256={})
                v.verify_frozen(frozen)
                src.write_text('changed')
                with self.assertRaisesRegex(RuntimeError, 'Source changed'):
                    v.verify_frozen(frozen)

    def test_repeat_or_existing_fresh_inputs_refuse_before_work(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with mock.patch.object(v, 'OUT', root/'reports'), mock.patch.object(v.roads, 'ROADS', root/'roads'), \
                    mock.patch.object(v.worlds, 'WORLDS', root/'worlds'), mock.patch.object(v, 'prepare') as prepare:
                v.OUT.mkdir()
                for name in ('results.json', 'protocol.json', 'failure.json'):
                    file = v.OUT/name
                    file.write_text('{}')
                    with self.assertRaisesRegex(RuntimeError, 'refusing'):
                        v.run()
                    file.unlink()
                (v.roads.ROADS/'validation_bubb').mkdir(parents=True)
                with self.assertRaisesRegex(RuntimeError, 'Fresh road inputs'):
                    v.run()
                prepare.assert_not_called()

    def test_preparation_failure_retains_protocol_and_explicit_failure(self):
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(v, 'OUT', Path(temp)/'out'), \
                mock.patch.object(v, 'refuse_repeat'), mock.patch.object(v, 'source_hashes', return_value={}), \
                mock.patch.object(v, 'prepare', side_effect=ValueError('signals matched one TLS')):
            with self.assertRaisesRegex(ValueError, 'one TLS'):
                v.run()
            self.assertTrue((v.OUT/'protocol.json').exists())
            self.assertIn('signals matched one TLS', (v.OUT/'failure.json').read_text())
            self.assertFalse((v.OUT/'results.json').exists())

    def test_preparation_builds_only_the_two_fresh_roads(self):
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(v, 'OUT', Path(temp)), \
                mock.patch.object(v.roads, 'SPECS', {}), mock.patch.object(v.worlds, 'SEEDS', {}), \
                mock.patch.object(v.roads, 'build_road') as build_road, \
                mock.patch.object(v.worlds, 'build_world') as build_world, \
                mock.patch.object(v.road, 'load', return_value={}), \
                mock.patch.object(v.worlds, 'stale_routes', return_value={}):
            v.prepare()
            self.assertEqual([c.args[0] for c in build_road.call_args_list], list(v.SPECS))
            self.assertEqual([c.args[0] for c in build_world.call_args_list], list(v.SPECS))


class PreparationFailureTests(unittest.TestCase):
    def test_unsupported_geometry_is_retained_while_other_road_is_prepared(self):
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(v, 'OUT', Path(temp)), \
                mock.patch.object(v.roads, 'SPECS', {}), mock.patch.object(v.worlds, 'SEEDS', {}), \
                mock.patch.object(v.roads, 'build_road', side_effect=[ValueError('unsupported turn'), None]), \
                mock.patch.object(v.worlds, 'build_world'), mock.patch.object(v.road, 'load', return_value={}), \
                mock.patch.object(v.worlds, 'stale_routes', return_value={}):
            prepared, failures = v.prepare()
            self.assertEqual(prepared, ['validation_stelling'])
            self.assertIn('unsupported turn', failures['validation_bubb']['error'])
            self.assertTrue((v.OUT/'preparation_failures.json').exists())


class WiringTests(unittest.TestCase):
    def test_both_samplers_receive_the_same_copied_observations(self):
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(v, 'OUT', Path(temp)), \
                mock.patch.object(v.road, 'load', return_value={}), \
                mock.patch.object(v.road, 'file', return_value=Path('old.xml')):
            observed = v.OUT/'observed/validation_bubb'
            observed.mkdir(parents=True)
            (observed/'copy.rou.xml').write_text('same learned input')
            roots = []
            def practice(name, **kwargs):
                roots.append(v.road.OUT)
                self.assertEqual((v.road.OUT/name/'copy.rou.xml').read_text(), 'same learned input')
                return dict(quality_gate={'passed': False}, trials=0, confirm_gain=0, confirm_p=1)
            with mock.patch.object(v.practice, 'practice', side_effect=practice) as call, \
                    mock.patch.object(v.card, 'recommend', return_value={'decision': 'no change'}):
                selections, decisions = v.strategies('validation_bubb', 150)
            self.assertEqual(set(decisions), {'tpe', 'random'})
            self.assertEqual(selections, dict(tpe=Path('old.xml'), random=Path('old.xml')))
            self.assertEqual(len(set(roots)), 2)
            self.assertIsInstance(call.call_args_list[0].kwargs['sampler'], v.optuna.samplers.TPESampler)
            self.assertIsInstance(call.call_args_list[1].kwargs['sampler'], v.optuna.samplers.RandomSampler)
            self.assertTrue(all(c.kwargs['trials'] == 150 for c in call.call_args_list))

    def test_evaluator_uses_true_profile_only_outside_learner_and_pairs_rollback(self):
        def stats(value):
            return dict.fromkeys(v.METRICS, value) | {'origin_delay_s': {'north': value}}
        def check(name, path, program, seed, demand):
            self.assertIsNone(v._ACTIVE)
            self.assertEqual(demand.name, '6000.rou.xml')
            return dict(seed=seed, program=program, go_back=program == 'bad', change_s=100,
                        time_s=1000 if program == 'bad' else None,
                        held=stats(200 if program == 'bad' else 100),
                        with_rule=stats(120 if program == 'bad' else 100))
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(v, 'OUT', Path(temp)), \
                mock.patch.object(v, 'TEST_PROFILES', (6000,)), mock.patch.object(v, 'TEST_DRIVERS', (7000, 7001)), \
                mock.patch.object(v.road, 'load', return_value={'signals': [], 'mainline_edges': []}), \
                mock.patch.object(v.road, 'file', return_value=Path('old.xml')), \
                mock.patch.object(v.road, 'window', return_value=(0, 900)), \
                mock.patch.object(v.baseline, 'actuated'), mock.patch.object(v.worlds, 'bad_plan'), \
                mock.patch.object(v.worlds, 'noop_plan'), mock.patch.object(v.worlds, 'check_run', side_effect=check), \
                mock.patch.object(v.road, 'many', side_effect=lambda jobs: [(stats(100), None) for _ in jobs]) as many:
            result = v.evaluate('validation_bubb', dict(tpe=Path('old.xml'), random=Path('old.xml')))
            self.assertEqual(set(result), {'6000'})
            self.assertEqual(set(result['6000']['arms']), {'old', 'tpe', 'random', 'fresh'})
            self.assertTrue(result['6000']['rollback']['passed'])
            self.assertTrue(all(len(c.args[0]) == 2 for c in many.call_args_list))
            self.assertTrue((v.OUT/'evaluation/validation_bubb/6000/metrics.json').exists())


class SummaryTests(unittest.TestCase):
    def stats(self, value):
        return dict.fromkeys(v.METRICS, value) | {'origin_delay_s': {'north': value, 'south': value*2}}

    def test_descriptive_paired_math_and_origin_groups(self):
        rows = [dict(seed=1, arm='old', metrics=self.stats(100)), dict(seed=2, arm='old', metrics=self.stats(200)),
                dict(seed=1, arm='tpe', metrics=self.stats(90)), dict(seed=2, arm='tpe', metrics=self.stats(180))]
        summary = v.paired_summary(rows, 'tpe')
        primary = summary['all_requested_delay_s']
        self.assertEqual((primary['mean'], primary['old_mean'], primary['diff_mean']), (135, 150, -15))
        self.assertEqual(primary['per_seed_diff'], {'1': -10, '2': -20})
        self.assertEqual(summary['origin_delay_s']['south']['diff_mean'], -30)
        self.assertNotIn('p_less', primary)
        with self.assertRaisesRegex(ValueError, 'complete paired'):
            v.paired_summary(rows[:-1], 'tpe')
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            v.paired_summary(rows+[rows[0]], 'tpe')

    def test_rollback_harm_and_undo_timing_are_relative_to_paired_noop(self):
        runs = []
        for seed in range(10):
            runs.extend([dict(seed=seed, program='bad', go_back=True, change_s=100, time_s=1000,
                              held={'all_requested_delay_s': 200}, with_rule={'all_requested_delay_s': 120}),
                         dict(seed=seed, program='noop', go_back=False, change_s=100, time_s=None,
                              held={'all_requested_delay_s': 100}, with_rule={'all_requested_delay_s': 100})])
        summary = v.rollback_summary(runs)
        self.assertTrue(summary['passed'])
        self.assertEqual(summary['mean_bad_rule_vs_held_s'], -80)
        self.assertEqual(summary['mean_bad_rule_vs_noop_s'], 20)
        self.assertEqual(summary['mean_noop_rule_vs_noop_s'], 0)
        self.assertEqual(summary['paired'][0]['undo_after_change_s'], 900)
        for r in runs:
            if r['program'] == 'noop':
                r['go_back'] = True
        self.assertFalse(v.rollback_summary(runs)['passed'])

    def test_learner_output_restores_root_and_rejects_hidden_reads(self):
        prior = v.road.OUT
        with tempfile.TemporaryDirectory() as temp:
            own = Path(temp)/'own'
            own.mkdir()
            file = own/'data'
            file.write_text('visible')
            with v.learner_output(own):
                self.assertEqual(v.road.OUT, own)
                self.assertEqual(file.read_text(), 'visible')
                with self.assertRaises(PermissionError):
                    (v.worlds.WORLDS/'hidden.rou.xml').read_text()
            self.assertEqual(v.road.OUT, prior)


if __name__ == '__main__':
    unittest.main()
