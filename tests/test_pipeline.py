import subprocess
import sys
import unittest


class Milestones(unittest.TestCase):
    def test_m0_verbs(self):
        for verb in ('build-net', 'build-demand', 'check-demand', 'baseline', 'optimize', 'eval', 'bench', 'dashboard'):
            result = subprocess.run([sys.executable, '-m', 'signal_lab', verb, '--help'], capture_output=True)
            self.assertEqual(result.returncode, 0, verb)

    def test_m0_benchmark_number(self):
        from signal_lab.pipeline import ROOT
        self.assertRegex((ROOT / 'reports/bench.md').read_text(), r'\d+\.\d+ wall seconds')

    def test_m1_network_loads(self):
        from signal_lab.pipeline import run, BIN, ROOT
        output = run([BIN/'sumo', '-c', ROOT/'sim/corridor.sumocfg', '-e', '1', '--no-step-log', '--duration-log.statistics'])
        self.assertIn('Simulation ended at time: 1.00', output)

    def test_m1_five_signals_and_osm_provenance(self):
        from signal_lab.pipeline import config, ROOT, sumolib, ET
        cfg = config()
        self.assertEqual(len(cfg['signals']), 5)
        self.assertEqual(len({s['sumo_tls_id'] for s in cfg['signals']}), 5)
        net = sumolib.net.readNet(str(ROOT / 'sim/corridor.net.xml'))
        for signal in cfg['signals']:
            self.assertIsNotNone(net.getTLS(signal['sumo_tls_id']))
            self.assertGreater(len(signal['osm_signal_nodes']), 0)
            x,y = net.convertLonLat2XY(signal['lon'], signal['lat'])
            self.assertLess(min(__import__('math').dist((x,y), c[0].getEdge().getToNode().getCoord()) for c in net.getTLS(signal['sumo_tls_id']).getConnections()), 65)
        self.assertGreater(len(cfg['mainline_edges']), 0)
        self.assertGreater(len(cfg['side_edges']), 0)
        self.assertGreater(cfg['bbox'][2], cfg['bbox'][0])
        self.assertGreater(cfg['bbox'][3], cfg['bbox'][1])

    def test_m1_lane_counts_three_intersections(self):
        import csv
        from signal_lab.pipeline import ROOT, config, sumolib
        net = sumolib.net.readNet(str(ROOT / 'sim/corridor.net.xml'))
        signals = {s['name']: s for s in config()['signals']}
        with open(ROOT / 'tests/fixtures/mainline_lanes.csv') as stream:
            fixture = list(csv.DictReader(stream))
        self.assertEqual(len({row['intersection'] for row in fixture}), 3)
        for row in fixture:
            tls = net.getTLS(signals[row['intersection']]['sumo_tls_id'])
            edges = {c[0].getEdge() for c in tls.getConnections() if c[0].getEdge().getID().split('#')[0] == row['osm_way_id']}
            self.assertEqual(len(edges), 1, row)
            self.assertEqual(next(iter(edges)).getLaneNumber(), int(row['lanes']), row)

    def test_m1_detector_positions_and_coverage(self):
        from signal_lab.pipeline import ROOT, config, sumolib, ET
        net = sumolib.net.readNet(str(ROOT / 'sim/corridor.net.xml'))
        detectors = ET.parse(ROOT / 'sim/detectors.add.xml').getroot()
        ids = {d.get('id'): d for d in detectors}
        self.assertEqual(len(ids), len(detectors))
        lanes = {c[0] for s in config()['signals'] for c in net.getTLS(s['sumo_tls_id']).getConnections()}
        self.assertEqual(len(detectors), 2*len(lanes))
        for lane in lanes:
            for label,distance in [('stop',1), ('upstream',40)]:
                detector = ids[f'{label}_{lane.getID()}']
                self.assertAlmostEqual(float(detector.get('pos')), max(0,lane.getLength()-distance))
                self.assertLess(float(detector.get('pos')), lane.getLength())

    def test_m1_timing_inputs(self):
        import csv
        import math
        from signal_lab.pipeline import ROOT, config
        with open(ROOT / 'data/processed/timing_inputs.csv') as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual({r['sumo_tls_id'] for r in rows}, {s['sumo_tls_id'] for s in config()['signals']})
        for row in rows:
            speed,grade,width = (float(row[k]) for k in ('speed_mph','grade','width_ft'))
            self.assertEqual(float(row['yellow_s']), max(3,math.ceil((1+1.467*speed/(20+64.4*grade))*10)/10))
            self.assertAlmostEqual(float(row['red_clear_s']), max(1,round((width+20)/(1.467*speed),1)),places=1)
            self.assertIn(float(row['min_green_s']), (5,7))
            self.assertEqual(float(row['max_green_s']), 60)
            self.assertTrue(row['basis'])
