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
        self.assertEqual(d.FCD_SEED, 73)
        self.assertEqual(d.CONTROLLERS, ('actuated', 'optuna_v5'))
        text = '\n'.join(line for _, _, line in script)
        self.assertIn('932 cars waiting outside textbook, 525 with v5', text)
        self.assertIn('Eastbound 387 to 175 s; westbound 139 to 146 s (worse)', text)
        self.assertIn('1,242 of 4,016 paired trips took longer', text)
        self.assertIn("not the city's plan", text)
        self.assertIn('Some trips get worse', text)
        trips = d.read_csv(p.ROOT/'reports/trips_seed73.csv')
        race = d.typical_driver(trips)
        self.assertEqual((race['id'], race['count'], race['excluded']), ('demand_5720', 4016, 30))
        self.assertEqual(race['median_saving'], 174)
        requests = {v.get('id'): float(v.get('depart')) for v in
                    p.ET.parse(p.ROOT/'sim/routes_pm_peak.rou.xml').getroot().findall('vehicle')
                    if 61200 <= float(v.get('depart')) < 63000}
        for controller in d.CONTROLLERS:
            saved = {r['id']: float(r['requested_s']) for r in trips if r['controller'] == controller}
            self.assertEqual(saved, requests)

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

    def test_page_and_deck_use_the_v5_cohort_and_saved_facts(self):
        rows = d.read_csv(p.ROOT/'reports/results_v5.csv')
        f = d.facts(rows)
        self.assertEqual([int(r['seed']) for r in f['groups'][0]], list(range(73, 103)))
        self.assertAlmostEqual(f['delay_cut'], 40.72940163924989)
        self.assertEqual(f['unfinished'], [21847, 189])
        self.assertEqual((f['close'], len(f['checks'])), (48, 96))
        self.assertEqual((f['n_worse'], len(f['origins'])), (6, 11))
        self.assertAlmostEqual(f['night_rise'], 2.978932567381798)
        self.assertFalse(f['night_confirmed'])
        with self.assertRaises(ValueError):
            d.facts(rows + [f['groups'][0][0]])
        with self.assertRaises(ValueError):
            d.facts(d.read_csv(p.ROOT/'reports/results_2024.csv'))
        differences = [float(b[d.PRIMARY])-float(a[d.PRIMARY]) for a,b in zip(*f['groups'])]
        self.assertAlmostEqual(f['primary_p'], wilcoxon(differences, alternative='less').pvalue)
        roads, signals, _, _ = d.geometry(p.config())
        for html in (d.build_page(rows, roads, signals), d.build_deck(rows, roads, signals)):
            for shown in ('40.7%', '829 → 491', '21,847 → 189', '349 → 178', '995 → 577', '140 → 145',
                          d.RESULT_NOTE, 'rose about 3%', 'did not establish that the increase stayed within 5%',
                          'switch between them was not simulated', '+49 s', '+32 s', '+27 s', '+8 s', '+7 s', '+4 s',
                          '48 of 96', '6 of 11 groups wait longer', "city's real signal timing", 'on the street with the city',
                          'This plan is tuned for this corridor only', '2024-10-09', 'Kia Sharifi, P.E.', 'Larissa Sanderfer',
                          'IDAX', 'Bandley Dr and Saich Way', 'Mary uses 2018', 'Gap-out', 'Min green', 'Max green',
                          'Offset', 'Green split', 'Rush hours 73 to 102', '585 tries'):
                self.assertIn(shown, html)
            self.assertIn('<video controls preload="metadata"', html)
            self.assertIn('../reports/side_by_side.mp4', html)
            for stale in ('v4', 'v3', 'U-turn', 'repair', 'close copy', 'projection', 'jams', 'passed every rule',
                          'beat', 'better for everyone.', 'any intersection', 'one tested policy', '30.3%', 'time_space.png'):
                self.assertNotIn(stale, html.replace('not better for everyone', ''))
            for word in ('ensure', 'crucial', 'robust', 'leverage', 'delve', '—'):
                self.assertNotRegex(html.lower(), r'(?<![a-z])'+word+r'(?![a-z])')
            self.assertNotIn('https://', html)
            for link in re.findall(r'(?:href|src|poster)="([^"#]+)"', html):
                self.assertTrue((p.ROOT/'dashboard'/link).resolve().is_file(), link)
            order = [html.index(s) for s in ('Rush hour on Stevens Creek', 'How a traffic light works',
                                              'The data we got from VTA', 'How the tuner works', 'Results by direction',
                                              'Why the test is fair', 'What we would do next')]
            self.assertEqual(order, sorted(order))
        # The deck teaches lights before our solution; the page leads with the headline.
        self.assertLess(html.index('How a traffic light works'), html.index('829 → 491'))
        self.assertLess(html.index('829 → 491'), html.index('The data we got from VTA'))

    def test_deck_preserves_fixed_stage_and_notes_for_each_slide(self):
        rows = d.read_csv(p.ROOT/'reports/results_v5.csv')
        deck = d.build_deck(rows, *d.geometry(p.config())[:2])
        self.assertEqual(deck.count('<section class="slide">'), 14)
        self.assertEqual(deck.count('<p class="note">'), 14)
        self.assertIn('width:1920px;height:1080px', deck)
        self.assertIn("e.key === 'n'", deck)
        self.assertIn('In this fixed-demand simulation, v5 cut PM-holdout delay 40.7% against textbook, '
                      'while several origins waited longer.', deck)
        for diagram in ('The whole system', 'From count sheet to cars', 'Inside one signal',
                        'How the tuner works', 'Why the test is fair', 'Lights work as a team'):
            self.assertIn(diagram, deck)
        # Marker ids must be unique: every slide lives in one document.
        markers = re.findall(r'<marker id="([^"]+)"', deck)
        self.assertEqual(len(markers), len(set(markers)))
        self.assertIn('96 counted movements', d.grid_svg(41, 96))

    def test_tuner_slides_use_v5_search_space_and_scores(self):
        rows = d.read_csv(p.ROOT/'reports/results_v5.csv')
        f = d.facts(rows)
        trials = d.read_csv(p.ROOT/'reports/optimize_v5_trials.csv')
        self.assertEqual([count for count, _, _ in f['knobs']], [1, 5, 16, 5, 5])
        self.assertEqual(sum(count for count, _, _ in f['knobs']),
                         sum(c.startswith('params_') for c in trials[0]))
        self.assertEqual((len(f['curve']), f['pm_trials'], f['night_trials'], f['kept'], f['thrown_out']),
                         (585, 585, 200, 561, 201))
        self.assertAlmostEqual(f['try0'], float(trials[0]['value']))
        self.assertAlmostEqual(f['kept_score'], float(trials[f['kept']]['value']))
        self.assertEqual((f['train_range'], f['pick_range'], f['test_range']),
                         ('0 to 4', '5 to 12', '73 to 102'))
        deck = d.build_deck(rows, *d.geometry(p.config())[:2])
        for shown in ('457 s', '225 s', 'Try 561, the plan we kept', '32 numbers in all',
                      '201 of the 585 tries broke a rule', '5 practice', '80 to 180 s', '110 minutes on a laptop',
                      '2026-10-30', 'not a neural network', 'night search ran 200 tries'):
            self.assertIn(shown, deck)
        self.assertNotIn('3 practice', deck)

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
        for controller in ('actuated', 'optuna_v3'):
            group = [r for r in rows if r['controller'] == controller]
            requests = sorted((r['id'], float(r['requested_s']), r['entry']) for r in group)
            self.assertEqual(len(requests), 4171)
            self.assertEqual(hashlib.sha256(json.dumps(requests).encode()).hexdigest(), expected)
        race = d.typical_driver(rows, controllers=('actuated', 'optuna_v3'))
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
