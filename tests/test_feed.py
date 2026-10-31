from collections import Counter
import csv
from datetime import datetime
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from signal_lab import demand as d, feed as f, pipeline as p


class FeedTests(unittest.TestCase):
    def test_scenarios_are_deterministic_and_labeled(self):
        source = p.ROOT/'sim/routes_pm_peak.rou.xml'
        original = ET.parse(source).getroot().findall('vehicle')
        def totals(vehicles):
            return Counter(v.find('route').get('edges').split()[0] for v in vehicles
                           if f.CHANGE_START <= float(v.get('depart')) < f.CHANGE_END)
        before = totals(original)
        with tempfile.TemporaryDirectory() as temp:
            for scenario in f.SCENARIOS:
                with self.subTest(scenario=scenario):
                    path, again = Path(temp)/'routes.xml', Path(temp)/'again.xml'
                    f.scenario_routes(scenario, path)
                    f.scenario_routes(scenario, again)
                    self.assertEqual(path.read_bytes(), again.read_bytes())
                    if scenario in ('calm', 'sensor_failure'):
                        self.assertEqual(path.read_bytes(), source.read_bytes())
                    vehicles = ET.parse(path).getroot().findall('vehicle')
                    self.assertEqual(len({v.get('id') for v in vehicles}), len(vehicles))
                    self.assertEqual([float(v.get('depart')) for v in vehicles],
                                     sorted(float(v.get('depart')) for v in vehicles))
                    after = totals(vehicles)
                    for origin, count in before.items():
                        expected = count
                        if scenario == 'drop':
                            expected -= round(count*.3)
                        elif origin == f.ENTRIES.get(scenario):
                            expected += round(count*(.4 if scenario == 'south_surge' else .3))
                        self.assertEqual(after[origin], expected)
                    outside = lambda vs: [ET.tostring(v) for v in vs
                                          if not f.CHANGE_START <= float(v.get('depart')) < f.CHANGE_END]
                    self.assertEqual(outside(vehicles), outside(original))
                    original_by_id = {v.get('id'): v for v in original}
                    for v in vehicles:
                        if v.get('id') in original_by_id:
                            self.assertEqual(ET.tostring(v), ET.tostring(original_by_id[v.get('id')]))
                        else:
                            # Clones retain a real route and departure, not an invented path.
                            self.assertTrue(any(v.get('depart') == old.get('depart') and
                                                v.find('route').attrib == old.find('route').attrib
                                                for old in original))

    def test_real_sumo_crossings_and_feed_schema(self):
        begin, end = f.CHANGE_START-300, f.CHANGE_START+1800
        pair = d.movement_map(d.network())['De Anza Blvd', 'N', 'T']
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            routes = folder/'routes.xml'
            root = ET.Element('routes')
            for i in range(3):
                v = ET.SubElement(root, 'vehicle', id=f'test{i}', depart=str(f.CHANGE_START+10+i*20))
                ET.SubElement(v, 'route', edges=' '.join(pair))
            p.xml_write(root, routes)
            detectors, ids, unmapped = f.feed_detectors(folder)
            self.assertEqual(unmapped, [])
            self.assertEqual(len(ids), 67)
            self.assertEqual(len(set(ids.values())), 17)
            p.run([p.BIN/'sumo', '-c', p.ROOT/'sim/corridor.sumocfg', '-r', routes,
                   '-a', f'{detectors},{p.ROOT}/sim/tls_optuna_v5_pm_peak.add.xml',
                   '-b', begin, '-e', end, '--seed', 0, '--no-step-log',
                   '--vehroute-output', folder/'crossings.xml', '--vehroute-output.exit-times', 'true',
                   '--tripinfo-output', folder/'trips.xml'])
            rows = f.feed_rows(folder/'counts.xml', ids, begin, end)
            # Independent SUMO route exits confirm physical traversal of the signal.
            crossings = ET.parse(folder/'crossings.xml').getroot().findall('vehicle')
            crossed = [v for v in crossings if v.find('route').get('edges').split() == list(pair)
                       and all(float(t) >= begin for t in v.find('route').get('exitTimes').split())]
            self.assertEqual(len(crossed), 3)
            self.assertEqual(sum(r['count'] for r in rows), len(crossed))
            self.assertEqual(sum(r['count'] for r in rows if (r['site'], r['approach']) == ('De Anza Blvd', 'N')), 3)
            p.write_csv(folder/'feed.csv', rows)
            with open(folder/'feed.csv', newline='') as stream:
                reader = csv.DictReader(stream)
                self.assertEqual(reader.fieldnames, ['window_end', 'site', 'approach', 'count', 'ok'])
                saved = list(reader)
            self.assertEqual(len(saved), 7*17)
            for row in saved:
                self.assertIsNotNone(datetime.fromisoformat(row['window_end']).tzinfo)
                self.assertIn(row['site'], {s['name'] for s in p.config()['signals']})
                self.assertIn(row['approach'], 'NSEW')
                self.assertGreaterEqual(int(row['count']), 0)
                self.assertEqual(row['ok'], '1')
            failed = f.feed_rows(folder/'counts.xml', ids, begin, end, sensor_failure=True)
            self.assertEqual(sum(r['ok'] == 0 for r in failed), 4)
            self.assertEqual([{**r, 'ok': 1} for r in failed], rows)
            intervals = ET.parse(folder/'counts.xml')
            intervals.getroot().remove(intervals.getroot().find('interval'))
            intervals.write(folder/'missing.xml')
            with self.assertRaisesRegex(ValueError, 'Missing detector'):
                f.feed_rows(folder/'missing.xml', ids, begin, end)
            counts = f.insertion_counts(routes, folder/'trips.xml')
            self.assertEqual(counts[pair[0]], dict(requested=3, entered_by_run_end=3, entered_during_change=3))
            trips = ET.parse(folder/'trips.xml')
            trips.getroot().remove(trips.getroot().find('tripinfo'))
            trips.write(folder/'missing_trip.xml')
            with self.assertRaisesRegex(ValueError, 'every requested vehicle'):
                f.insertion_counts(routes, folder/'missing_trip.xml')


if __name__ == '__main__':
    unittest.main()
