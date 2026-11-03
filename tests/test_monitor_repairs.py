"""Synthetic regression checks; no held-out outcomes calibrate these rules."""
from datetime import timedelta
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from learner import card, check, learn, road
from signal_lab import feed

START = 61200
KEYS = ('A', 'B')


def rows(indices=range(1, 11), occupancy=10, count=5):
    return [dict(window_end=(feed.CLOCK+timedelta(seconds=START+300*i)).isoformat(),
                 site='S', approach=key, occupancy=str(occupancy), count=str(count), ok='1')
            for i in indices for key in KEYS]


class MonitorRepairs(unittest.TestCase):
    def decide(self, after, watched=None):
        with mock.patch.object(learn, 'read', return_value=watched if watched is not None else [rows()]*3):
            return check.decide('synthetic', after, START)

    def assert_insufficient(self, decision):
        self.assertFalse(decision['go_back'])
        self.assertEqual(decision['status'], 'insufficient_data')
        self.assertTrue(decision['reason'])

    def test_gap_breaks_occupancy_streak(self):
        self.assert_insufficient(self.decide(rows([1, 2, 4, 5], occupancy=50)))
        decision = self.decide(rows([1, 2, 4, 5, 6], occupancy=50))
        self.assertEqual((decision['go_back'], decision['time_s']), (True, START+1800))

    def test_gap_discards_rolling_counts(self):
        self.assertFalse(self.decide(rows([1, 2, 3, 5, 6, 7, 8], count=0))['go_back'])
        decision = self.decide(rows([1, 2, 3, 5, 6, 7, 8, 9], count=0))
        self.assertEqual(decision['time_s'], START+2700)

    def test_bad_windows_break_both_histories(self):
        corruptions = [dict(ok='0'), dict(occupancy='nan'), dict(occupancy='inf'),
                       dict(occupancy='-1'), dict(occupancy='101'), dict(count='nan'),
                       dict(count='inf'), dict(count='1e308'), dict(count='-1'), dict(count='bad'), dict(site='unknown')]
        for corrupt in corruptions:
            with self.subTest(corrupt=corrupt):
                after = rows(range(1, 6), occupancy=50)
                after[4].update(corrupt)
                self.assert_insufficient(self.decide(after))
                after = rows(range(1, 8), count=0)
                after[4].update(corrupt)
                self.assertFalse(self.decide(after)['go_back'])

    def test_missing_duplicate_and_missing_fields_fail_closed(self):
        after = rows(range(1, 6), occupancy=50)
        cases = [after[:4]+after[5:], after+[dict(after[4])],
                 [dict(r) if i != 4 else {k: v for k, v in r.items() if k != 'count'}
                  for i, r in enumerate(after)]]
        for case in cases:
            with self.subTest(case=case[4]):
                self.assert_insufficient(self.decide(case))

    def test_invalid_timestamps_cannot_trigger_action(self):
        stamps = ['bad', '2026-10-31T17:15:01-07:00', '2026-10-31T17:15:00.000001-07:00',
                  '2026-11-01T17:15:00-07:00', '2026-10-31T17:15:00']
        for stamp in stamps:
            with self.subTest(stamp=stamp):
                after = rows(range(1, 4), occupancy=50)
                after.append(dict(after[0], window_end=stamp))
                self.assert_insufficient(self.decide(after))
        after = rows(range(1, 4), occupancy=50)
        after.append({'occupancy': 50})
        self.assert_insufficient(self.decide(after))

    def test_feed_outside_watched_window_and_empty_feed(self):
        self.assert_insufficient(self.decide(rows([11, 12, 13], occupancy=50)))
        self.assert_insufficient(self.decide([]))
        with mock.patch.object(learn, 'read', return_value=[rows()]*3):
            for change in (None, float('nan'), -1, 86400):
                self.assert_insufficient(check.decide('synthetic', rows(), change))

    def test_zero_watched_count_is_observed_data(self):
        for count in (0, 5):
            result = self.decide(rows(count=count), watched=[rows(count=0)]*3)
            self.assertFalse(result['go_back'])
            self.assertEqual(result['status'], 'within_range')
        self.assertTrue(self.decide(rows(occupancy=50, count=0), watched=[rows(count=0)]*3)['go_back'])

    def test_invalid_watched_windows_are_not_baselines(self):
        for corrupt in (dict(ok='0'), dict(occupancy='nan'), dict(count='-1'), dict(count='1e308')):
            day = rows()
            day[0].update(corrupt)
            with mock.patch.object(learn, 'read', return_value=[day]):
                base = check.expected('synthetic')
            self.assertNotIn((START+300, 'S', 'A'), base)
            self.assertNotIn((START+300, 'S', 'B'), base)
        missing = rows()[1:]
        duplicate = rows()+[rows()[0]]
        for day in (missing, duplicate):
            with mock.patch.object(learn, 'read', return_value=[day]):
                self.assertNotIn((START+300, 'S', 'B'), check.expected('synthetic'))
        self.assert_insufficient(self.decide(rows(), watched=[]))

    def test_count_variability_uses_watched_day_totals(self):
        variable = [rows(count=count) for count in (0, 5, 10)]
        self.assertFalse(self.decide(rows(count=3), watched=variable)['go_back'])
        stable = self.decide(rows(count=4.5))
        self.assertTrue(stable['go_back'])
        self.assertEqual(stable['time_s'], START+1500)
        # Opposite approach fluctuations cancel at corridor level, so a real total drop still flags.
        days = [rows() for _ in range(3)]
        for day, count in zip(days, (0, 5, 10)):
            for row in day:
                row['count'] = str(count if row['approach'] == 'A' else 10-count)
        self.assertTrue(self.decide(rows(count=4.5), watched=days)['go_back'])


