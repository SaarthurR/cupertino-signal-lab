import contextlib
import csv
import io
import math
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from signal_lab import demand as d, pipeline as p


class DemandTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = d.load_counts()
        cls.net = d.network()
        cls.mapping = d.movement_map(cls.net)

    def test_complete_profiles_and_provenance(self):
        self.assertEqual(len(self.rows), 392)
        self.assertEqual(sum(r['source'] == 'measured' for r in self.rows), 256)
        counts = d.mapped_counts(self.rows, self.mapping)
        self.assertEqual(set(counts), set(range(59400, 66600, 900)))
        self.assertTrue(all(len(c) == 49 for c in counts.values()))
        self.assertEqual({r['intersection'] for r in self.rows if r['source'] == 'measured'}, {'De Anza Blvd', 'Stelling Rd'})
        with open(p.ROOT/'data/processed/tmc_sources.csv') as stream:
            sources = list(csv.DictReader(stream))
        self.assertEqual(len(sources), 5)
        self.assertTrue(all(r['method'] and r['source_url'] and r['pdf_page'] for r in sources))
        self.assertEqual({r['intersection']: r['year'] for r in sources},
                         {n: '2018' if n == 'Mary Ave' else '2024' for n in ('De Anza Blvd', 'Bandley Dr', 'Saich Way', 'Stelling Rd', 'Mary Ave')})
        self.assertEqual({r['count_date'] for r in sources if r['source'] == 'measured'}, {'2024-10-09'})
        self.assertTrue(all(r['heavy'] == '' for r in self.rows))
        self.assertTrue(all(r['peds'] == '' for r in self.rows if r['movement'] != 'T' or r['source'] == 'estimated'))

    def test_mary_hourly_measurements_are_not_measured_quarters(self):
        with open(p.ROOT/'data/processed/tmc_hourly.csv') as stream:
            hourly = list(csv.DictReader(stream))
        self.assertEqual(sum(int(r['vehicles']) for r in hourly), 3773)
        self.assertEqual(sum(int(r['vehicles']) for r in hourly if r['movement'] == 'U'), 61)
        modeled = sum(int(r['vehicles']) for r in hourly if (r['intersection'], r['approach'], r['movement']) in self.mapping)
        self.assertEqual(3773-modeled, 775)
        values = {(r['approach'], r['movement']): int(r['vehicles']) for r in hourly}
        for row in self.rows:
            if row['intersection'] == 'Mary Ave':
                self.assertEqual(row['source'], 'estimated')
                self.assertEqual(int(row['vehicles']), round(values[row['approach'], row['movement']]/4))

    def test_bad_input_rejected(self):
        original = self.rows[0]
        bad = [dict(original, vehicles='-1'), dict(original, source='current'), dict(original, approach=''),
               dict(original, movement='LT'), dict(original, interval_start='16:31')]
        for row in bad:
            with self.subTest(row=row), patch.object(d.csv, 'DictReader', return_value=[row]):
                with self.assertRaises(ValueError):
                    d.load_counts()
        with patch.object(d.csv, 'DictReader', return_value=[original, original]):
            with self.assertRaisesRegex(ValueError, 'Duplicate'):
                d.load_counts()
        with self.assertRaisesRegex(ValueError, 'no legal SUMO'):
            d.mapped_counts([dict(original, intersection='Mary Ave', approach='S')], self.mapping)

    def test_every_measured_turn_is_legal_including_stelling_rights(self):
        for a in 'NESW':
            for movement in 'LTR':
                self.assertIn(('Stelling Rd', a, movement), self.mapping)
        self.assertEqual(self.mapping['De Anza Blvd', 'N', 'T'], ('25085669#0', '157747965#0'))
        self.assertEqual(self.mapping['Stelling Rd', 'E', 'T'], ('317693332#0', '498007413#0'))
        for pair in self.mapping.values():
            outgoing = self.net.getEdge(pair[1])
            self.assertIn(outgoing, self.net.getEdge(pair[0]).getOutgoing())

    def test_candidates_cover_all_movements_and_are_connected(self):
        routes = ET.parse(p.ROOT/'data/processed/candidate_routes.rou.xml').getroot()
        # Saich's clipped north end has only an automatic U-turn incoming connection.
        self.assertIn('-714078200#1', {r.get('edges').split()[0] for r in routes})
        covered = set()
        for route in routes:
            edges = route.get('edges').split()
            reverses = []
            for first, second in zip(edges, edges[1:]):
                self.assertIn(self.net.getEdge(second), self.net.getEdge(first).getOutgoing())
                if all(c.getDirection() == 't' for c in self.net.getEdge(first).getOutgoing()[self.net.getEdge(second)]):
                    reverses.append((first, second))
                covered.add((first, second))
            counted_uturns = {pair for key, pair in self.mapping.items() if key[2] == 'U'}
            self.assertLessEqual(len(reverses), 1)
            self.assertTrue(set(reverses) <= counted_uturns)
            if not reverses:
                self.assertEqual(len(set(edges)), len(edges))
        self.assertTrue(set(self.mapping.values()) <= covered)

    def test_fit_replay_and_warmup(self):
        routes = ET.parse(p.ROOT/'sim/routes_pm_peak.rou.xml').getroot()
        buckets = [[], [], []]
        for v in routes:
            time = float(v.get('depart'))
            self.assertGreaterEqual(time, 58500)
            self.assertLess(time, 66600)
            edges = v.find('route').get('edges')
            if time < 59400:
                buckets[0].append((round(time+900, 2), edges))
            elif time < 63000:
                buckets[1].append((round(time, 2), edges))
            else:
                buckets[2].append((round(time-3600, 2), edges))
        self.assertEqual(buckets[1], buckets[2])
        self.assertEqual(buckets[0], [v for v in buckets[1] if v[0] < 60300])
        turns = ET.parse(p.ROOT/'data/processed/turns_pm_peak.xml').getroot()
        self.assertEqual([int(i.get('begin')) for i in turns], [59400, 60300, 61200, 62100])

    def test_holdout_changes_cannot_change_generated_routes(self):
        # Exercise the real count fitter twice; skip only the full simulations.
        actual_root = p.ROOT
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for path in ('config', 'sim', 'reports', 'data/processed'):
                (root/path).mkdir(parents=True, exist_ok=True)
            for path in ('config/corridor.yaml', 'sim/corridor.net.xml', 'data/processed/tmc.csv'):
                shutil.copy(actual_root/path, root/path)
            stat = dict(teleports=0, inserted=1, running=0, waiting=0, log='Full simulations tested separately')
            with patch.object(p, 'ROOT', root), patch.object(d, 'simulation', return_value=stat), contextlib.redirect_stdout(io.StringIO()):
                d.build_demand()
                original = [(root/f'sim/routes_{s}.rou.xml').read_bytes() for s in ('pm_peak', 'night')]
                changed = [dict(r, vehicles=str(int(r['vehicles'])+100000)) if r['interval_start'] >= '17:30' else r for r in self.rows]
                p.write_csv('data/processed/tmc.csv', changed)
                d.build_demand()
                self.assertEqual(original, [(root/f'sim/routes_{s}.rou.xml').read_bytes() for s in ('pm_peak', 'night')])

    def test_m2_both_scenarios_finish_night_without_teleports(self):
        with tempfile.TemporaryDirectory() as temp:
            for scenario in ('pm_peak', 'night'):
                stat = d.simulation(scenario, Path(temp)/scenario)
                self.assertIn('Simulation ended at time:', stat['log'])
                self.assertGreater(stat['inserted'], 0)
                if scenario == 'night':
                    self.assertEqual((stat['teleports'], stat['running'], stat['waiting']), (0, 0, 0))

    def test_summary_counters_are_cumulative(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'summary.xml'
            path.write_text('<summary>'+''.join(f'<step teleports="{v}" inserted="10" running="2" waiting="1"/>' for v in [0, 1, 1, 2])+'</summary>')
            self.assertEqual(d.summary_stats(path)['teleports'], 2)

    def test_geh_uses_hourly_flows(self):
        self.assertEqual(d.geh(0, 0), 0)
        self.assertAlmostEqual(d.geh(100, 125), math.sqrt(2*100**2/900))
        self.assertAlmostEqual(d.geh(0, 1), math.sqrt(8))
        for args in [(-1, 0), (0, -1), (1, 1, 0)]:
            with self.assertRaises(ValueError):
                d.geh(*args)

    def test_symmetric_fit_does_not_sacrifice_turn_to_inconsistent_ceiling(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            candidates, turns, output = [root/name for name in ('routes.xml', 'turns.xml', 'out.xml')]
            candidates.write_text('<routes><route edges="a b c"/><route edges="a d c"/></routes>')
            # Both routes pass c, but different observed turns can demand more than its ceiling.
            d.turn_file({0: {('a', 'b'): 20, ('a', 'd'): 10, ('b', 'c'): 5}}, turns)
            d.sample(candidates, turns, output)
            routes = [v.find('route').get('edges') for v in ET.parse(output).getroot()]
            self.assertGreater(routes.count('a b c'), 5)
            self.assertGreater(routes.count('a d c'), 0)

    def test_counted_uturns_preserve_source_and_are_separate(self):
        rows = [r for r in self.rows if r['movement'] == 'U' and r['interval_start'] < '17:30']
        self.assertEqual(sum(int(r['vehicles']) for r in rows), 272)
        self.assertEqual({r['source'] for r in rows}, {'measured'})
        self.assertEqual(len({self.mapping[r['intersection'], r['approach'], 'U'] for r in rows}), 8)

    def test_deanza_lefts_wait_before_conflicting_internal_paths(self):
        root = ET.parse(p.ROOT/'sim/corridor.net.xml').getroot()
        lefts = {pair for key, pair in self.mapping.items() if key[0] == 'De Anza Blvd' and key[2] == 'L'}
        for connection in root.findall('connection'):
            if (connection.get('from'), connection.get('to')) in lefts:
                self.assertEqual(float(connection.get('contPos')), 0)
                via = connection.get('via').rsplit('_', 1)[0]
                continuation = [c for c in root.findall('connection') if c.get('from') == via]
                self.assertTrue(continuation)
                self.assertTrue(all(c.get('via') is None for c in continuation))

    def test_detector_binning_and_front_entries(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'counts.xml'
            path.write_text('<detector>'+''.join(f'<interval id="a" begin="{t}" nVehEntered="{v}" nVehContrib="999"/>' for t,v in [(62100, 9), (63000, 2), (63900, 3), (66600, 8)])+'</detector>')
            counts = d.detector_counts(path, {'a': ('in', 'out')}, 63000, 66600)
            self.assertEqual(dict(counts), {(63000, 'in', 'out'): 2, (63900, 'in', 'out'): 3})

    def test_physical_turn_detectors_count_three_real_vehicles(self):
        pair = self.mapping['De Anza Blvd', 'N', 'T']
        candidates = ET.parse(p.ROOT/'data/processed/candidate_routes.rou.xml').getroot()
        route = min((r.get('edges').split() for r in candidates if pair in list(zip(r.get('edges').split(), r.get('edges').split()[1:]))), key=len)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'three.rou.xml'
            path.write_text('<routes>'+''.join(f'<vehicle id="test{i}" depart="{82810+20*i}"><route edges="{" ".join(route)}"/></vehicle>' for i in range(3))+'</routes>')
            detectors, ids = d.turn_detectors(self.net, {('De Anza Blvd', 'N', 'T'): pair}, temp)
            stat = d.simulation('night', temp, routes=path, additional=detectors)
            counts = d.detector_counts(Path(temp)/'turn_counts.xml', ids, 82800, 86400)
            self.assertEqual(sum(counts.values()), 3)
            self.assertEqual(stat['teleports'], 0)

    def test_missing_turns_and_uturns_have_physical_detector_crossings(self):
        keys = [('De Anza Blvd', 'W', 'L'), ('Stelling Rd', 'E', 'L'), ('Stelling Rd', 'E', 'R')]
        keys += [k for k in self.mapping if k[2] == 'U']
        selected = {k: self.mapping[k] for k in keys}
        with tempfile.TemporaryDirectory() as temp:
            root = ET.Element('routes')
            for i, pair in enumerate(selected.values()):
                for j in range(3):
                    v = ET.SubElement(root, 'vehicle', id=f'turn_{i}_{j}', depart=str(82810+i*30+j*5), departLane='best')
                    ET.SubElement(v, 'route', edges=' '.join(pair))
            path = Path(temp)/'turns.rou.xml'
            p.xml_write(root, path)
            detectors, ids = d.turn_detectors(self.net, selected, temp)
            stat = d.simulation('night', temp, routes=path, additional=detectors)
            counts = d.detector_counts(Path(temp)/'turn_counts.xml', ids, 82800, 86400)
            for pair in selected.values():
                self.assertEqual(sum(v for (_, a, b), v in counts.items() if (a, b) == pair), 3, pair)
            self.assertEqual(stat['teleports'], 0)

    def test_m3_reports_only_measured_holdout_with_honest_percentage(self):
        with open(p.ROOT/'reports/demand_check.csv') as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 128)
        self.assertEqual({r['interval'] for r in rows}, {'17:30', '17:45', '18:00', '18:15'})
        self.assertTrue(all(r['movement'].split(' / ')[0] in ('De Anza Blvd', 'Stelling Rd') for r in rows))
        for row in rows:
            self.assertAlmostEqual(float(row['geh']), d.geh(int(row['observed']), int(row['simulated'])), places=4)
        percentage = 100*sum(float(r['geh']) < 5 for r in rows)/len(rows)
        self.assertIn(f'{percentage:.2f}%', (p.ROOT/'reports/demand_check.md').read_text())
        self.assertIn('textbook coordinated-actuated baseline', (p.ROOT/'reports/demand_check.md').read_text())


if __name__ == '__main__':
    unittest.main()
