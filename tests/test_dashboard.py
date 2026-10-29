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

    def test_deck_is_eleven_offline_slides_with_a_spoken_note_each(self):
        roads, signals, _, _ = d.geometry(p.config())
        rows = d.read_csv(p.ROOT/'reports/results.csv')
        deck = d.build_deck(rows, roads, signals)
        self.assertEqual(deck.count('<section class="slide">'), 11)
        self.assertEqual(deck.count('<p class="note">'), 11)
        self.assertNotIn('https://', deck)
        for link in re.findall(r'(?:href|src|poster)="([^"]+)"', deck):
            self.assertTrue((p.ROOT/'dashboard'/link).resolve().is_file(), link)
        facts = d.facts(rows)
        for text in (f'{facts["delay_cut"]:.1f}%', f'{facts["wb_cut"]:.1f}%', f'{facts["faster"]:.1f}%',
                     f'{facts["teleports"][0]} &rarr; {facts["teleports"][1]}',
                     str(facts['close']), f'{facts["trips"]:,}'):
            self.assertIn(text, deck)
        # The closing limit and spoken note name the rule we broke.
        self.assertEqual(deck.count('That broke a rule we set before testing, so finding out why comes first.'), 2)
        self.assertIn('In 1 of the 20 test rush hours our plan left 15 cars stuck where the textbook plan left 0.', deck)
        self.assertNotIn('We cannot declare an overall feasible winner.', deck)
        self.assertNotIn('Promising', deck)
        self.assertIn('Every direction improved on average.', deck)
        self.assertNotIn('short of the usual target', deck)
        self.assertIn('Only 41 of 96 counted movements matched closely (GEH under 5)', deck)
        self.assertIn('96 counted movements', d.grid_svg(41, 96))

    def test_tuner_slides_quote_the_search_space_and_the_two_real_scores(self):
        """The knob list and both scores must come out of the optimizer's own record."""
        rows = d.read_csv(p.ROOT/'reports/results.csv')
        f = d.facts(rows)
        trials = d.read_csv(p.ROOT/'reports/optimize_v3_trials.csv')
        self.assertEqual([count for count, _, _ in f['knobs']], [1, 5, 16, 5, 5])
        self.assertEqual(sum(count for count, _, _ in f['knobs']),
                         sum(c.startswith('params_') for c in trials[0]))
        # Trial 0 is the textbook plan the optimizer enqueued, so its score is textbook's.
        from signal_lab.optimize import baseline_params
        for key, value in baseline_params().items():
            self.assertAlmostEqual(float(trials[0]['params_'+key]), value)
        self.assertAlmostEqual(f['try0'], 396.4492997493734)
        self.assertEqual(f['kept'], 224)
        self.assertAlmostEqual(f['kept_score'], 269.85603007518796)
        # The kept plan won a run-off on fresh seeds; it is not the lowest point on the curve.
        self.assertLess(min(f['curve']), f['kept_score'])
        deck = d.build_deck(rows, *d.geometry(p.config())[:2])
        for shown in ('396 s', '270 s', 'Try 224, the plan we kept', '32 numbers in all',
                      '181 of the 300 tries broke a rule', 'best on practice'):
            self.assertIn(shown, deck)
        self.assertNotIn('neural network', d.build_page(rows, *d.geometry(p.config())[:2]))
        self.assertIn('not a neural network', deck)

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

    def test_recorded_race_pool_matches_every_route_request(self):
        import xml.etree.ElementTree as ET
        rows = d.read_csv(p.ROOT/'reports/trips_seed33.csv')
        vehicles = {v.get('id'): v for v in ET.parse(p.ROOT/'sim/routes_pm_peak.rou.xml').getroot().findall('vehicle')
                    if 61200 <= float(v.get('depart')) < 63000}
        for controller in d.CONTROLLERS:
            group = [r for r in rows if r['controller'] == controller]
            self.assertEqual(len(group), len(vehicles))
            self.assertEqual({r['id'] for r in group}, vehicles.keys())
            for row in group:
                self.assertEqual(float(row['requested_s']), float(vehicles[row['id']].get('depart')))
                self.assertEqual(row['entry'], vehicles[row['id']].find('route').get('edges').split()[0])
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