class CardForecastRepairs(unittest.TestCase):
    def result(self, **changes):
        stats = [dict(seed=1, all_requested_delay_s=100, teleports=0, side_all_requested_delay_s=20),
                 dict(seed=2, all_requested_delay_s=100, teleports=0, side_all_requested_delay_s=20)]
        result = dict(clear_gain=False, best_trial=1, confirm_old=stats, confirm_new=stats,
                      confirm_diffs_s=[-10, -20], confirm_gain=.15, confirm_p=.2, confirm_seeds=[1, 2])
        return dict(result, **changes)

    def recommend(self, result):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)/'synthetic'
            out.mkdir()
            (out/'practice.json').write_text(json.dumps(result))
            (out/'pattern.csv').write_text('site,approach,mean_count\n')
            with mock.patch.object(road, 'OUT', Path(temp)), \
                    mock.patch.object(road, 'load', return_value={'signals': []}), \
                    mock.patch.object(road, 'net'), mock.patch.object(road, 'file'), \
                    mock.patch.object(card, 'settings', return_value={}):
                result = card.recommend('synthetic')
            return result, (out/'card.md').read_text(), json.loads((out/'card.json').read_text())

    def test_rejected_candidate_is_not_selected_forecast(self):
        result, markdown, saved = self.recommend(self.result())
        self.assertEqual(result, saved)
        self.assertEqual(result['decision'], 'no change')
        selected = result['expected_in_copy']
        self.assertEqual((selected['new_delay_s'], selected['change_s'], selected['change_range_s'],
                          selected['change_share'], selected['p_value']), (100, 0, [0, 0], 0, None))
        self.assertEqual(result['rejected_candidate_in_copy']['change_s'], -15)
        self.assertIn('Selected plan in the copy', markdown)
        self.assertIn('100 s -> 100 s', markdown)
        self.assertIn('Rejected candidate in the copy', markdown)
        self.assertIn('100 s -> 85 s', markdown)
        self.assertIn('can miss harmful changes or undo harmless ones', result['limits'])
        self.assertIn('not a safety mechanism or a live controller', markdown)

    def test_clear_gain_retains_selected_forecast(self):
        result, _, _ = self.recommend(self.result(clear_gain=True))
        self.assertEqual(result['expected_in_copy']['change_s'], -15)
        self.assertIsNone(result['rejected_candidate_in_copy'])

    def test_names_new_confirmation_guard_failures(self):
        old = [dict(s, unfinished=0, origin_delay_s={'N': 100, 'S': 100},
                    all_requested_delay_0_s=50, all_requested_delay_1800_s=200)
               for s in self.result()['confirm_old']]
        new = [dict(s, origin_delay_s=dict(s['origin_delay_s'])) for s in old]
        new[0].update(unfinished=1, origin_delay_s={'N': 120, 'S': 100},
                      all_requested_delay_0_s=60, all_requested_delay_1800_s=210)
        text = card.why(self.result(confirm_old=old, confirm_new=new, confirm_p=.001, confirm_feasible=False))
        self.assertIn('more unfinished trips on copy seeds 1', text)
        self.assertIn('origin-group delay over 1.05x old: N', text)
        self.assertIn('aggregate delay regresses at 0 s penalty', text)
        self.assertIn('aggregate delay regresses at 1800 s penalty', text)

    def test_names_missing_paired_seed_and_origin_evidence(self):
        old = [dict(s, origin_delay_s={'N': 100}) for s in self.result()['confirm_old']]
        new = [dict(s) for s in old]
        new[0] = dict(new[0], seed=99, origin_delay_s={})
        text = card.why(self.result(confirm_old=old, confirm_new=new, confirm_p=.001, confirm_feasible=False))
        self.assertIn('same paired copy seeds', text)
        self.assertIn('missing or inconsistent origin-group delay evidence', text)
        missing = card.why(self.result(confirm_p=.001, confirm_feasible=False))
        self.assertIn('missing or inconsistent origin-group delay evidence', missing)
        self.assertNotIn('failed the limits: .', missing)

    def test_names_failed_shared_lane_stress_copies(self):
        stress = [dict(copy='copy_low.rou.xml', gain=.01, p=.2, feasible=False, passed=False),
                  dict(copy='copy_high.rou.xml', gain=.05, p=.001, feasible=True, passed=True)]
        text = card.why(self.result(confirm_p=.001, confirm_feasible=True, stress_copies=stress))
        self.assertIn('shared-lane copy copy_low.rou.xml: gain under 2%, p not under 0.05, feasibility limits failed', text)
        self.assertNotIn('copy_high.rou.xml', text)

    def test_failed_quality_gate_has_unavailable_forecast_without_simulations(self):
        result = self.result(best_trial=0, confirm_old=[], confirm_new=[], confirm_diffs_s=[],
                             quality_gate=dict(passed=False, reasons=['copy fit unavailable']))
        chosen, markdown, _ = self.recommend(result)
        self.assertFalse(chosen['expected_in_copy']['available'])
        self.assertIsNone(chosen['expected_in_copy']['change_s'])
        self.assertIsNone(chosen['rejected_candidate_in_copy'])
        self.assertIn('copy fit unavailable', chosen['why'])
        self.assertIn('confirmation simulations were not run', markdown)

    def test_quality_gate_blocks_before_normal_gain_logic(self):
        gate = dict(passed=False, reasons=['missing fit', 'copy discrepancy'])
        result = self.result(best_trial=0, quality_gate=gate, confirm_diffs_s=[0, 0], confirm_gain=0)
        chosen, markdown, _ = self.recommend(result)
        self.assertIn('missing fit; copy discrepancy', chosen['why'])
        self.assertIn('copy quality screening failed', markdown)
        self.assertIsNone(chosen['rejected_candidate_in_copy'])
        self.assertEqual(chosen['expected_in_copy']['change_s'], 0)
        self.assertIn('quality screening failed', card.why(dict(result, clear_gain=True)))
        self.assertEqual(self.recommend(dict(result, clear_gain=True))[0]['decision'], 'no change')


if __name__ == '__main__':
    unittest.main()
