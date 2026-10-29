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

    def test_paths_break_at_missing_samples_and_position_jumps(self):
        track = [(63000,'eb',0),(63001,'eb',5),(63003,'eb',10),
                 (63004,'side',0),(63005,'eb',20),(63006,'eb',200),
                 (63007,'eb',205)]
        lines = d.segments(track, {'eb': 100})
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], ((0,100),(1/60,105)))

    def test_page_uses_csvs_and_only_local_assets(self):
        roads, signals, offsets, distance = d.geometry(p.config())
        self.assertGreater(distance, 1000)
        self.assertEqual(len(signals), 5)
        self.assertGreater(len(offsets), 5)
        html = d.build_page(d.read_csv(p.ROOT/'reports/results.csv'), d.read_csv(p.ROOT/'reports/wilcoxon.csv'), roads, signals)
        for text in ('+513','9.1%','+11.8%','7,980.0','7,283.2','7,796.6','696.8','183.4','0.018555','2018','Completed-only','52','61'):
            self.assertIn(text, html)
        self.assertNotIn('https://', html)
        for link in re.findall(r'(?:href|src|poster)="([^"]+)"', html):
            if link.endswith(('.csv',)):
                self.assertTrue((p.ROOT/'dashboard'/link).resolve().is_file(), link)
