import re
import unittest

import numpy as np
from scipy.stats import wilcoxon
from signal_lab import dashboard as d, pipeline as p


class DashboardTests(unittest.TestCase):
    def test_exact_paired_cohort_and_uncertainty(self):
        rows = d.read_csv(p.ROOT/'reports/results.csv')
        groups = d.cohort(rows)
        self.assertEqual([int(r['seed']) for r in groups[0]], list(range(33, 53)))
        means, sds = d.stats(groups, 'completed')
        self.assertAlmostEqual(means[1]-means[0], 566.45)
        self.assertTrue(np.all(sds > 0))
        with self.assertRaises(ValueError):
            d.cohort(rows + [groups[0][0]])
        # The preregistered v3 comparison, not either earlier try, drives the page.
        tests = d.read_csv(p.ROOT/'reports/wilcoxon.csv')
        row = next(r for r in tests if r['scenario']=='pm_peak' and r['window']=='holdout' and r['seed_group']=='v3_final' and r['metric']=='mainline_travel_eb_s' and r['controller']=='optuna_v3')
        differences = [float(b['mainline_travel_eb_s'])-float(a['mainline_travel_eb_s']) for a,b in zip(*groups)]
        self.assertAlmostEqual(float(row['p_value']), wilcoxon(differences, alternative='less').pvalue)

    def test_video_captions_only_claim_what_the_timeline_shows(self):
        counters = d.timeline()
        script = d.caption_script(counters)
        self.assertGreater(len(script), 3)
        for (start, stop, line), (later, _, _) in zip(script, script[1:]):
            self.assertLess(start, stop)
            self.assertLessEqual(stop, later)  # captions never overlap on screen
        textbook, ours = counters
        shown = {int(n.replace(',', '')) for _, _, line in script
                 for n in re.findall(r'(?<![:\d])(\d[\d,]*)(?!\s*PM|:)', line)}
        real = {c[t][1] for c in counters for t in range(*d.VIDEO)}
        real |= {ours[t][2]-textbook[t][2] for t in range(*d.VIDEO)}
        real |= {textbook[t][1]-ours[t][1] for t in range(*d.VIDEO)}
        self.assertEqual(shown-real, set())

    def test_paths_break_at_missing_samples_and_position_jumps(self):
        base = d.VIDEO[0]
        step = d.STEP
        samples = [(base, 100), (base+step, 105), (base+3*step, 110),
                   (base+4*step, 120), (base+5*step, 500), (base+6*step, 505)]
        lines = d.segments(samples)
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[0], ((0, 100), (step/60, 105)))

    def test_best_so_far_only_falls_and_ignores_unfinished_trials(self):
        trials = [{'state': 'COMPLETE', 'value': '9'}, {'state': 'FAIL', 'value': '1'},
                  {'state': 'COMPLETE', 'value': '12'}, {'state': 'COMPLETE', 'value': '4'}]
        self.assertEqual(d.best_so_far(trials), [9., 9., 4.])
        curve = d.best_so_far(d.read_csv(p.ROOT/'reports/optimize_v3_trials.csv'))
        self.assertEqual(len(curve), 300)
        self.assertTrue(all(b <= a for a, b in zip(curve, curve[1:])))
        with self.assertRaises(ValueError):
            d.best_so_far([{'state': 'RUNNING', 'value': '1'}])

    def test_page_walks_the_steps_in_order_without_jargon(self):
        roads, signals, _, _ = d.geometry(p.config())
        html = d.build_page(d.read_csv(p.ROOT/'reports/results.csv'), roads, signals)
        flow, extras = html.split('<details>', 1)
        for word in ('Optuna', 'Wilcoxon', 'FCD', 'p=', '—', '–'):
            self.assertNotIn(word, flow)
        self.assertEqual([int(n) for n in re.findall(r'<span class="n">(\d)</span>', flow)], list(range(1, 8)))
        for word in ('Optuna', 'Wilcoxon', 'p='):
            self.assertIn(word, extras)

    def test_page_uses_csvs_and_only_local_assets(self):
        roads, signals, offsets, distance = d.geometry(p.config())
        self.assertGreater(distance, 1000)
        self.assertEqual(len(signals), 5)
        self.assertGreater(len(offsets), 5)
        html = d.build_page(d.read_csv(p.ROOT/'reports/results.csv'), roads, signals)
        for text in ('22.7%','16.5%','35.6%','15.0%','185 → 17','18 of the 20','7,980.0','836.77',
                     '646.74','0.000052','2018','2026-10-28','Completed-only'):
            self.assertIn(text, html)
        self.assertNotIn('https://', html)
        self.assertNotIn('137.1122804334809', html)
        self.assertNotIn('3.4873149533668006', html)
        self.assertEqual(html.count('<td>137.1</td>'), 10)
        self.assertIn('shut out of the corridor', html)
        for link in re.findall(r'(?:href|src|poster)="([^"]+)"', html):
            if link.endswith(('.csv', '.md')):
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
        for text in (f'{facts["delay_cut"]:.0f}%', f'{facts["wb_cut"]:.0f}%', f'{facts["faster"]:.0f}%',
                     f'{facts["teleports"][0]} &rarr; {facts["teleports"][1]}',
                     str(facts['close']), f'{facts["trips"]:,}'):
            self.assertIn(text, deck)
        # The limits appear once, as the closing next steps, and name the rule we broke.
        self.assertEqual(deck.count('breaking the rule we set ourselves'), 1)
        self.assertNotIn('Promising', deck)
        self.assertIn('Every direction came out ahead.', deck)
        self.assertNotIn('short of the usual target', deck)
        self.assertIn('Only 41 of 96 counted movements matched closely (GEH under 5)', deck)
        self.assertIn('96 counted movements', d.grid_svg(41, 96))

    def test_typical_driver_is_nearest_paired_median_and_rejects_broken_paths(self):
        def trip(duration):
            return [(61200+t, t, 0, 'entry' if t == 0 else 'exit')
                    for t in range(0, duration, 2)]
        textbook = {'slow': trip(50), 'median': trip(40), 'fast': trip(30),
                    'broken': trip(100), 'truncated': trip(40)}
        ours = {'slow': trip(10), 'median': trip(20), 'fast': trip(30),
                'broken': trip(10), 'truncated': trip(20)}
        textbook['broken'].pop(3)
        textbook['truncated'] = [(t, x, y, 'entry') for t, x, y, _ in trip(40)]
        chosen = d.typical_driver([textbook, ours], ('entry', 'exit'), ['entry', 'exit'])
        self.assertEqual(chosen, dict(id='median', durations=[40, 20], median_saving=20., count=3))
        self.assertEqual(d.trip_text(206), '3 min 26 s')
        with self.assertRaises(ValueError):
            d.typical_driver([{}, {}], ('entry', 'exit'), [])
