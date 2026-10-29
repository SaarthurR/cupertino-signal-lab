import re
import unittest

import numpy as np
from scipy.stats import wilcoxon
from signal_lab import dashboard as d, pipeline as p


class DashboardTests(unittest.TestCase):
    def test_exact_paired_cohort_and_uncertainty(self):
        rows = d.read_csv(p.ROOT/'reports/results.csv')
        groups = d.cohort(rows)
        self.assertEqual([int(r['seed']) for r in groups[0]], list(range(3, 13)))
        means, sds = d.stats(groups, 'completed')
        self.assertAlmostEqual(means[1]-means[0], 513.4)
        self.assertTrue(np.all(sds > 0))
        with self.assertRaises(ValueError):
            d.cohort(rows + [groups[0][0]])
        tests = d.read_csv(p.ROOT/'reports/wilcoxon.csv')
        row = next(r for r in tests if r['scenario']=='pm_peak' and r['window']=='holdout' and r['seed_group']=='out_of_sample' and r['metric']=='mainline_travel_eb_s')
        differences = [float(b['mainline_travel_eb_s'])-float(a['mainline_travel_eb_s']) for a,b in zip(*groups)]
        self.assertAlmostEqual(float(row['p_value']), wilcoxon(differences, alternative='less').pvalue)

    def test_counts_distinguish_insertion_arrival_and_teleport_gap(self):
        cars = np.array([[0, 0, 0], [1, 1, .1]])
        due = {'old': 0, 'blocked': 5, 'future': 11, 'arrived': 1, 'gap': 2}
        inserted = {'old': 0, 'arrived': 2, 'gap': 3, 'blocked': 11}
        self.assertEqual(d.traffic_counts(10, cars, due, inserted, [9, 11]), (1, 1, 1))
        self.assertEqual(d.traffic_counts(11, cars, due, inserted, [9, 11]), (1, 1, 2))

    def test_paths_break_at_missing_samples_and_position_jumps(self):
        track = [(63000,'eb',0),(63001,'eb',5),(63003,'eb',10),
                 (63004,'side',0),(63005,'eb',20),(63006,'eb',200),
                 (63007,'eb',205)]
        lines = d.segments(track, {'eb': 100})
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], ((0,100),(1/60,105)))

    def test_best_so_far_only_falls_and_ignores_unfinished_trials(self):
        trials = [{'state': 'COMPLETE', 'value': '9'}, {'state': 'FAIL', 'value': '1'},
                  {'state': 'COMPLETE', 'value': '12'}, {'state': 'COMPLETE', 'value': '4'}]
        self.assertEqual(d.best_so_far(trials), [9., 9., 4.])
        curve = d.best_so_far(d.read_csv(p.ROOT/'reports/optimize_trials.csv'))
        self.assertEqual(len(curve), 200)
        self.assertTrue(all(b <= a for a, b in zip(curve, curve[1:])))
        with self.assertRaises(ValueError):
            d.best_so_far([{'state': 'RUNNING', 'value': '1'}])

    def test_page_walks_the_steps_in_order_without_jargon(self):
        roads, signals, _, _ = d.geometry(p.config())
        html = d.build_page(d.read_csv(p.ROOT/'reports/results.csv'), d.read_csv(p.ROOT/'reports/wilcoxon.csv'), roads, signals)
        flow, extras = html.split('<details>', 1)
        for word in ('Optuna', 'Wilcoxon', 'GEH', 'FCD', 'p=', '—', '–'):
            self.assertNotIn(word, flow)
        self.assertEqual([int(n) for n in re.findall(r'<span class="n">(\d)</span>', flow)], list(range(1, 7)))
        for word in ('Optuna', 'Wilcoxon', 'p='):
            self.assertIn(word, extras)

    def test_page_uses_csvs_and_only_local_assets(self):
        roads, signals, offsets, distance = d.geometry(p.config())
        self.assertGreater(distance, 1000)
        self.assertEqual(len(signals), 5)
        self.assertGreater(len(offsets), 5)
        html = d.build_page(d.read_csv(p.ROOT/'reports/results.csv'), d.read_csv(p.ROOT/'reports/wilcoxon.csv'), roads, signals)
        for text in ('+513','9.1%','+11.8%','7,980.0','7,283.2','7,796.6','696.8','183.4','0.018555','2018','Completed-only','52','61'):
            self.assertIn(text, html)
        self.assertNotIn('https://', html)
        self.assertNotIn('136.699633', html)
        self.assertNotIn('2.469368', html)
        self.assertEqual(html.count('<td>136.7</td>'), 10)
        self.assertIn('blocked', html.lower())
        for link in re.findall(r'(?:href|src|poster)="([^"]+)"', html):
            if link.endswith(('.csv',)):
                self.assertTrue((p.ROOT/'dashboard'/link).resolve().is_file(), link)

    def test_deck_is_nine_offline_slides_with_a_spoken_note_each(self):
        roads, signals, _, _ = d.geometry(p.config())
        rows = d.read_csv(p.ROOT/'reports/results.csv')
        deck = d.build_deck(rows, roads, signals)
        self.assertEqual(deck.count('<section class="slide">'), 9)
        self.assertEqual(deck.count('<p class="note">'), 9)
        self.assertNotIn('https://', deck)
        for link in re.findall(r'(?:href|src|poster)="([^"]+)"', deck):
            self.assertTrue((p.ROOT/'dashboard'/link).resolve().is_file(), link)
        facts = d.facts(rows)
        for text in (f'+{facts["extra"]:,.0f}', f'{facts["faster"]:.1f}%', str(facts['close']), f'{facts["trips"]:,}'):
            self.assertIn(text, deck)
