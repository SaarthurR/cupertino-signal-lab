"""Printed totals and Vistro p2 are independent checks of the visual transcription."""
import csv
import unittest
from signal_lab import demand as d, pipeline as p


class VTACountTests(unittest.TestCase):
    def test_all_printed_rows_columns_and_peak_hours(self):
        with open(p.ROOT/'data/processed/vta_counts_2024.csv') as f:
            rows = list(csv.DictReader(f))
        keys = ('site_id', 'period', 'interval_start', 'category', 'approach', 'movement')
        cells = {tuple(r[k] for k in keys): int(r['value']) for r in rows}
        self.assertEqual(len(cells), len(rows))
        self.assertEqual(len(rows), 764)
        self.assertEqual({r['count_date'] for r in rows}, {'2024-10-09'})
        for site, peak, total in [('211', '17:15', 6271), ('217', '17:00', 4393)]:
            def get(period, start, category, approach, movement):
                return cells[site, period, start, category, approach, movement]
            starts = ['16:30', '16:45', '17:00', '17:15', '17:30', '17:45', '18:00', '18:15']
            peak_starts = [t for t in starts if d.seconds(peak) <= d.seconds(t) < d.seconds(peak)+3600]
            for category in ('vehicles', 'heavy', 'bicycles', 'pedestrians'):
                columns = [(a, m) for a in 'NESW' for m in ('ULTR' if category == 'vehicles' else ['total'])]
                for start in starts:
                    self.assertEqual(sum(get('interval', start, category, a, m) for a, m in columns),
                                     get('interval', start, category, 'ALL', 'total'), (site, category, start))
                for a, m in columns + [('ALL', 'total')]:
                    self.assertEqual(sum(get('interval', t, category, a, m) for t in starts),
                                     get('count_total', '', category, a, m), (site, category, a, m))
                    self.assertEqual(sum(get('interval', t, category, a, m) for t in peak_starts),
                                     get('peak_hour', peak, category, a, m), (site, category, a, m))
                if category == 'vehicles':
                    for a, m in columns:
                        self.assertEqual(get('peak_hour', peak, category, a, m), get('vistro_peak', peak, category, a, m))
                        self.assertEqual(round(100*get('peak_hv', peak, category, a, m)/get('peak_hour', peak, category, a, m)),
                                         get('peak_hv_percent', peak, category, a, m))
                    for a in 'NESW':
                        self.assertEqual(sum(get('peak_hv', peak, category, a, m) for m in 'ULTR'),
                                         get('peak_hour', peak, 'heavy', a, 'total'))
            self.assertEqual(get('peak_hour', peak, 'vehicles', 'ALL', 'total'), total)
            heavy_peak = get('peak_hour', peak, 'heavy', 'ALL', 'total')
            self.assertEqual(get('peak_hv', peak, 'vehicles', 'ALL', 'total'), heavy_peak)
            self.assertEqual(get('peak_hv_percent', peak, 'vehicles', 'ALL', 'total'), round(100*heavy_peak/total))
            for period in ('count_total', 'peak_hour', 'peak_hv', 'peak_hv_percent'):
                self.assertEqual(get(period, '' if period == 'count_total' else peak, 'vehicles', 'ALL', 'rolling_hour'), 0)
            rolling = []
            for i, start in enumerate(starts):
                expected = sum(get('interval', t, 'vehicles', 'ALL', 'total') for t in starts[i-3:i+1]) if i >= 3 else 0
                self.assertEqual(get('interval', start, 'vehicles', 'ALL', 'rolling_hour'), expected)
                rolling.append(expected)
            self.assertEqual(max(rolling), total)
            self.assertEqual(starts[rolling.index(total)-3], peak)

    def test_production_counts_and_neighbor_estimates(self):
        with open(p.ROOT/'data/processed/vta_counts_2024.csv') as f:
            raw = list(csv.DictReader(f))
        cells = {(r['intersection'], r['interval_start'], r['approach'], r['movement']): int(r['value'])
                 for r in raw if r['period'] == 'interval' and r['category'] == 'vehicles' and r['approach'] != 'ALL'}
        cfg = {s['name']: s['lon'] for s in p.config()['signals']}
        for row in d.load_counts():
            name, start, approach, movement = [row[k] for k in ('intersection', 'interval_start', 'approach', 'movement')]
            if name in ('De Anza Blvd', 'Stelling Rd'):
                self.assertEqual(int(row['vehicles']), cells[name, start, approach, movement])
                self.assertEqual(row['site_id'], '211' if name == 'De Anza Blvd' else '217')
                if movement == 'T':
                    peds = next(r['value'] for r in raw if r['intersection'] == name and r['period'] == 'interval'
                                and r['interval_start'] == start and r['category'] == 'pedestrians' and r['approach'] == approach)
                    self.assertEqual(row['peds'], peds)
            elif name in ('Bandley Dr', 'Saich Way'):
                expected = 5
                if approach in 'EW' and movement == 'T':
                    fraction = (cfg[name]-cfg['De Anza Blvd'])/(cfg['Stelling Rd']-cfg['De Anza Blvd'])
                    first, last = [cells[n, start, approach, movement] for n in ('De Anza Blvd', 'Stelling Rd')]
                    expected = round(first+(last-first)*fraction)
                self.assertEqual(int(row['vehicles']), expected)
