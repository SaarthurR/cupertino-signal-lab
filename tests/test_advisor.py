from contextlib import redirect_stdout
import csv
from dataclasses import replace
from datetime import datetime, timedelta
import io
import json
import os
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest

from signal_lab import advisor as a

FIXTURES = Path(__file__).with_name('fixtures')
START = datetime.fromisoformat('2026-10-31T17:00:00-07:00')


def snapshot(minute, count=200, occupancy=40):
    return [a.Row(START+timedelta(minutes=minute)-i*a.WINDOW, 'Test', leg, count, occupancy, 1)
            for i in range(3) for leg in 'NSEW']


def library():
    return dict(profiles=['pm', 'night'],
                plans={'v5_pm': {'profile': 'pm'}, 'v5_night': {'profile': 'night'}},
                features=[dict(approach=['Test', leg], profiles={'pm': [100, 20], 'night': [200, 40]},
                               scale=[100, 20]) for leg in 'NSEW'],
                margins={'pm': {'pm': 0, 'night': 0}, 'night': {'pm': 0, 'night': 0}})


class AdvisorTests(unittest.TestCase):
    def decide(self, minute, state, count=200, occupancy=40):
        rows = snapshot(minute, count, occupancy)
        return a.recommend(rows, state, START+timedelta(minutes=minute), library())

    def test_two_windows_and_fifteen_minutes_between_recommendations(self):
        first, state = self.decide(15, a.State())
        self.assertIsNone(first['plan'])
        second, state = self.decide(20, state)
        self.assertEqual(second['plan'], 'v5_night')
        self.assertIn('Test', second['reason'])
        self.assertIn('200.0 vs 100.0', second['reason'])
        for minute in (25, 30):
            held, state = self.decide(minute, state, 100, 20)
            self.assertIsNone(held['plan'])
        switched, state = self.decide(35, state, 100, 20)
        self.assertEqual(switched['plan'], 'v5_pm')
        self.assertEqual(state.last_change, START+timedelta(minutes=35))

    def test_bad_data_boundary_masks_suspect_values(self):
        rows = [replace(r, ok=0, count=999999) if r.approach == 'N' else r for r in snapshot(15)]
        good, state = a.recommend(rows, a.State(), START+3*a.WINDOW, library())
        self.assertEqual(good['bad_fraction'], .25)
        self.assertEqual(state.streak, 1)
        rows = [replace(r, ok=0) if r.approach in 'NS' else r for r in rows]
        bad, state = a.recommend(rows, a.State(candidate="v5_night", streak=1), START+3*a.WINDOW, library())
        self.assertIsNone(bad['plan'])
        self.assertIn('exceed 25%', bad['reason'])
        self.assertEqual(state.streak, 0)

    def test_stale_future_missing_and_duplicate_data(self):
        rows = snapshot(15)
        for now in (START+timedelta(minutes=20, seconds=1), START):
            result, state = a.recommend(rows, a.State(), now, library())
            self.assertIsNone(result['plan'])
            self.assertIn('stale or future', result['reason'])
        result, _ = a.recommend(rows[:-4], a.State(), START+3*a.WINDOW, library())
        self.assertIn('consecutive', result['reason'])
        result, _ = a.recommend(rows+[rows[0]], a.State(), START+3*a.WINDOW, library())
        self.assertIn('Duplicate', result['reason'])
        result, _ = a.recommend([r for r in rows if r.approach not in 'NS'], a.State(), START+3*a.WINDOW, library())
        self.assertIn('exceed 25%', result['reason'])

    def test_repeated_window_is_idempotent_and_gap_resets_streak(self):
        _, state = self.decide(15, a.State())
        repeated, state = self.decide(15, state)
        self.assertIsNone(repeated['plan'])
        self.assertEqual(state.streak, 1)
        second, _ = self.decide(20, state)
        self.assertEqual(second['plan'], 'v5_night')
        gap, state = self.decide(30, state)
        self.assertIsNone(gap['plan'])
        self.assertEqual(state.streak, 1)
        _, state = self.decide(35, state, 100, 20)
        self.assertEqual(state.streak, 0)

    def test_ties_and_exact_time_boundaries(self):
        tied, _ = self.decide(15, a.State(), 150, 30)
        self.assertEqual(tied['profile'], 'pm')
        self.assertIsNone(tied['plan'])
        fresh, state = a.recommend(snapshot(15), a.State(), START+4*a.WINDOW, library())
        self.assertEqual(state.streak, 1)
        state = a.State(candidate='v5_night', streak=1, last_window=START+2*a.WINDOW,
                        last_change=START+timedelta(seconds=1))
        held, _ = a.recommend(snapshot(15), state, START+3*a.WINDOW, library())
        self.assertIsNone(held['plan'])
        ready, _ = a.recommend(snapshot(15), replace(state, last_change=START), START+3*a.WINDOW, library())
        self.assertEqual(ready['plan'], 'v5_night')

    def test_unknown_profile_has_no_plan_and_margin_is_used(self):
        config = library()
        config['plans'].pop('v5_night')
        result, _ = a.recommend(snapshot(15), a.State(), START+3*a.WINDOW, config)
        self.assertIn('no validated plan', result['reason'])
        config = library()
        config['margins']['pm']['night'] = 8
        result, state = a.recommend(snapshot(15), a.State(), START+3*a.WINDOW, config)
        self.assertEqual(result['margin'], 8)
        self.assertEqual(state.streak, 0)

    def test_csv_schema_and_values(self):
        valid = dict(window_end=START.isoformat(), site='Test', approach='N', count='1', occupancy='2', ok='1')
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'feed.csv'
            def write(row, fields=a.FIELDS):
                with path.open('w', newline='') as stream:
                    writer = csv.DictWriter(stream, fieldnames=fields)
                    writer.writeheader()
                    if row is not None:
                        writer.writerow({k: row[k] for k in fields})
            for key, value in (('count', '-1'), ('count', '1.5'), ('occupancy', 'nan'),
                               ('occupancy', '101'), ('ok', '2'), ('approach', 'NE'),
                               ('site', ''), ('window_end', '2026-10-31T17:00:00')):
                with self.subTest(key=key, value=value):
                    write({**valid, key: value})
                    with self.assertRaises(ValueError):
                        a.read_feed(path)
            write(valid, a.FIELDS[:-1])
            with self.assertRaisesRegex(ValueError, 'columns'):
                a.read_feed(path)
            write(None)
            with self.assertRaisesRegex(ValueError, 'empty'):
                a.read_feed(path)
            write(valid, a.FIELDS[::-1])
            self.assertEqual(a.read_feed(path)[0].count, 1)
            with path.open('a') as stream:
                stream.write(','.join(valid[k] for k in a.FIELDS[::-1])+'\n')
            with self.assertRaisesRegex(ValueError, 'Duplicate'):
                a.read_feed(path)

    def test_real_seed_zero_replays_and_cli_log(self):
        config = json.loads(a.CALIBRATION.read_text())
        calm = a.read_feed(FIXTURES/'advisor_calm_seed0.csv')
        surge = a.read_feed(FIXTURES/'advisor_east_surge_seed0.csv')
        self.assertEqual(len(calm), 408)
        self.assertFalse(any(r['plan'] for r in a.replay(calm, config)))
        night = a.read_feed(FIXTURES/'advisor_night_seed0.csv')
        self.assertEqual([r['plan'] for r in a.replay(night, config) if r['plan']], ['v5_night'])
        decisions = list(a.replay(surge, config))
        detected = [r for r in decisions if r.get('profile') == 'east_surge' and r['margin'] > r['threshold']]
        self.assertTrue(detected)
        if 'east_surge' in config['plans']:
            self.assertTrue(any(r['plan'] == 'east_surge' for r in decisions))
        else:
            self.assertTrue(any('no validated plan' in r['reason'] for r in detected))
            self.assertFalse(any(r['plan'] for r in decisions))
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'city.csv'
            path.write_bytes((FIXTURES/'advisor_calm_seed0.csv').read_bytes())
            with redirect_stdout(io.StringIO()):
                a.advise(path)
            logged = [json.loads(line) for line in path.with_suffix('.advisor.jsonl').read_text().splitlines()]
            self.assertEqual(len(logged), 24)
            self.assertFalse(any(r['plan'] for r in logged))
            env = {k: v for k, v in os.environ.items() if k != 'SUMO_HOME'}
            env['PYTHONPATH'] = str(Path(a.__file__).parents[1])
            result = subprocess.run([sys.executable, '-S', '-m', 'signal_lab', 'advise', '--feed', str(path)],
                                    env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('Advisor replay log:', result.stdout)


if __name__ == '__main__':
    unittest.main()
