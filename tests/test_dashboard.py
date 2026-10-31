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
        self.assertIn('Red = cars stopped on the road.', script[1][2])
        self.assertIn('line outside and trips finished', script[1][2])
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

    def test_page_and_deck_use_the_2024_cohort_and_saved_facts(self):
        rows = d.read_csv(p.ROOT/'reports/results_2024.csv')
        f = d.facts(rows)
        self.assertEqual([int(r['seed']) for r in f['groups'][0]], list(range(53, 73)))
        self.assertAlmostEqual(f['delay_cut'], 30.280939443593336)
        self.assertEqual(f['unfinished'], [14344, 703])
        self.assertEqual(f['teleports'], [3, 0])
        self.assertEqual((f['close'], len(f['checks']), f['old_close']), (48, 96, 41))
        self.assertEqual(f['rings'], [203, 170])
        self.assertEqual(f['missing_turns'], 3)
        with self.assertRaises(ValueError):
            d.facts(rows + [f['groups'][0][0]])
        with self.assertRaises(ValueError):
            d.facts(d.read_csv(p.ROOT/'reports/results.csv'))
        differences = [float(b[d.PRIMARY])-float(a[d.PRIMARY]) for a,b in zip(*f['groups'])]
        self.assertAlmostEqual(f['primary_p'], wilcoxon(differences, alternative='less').pvalue)
        roads, signals, _, _ = d.geometry(p.config())
        for html in (d.build_page(rows, roads, signals), d.build_deck(rows, roads, signals)):
            for shown in ('30.3%', '14,344 → 703', '3 → 0', '351 → 173', '985 → 705',
                          '139 → 142', '48 of 96', 'up from 41', '19.0 to 20.3 s',
                          '+104 s', '203/170 s', '117.9 s', '167 s', '730 s',
                          '2024-10-09', 'Kia Sharifi, P.E.', 'Larissa Sanderfer',
                          'IDAX', 'U-turn', 'Bandley Dr and Saich Way', 'Mary uses 2018',
                          'not a field result', 'weak baseline', 'night plan is untested',
                          'projection, not a claim about the street', 'waiting spots'):
                self.assertIn(shown, html)
            for stale in ('22.7%', '23%', 'Every direction improved', 'side_by_side', 'time_space.png'):
                self.assertNotIn(stale, html)
            for word in ('ensure', 'crucial', 'robust', 'leverage', 'delve', '—'):
                self.assertNotRegex(html.lower(), r'(?<![a-z])'+word+r'(?![a-z])')
            self.assertNotIn('https://', html)
            for link in re.findall(r'(?:href|src|poster)="([^"#]+)"', html):
                self.assertTrue((p.ROOT/'dashboard'/link).resolve().is_file(), link)
            # The gain leads; all limitations share the final next-steps section.
            self.assertLess(html.index('30.3%'), html.index('We asked VTA'))
            self.assertLess(html.index('What we would do next'), html.index('48 of 96'))

    def test_deck_preserves_fixed_stage_and_notes_for_each_slide(self):
        rows = d.read_csv(p.ROOT/'reports/results_2024.csv')
        deck = d.build_deck(rows, *d.geometry(p.config())[:2])
        self.assertEqual(deck.count('<section class="slide">'), 14)
        self.assertEqual(deck.count('<p class="note">'), 14)
        self.assertIn('width:1920px;height:1080px', deck)
        self.assertIn("e.key === 'n'", deck)
        self.assertIn('96 counted movements', d.grid_svg(41, 96))

    def test_tuner_slides_use_v4_search_space_and_scores(self):
        rows = d.read_csv(p.ROOT/'reports/results_2024.csv')
        f = d.facts(rows)
        trials = d.read_csv(p.ROOT/'reports/optimize_v4_trials.csv')
        self.assertEqual([count for count, _, _ in f['knobs']], [1, 5, 16, 5, 5])
        self.assertEqual(sum(count for count, _, _ in f['knobs']),
                         sum(c.startswith('params_') for c in trials[0]))
        self.assertEqual((len(f['curve']), f['kept'], f['thrown_out']), (60, 39, 24))
        self.assertAlmostEqual(f['try0'], float(trials[0]['value']))
        self.assertAlmostEqual(f['kept_score'], float(trials[f['kept']]['value']))
        self.assertEqual((f['train_range'], f['pick_range'], f['test_range']),
                         ('0 to 2', '5 to 12', '53 to 72'))
        self.assertLess(min(f['curve']), f['kept_score'])
        deck = d.build_deck(rows, *d.geometry(p.config())[:2])
        for shown in ('466 s', '287 s', 'Try 39, the plan we kept', '32 numbers in all',
                      '24 of the 60 tries broke a rule', '3 practice', '80 to 180 s',
                      '2026-10-30', 'best on practice', 'not a neural network'):
            self.assertIn(shown, deck)
        self.assertNotIn('5 practice', deck)

    def test_dashboard_skip_video_builds_html_without_calling_media(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from signal_lab import __main__ as cli
        with patch('sys.argv', ['signal_lab', 'dashboard', '--skip-video']), \
             patch.object(p, 'dashboard') as build:
            cli.main()
            build.assert_called_once_with(skip_video=True)
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(p, 'ROOT', Path(temp)), patch.object(d.os, 'nice'), \
             patch.object(p, 'config', return_value={}), patch.object(d, 'geometry', return_value=([], [], {}, 0)), \
             patch.object(d, 'read_csv', return_value=[]), patch.object(d, 'build_page', return_value='page'), \
             patch.object(d, 'build_deck', return_value='deck'), patch.object(d, 'render_media') as media:
            d.dashboard(skip_video=True)
            media.assert_not_called()
            self.assertEqual((Path(temp)/'dashboard/deck.html').read_text(), 'deck')

    def test_driver_selection_uses_all_entries_waits_and_counts_unfinished(self):
        rows = []
        for vid, request, departures, arrivals, entry in (
                ('a', 62900, (63200, 63000), (63240, 63040), 'west'),
                ('b', 61300, (61500, 61400), (61540, 61460), 'side'),
                ('c', 61300, (61400, 61400), (61440, 61420), 'east'),
                ('unfinished', 61300, (-1, 61400), (-1, 61420), 'other'),
                ('truncated', 61300, (61400, 61400), (66600, 61420), 'other'),
                ('early', 61190, (61210, 61210), (61250, 61230), 'east')):
            rows.extend(dict(id=vid, requested_s=str(request), depart_s=str(depart),
                             arrival_s=str(arrive), entry=entry, controller=controller)
                        for controller, depart, arrive in zip(d.CONTROLLERS, departures, arrivals))
        chosen = d.typical_driver(rows)
        self.assertEqual(chosen['id'], 'b')
        self.assertEqual(chosen['entry'], 'side')
        self.assertEqual(chosen['durations'], [240, 160])
        self.assertEqual(chosen['waits'], [200, 100])
        self.assertEqual(chosen['drives'], [40, 60])
        self.assertEqual((chosen['median_saving'], chosen['count'], chosen['excluded']), (80, 3, 2))
        self.assertEqual(chosen['requested_count'], 5)
        with self.assertRaises(ValueError):
            d.typical_driver(rows[1:])
        with self.assertRaises(ValueError):
            d.typical_driver([])
        self.assertEqual(d.trip_text(206), '3 min 26 s')

    def test_recorded_2018_race_pool_matches_archived_requests(self):
        import hashlib
        import json
        rows = d.read_csv(p.ROOT/'reports/trips_seed33.csv')
        # Request metadata from the 2018 routes at 9290ecc, before the 2024 demand replacement.
        expected = 'd243bfdf01e8a4c2a892c71efaafa7c6221f0d7c2b18abb6d9a515589b9c1b1b'
        for controller in d.CONTROLLERS:
            group = [r for r in rows if r['controller'] == controller]
            requests = sorted((r['id'], float(r['requested_s']), r['entry']) for r in group)
            self.assertEqual(len(requests), 4171)
            self.assertEqual(hashlib.sha256(json.dumps(requests).encode()).hexdigest(), expected)
        race = d.typical_driver(rows)
        self.assertEqual((race['id'], race['count'], race['excluded']), ('demand_7759', 4171, 0))
        self.assertEqual(race['median_saving'], 62)
        for total, wait, drive in zip(race['durations'], race['waits'], race['drives']):
            self.assertAlmostEqual(total, wait+drive)

    def test_result_plot_has_a_numeric_seconds_scale(self):
        groups = d.cohort(d.read_csv(p.ROOT/'reports/results.csv'))
        chart = d.paired_svg(groups, d.PRIMARY, 'Time lost per requested car')
        values = [float(row[d.PRIMARY]) for group in groups for row in group]
        self.assertIn(f'{min(values)//100*100:.0f} s', chart)
        self.assertIn(f'{(max(values)//100+1)*100:.0f} s', chart)
