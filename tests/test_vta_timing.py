"""Fast file/logic checks only: these tests must never launch SUMO."""
import contextlib
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from signal_lab import pipeline as p
from signal_lab.demand import movement_map, network
from signal_lab.vta_timing import LABEL, existing_vta, source_issues, timing_rows
from signal_lab.vta_compare import movement_delays
from signal_lab import vta_compare as comparison


class VtaTimingTests(unittest.TestCase):
    def test_independently_read_timing_inputs(self):
        # All nonzero SG columns read from rendered Vistro p3, direction order from p1.
        expected = {
            '211': [(3,32,8,3.5,1.5,0,0,4), (8,67,8,4.3,1.5,5,31,6),
                    (7,40,8,3.5,1,0,0,4), (4,75,8,4.3,1.5,5,37,6),
                    (5,23,8,3.5,1.5,0,0,3.5), (2,46,8,4.1,1,5,38,2.5),
                    (1,50,8,3.5,1.5,0,0,3.5), (6,40,8,4.1,1.5,5,37,2.5)],
            '217': [(3,38,10,4.1,1,5,27,2), (4,37,10,4.1,1,5,26,4),
                    (5,33,8,3.5,1,0,0,3), (2,40,10,4,1,5,21,8),
                    (1,25,8,3.5,1,0,0,3), (6,32,10,4,1,5,21,8)],
        }
        fields = ('signal_group', 'split_s', 'min_green_s', 'amber_s', 'all_red_s',
                  'walk_s', 'ped_clearance_s', 'vehicle_extension_s')
        for site, values in expected.items():
            rows = [r for r in timing_rows() if r['site_id'] == site]
            self.assertEqual([tuple(float(r[k]) for k in fields) for r in rows], values)
            self.assertEqual({(float(r['cycle_s']), float(r['offset_s'])) for r in rows},
                             {(180,120) if site == '211' else (140,57)})

    def test_comparison_labels_and_hashes_merged_demand_without_simulation(self):
        original = p.ROOT
        def fake_run(args):
            outputs = {'--summary-output': '<summary><step teleports="0" inserted="0" running="0" waiting="0"/></summary>',
                       '--tripinfo-output': '<tripinfos/>', '--vehroute-output': '<routes/>', '--error-log': ''}
            for flag, value in outputs.items():
                Path(args[args.index(flag)+1]).write_text(value)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ('config', 'sim', 'data'):
                (root/name).symlink_to(original/name, target_is_directory=True)
            (root/'reports').mkdir()
            with patch.object(p, 'ROOT', root), patch.object(p, 'run', side_effect=fake_run) as run, \
                 patch.object(comparison.subprocess, 'check_output', return_value='100%; AC Power'), \
                 patch.object(comparison.subprocess, 'run') as process, \
                 patch.object(comparison, 'metrics', return_value={'requested': 1}), contextlib.redirect_stdout(io.StringIO()):
                process.return_value.returncode = 1
                comparison.compare()
            self.assertEqual(run.call_count, 6)
            for call in run.call_args_list:
                args = call.args[0]
                self.assertEqual(Path(args[args.index('-r')+1]), root/'sim/routes_pm_peak.rou.xml')
            for name in ('vta_timing_comparison.csv', 'vta_movement_comparison.csv'):
                with open(root/'reports'/name) as stream:
                    rows = list(csv.DictReader(stream))
                self.assertTrue(rows)
                self.assertEqual({r['demand_basis'] for r in rows}, {comparison.DEMAND_BASIS})
            provenance = json.loads((root/'reports/vta_timing_run.json').read_text())
            self.assertEqual(provenance['demand_basis'], comparison.DEMAND_BASIS)
            self.assertTrue({'data/processed/tmc.csv', 'data/processed/tmc_sources.csv',
                             'data/processed/vta_counts_2024.csv', 'sim/routes_pm_peak.rou.xml'} <= provenance['sha256'].keys())

    def test_source_sanity_preserves_and_exposes_contradictions(self):
        rows = timing_rows()
        self.assertEqual(len(rows), 14)
        self.assertEqual(len({(r['site_id'], r['signal_group']) for r in rows}), 14)
        issues = source_issues(rows)
        self.assertEqual(issues[:2], ['211 ring 1: splits 203 s != cycle 180 s',
                                     '211 ring 2: splits 170 s != cycle 180 s'])
        self.assertEqual(len(issues), 17)  # Two ring, 14 max-green, and one pedestrian discrepancy.
        for row in rows:
            self.assertEqual(row['basis'], LABEL)
            self.assertEqual(float(row['max_green_s']), float(row['split_s']))
            self.assertLess(float(row['min_green_s'])+float(row['amber_s'])+float(row['all_red_s']), float(row['split_s']))
            if float(row['max_green_s']) < float(row['walk_s'])+float(row['ped_clearance_s']):
                self.assertEqual((row['site_id'], row['signal_group']), ('211', '6'))
        stelling = [r for r in rows if r['site_id'] == '217']
        for ring in ('1', '2'):
            active = sum(float(r['split_s']) for r in stelling if r['ring'] == ring)
            inactive = sum(float(r['split_s']) for r in stelling if r['control_type'] == 'Split') if ring == '2' else 0
            self.assertEqual(active+inactive, 140)

    def test_reported_movements(self):
        with open(p.ROOT/'data/processed/vta_vistro_results_2024.csv') as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 32)
        self.assertEqual(len({(r['site_id'], r['direction'], r['movement']) for r in rows}), 32)
        for row in rows:
            self.assertGreater(float(row['delay_s_per_vehicle']), 0)
            self.assertIn(row['los'], 'ABCDEF')
            self.assertEqual(row['source_page'], '5')
            self.assertEqual(row['basis'], LABEL)
        self.assertEqual(next(r['delay_s_per_vehicle'] for r in rows if (r['site_id'], r['direction'], r['movement']) == ('211', 'SB', 'T')), '41.46')

    def test_plan_reproducible_without_simulation(self):
        with patch.object(p, 'run', side_effect=AssertionError('SUMO forbidden')), patch.object(p, 'xml_write') as xml_write, patch.object(p, 'write_csv') as write_csv, contextlib.redirect_stdout(io.StringIO()):
            existing_vta()
        actual = ET.parse(p.ROOT/'sim/tls_existing_vta_pm_peak.add.xml').getroot()
        generated = ET.fromstring(ET.tostring(xml_write.call_args.args[0]))
        self.assertEqual(ET.tostring(generated).replace(b'\n', b'').replace(b'  ', b''),
                         ET.tostring(actual).replace(b'\n', b'').replace(b'  ', b''))
        with open(p.ROOT/'reports/timing_existing_vta_pm_peak.csv') as stream:
            saved = list(csv.DictReader(stream))
        self.assertEqual([{k: str(v) for k, v in r.items()} for r in write_csv.call_args.args[1]], saved)

    def test_mapping_clearances_and_untouched_other_signals(self):
        old = {t.get('id'): t for t in ET.parse(p.ROOT/'sim/tls_actuated_pm_peak.add.xml').getroot().findall('tlLogic')}
        new = {t.get('id'): t for t in ET.parse(p.ROOT/'sim/tls_existing_vta_pm_peak.add.xml').getroot().findall('tlLogic')}
        net = network()
        mapping = movement_map(net)
        source = {(r['intersection'], int(r['signal_group'])): r for r in timing_rows()}
        with open(p.ROOT/'reports/timing_existing_vta_pm_peak.csv') as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(set(old), set(new))
        for signal in p.config()['signals']:
            logic = new[signal['sumo_tls_id']]
            selected = [r for r in rows if r['sumo_tls_id'] == signal['sumo_tls_id']]
            if not selected:
                before = old[signal['sumo_tls_id']]
                before.set('programID', 'existing_vta')
                self.assertEqual(ET.tostring(before), ET.tostring(logic))
                continue
            phases = logic.findall('phase')
            cycle = float(selected[0]['cycle_s'])
            self.assertAlmostEqual(sum(float(r['applied_split_s']) for r in selected)+float(selected[0]['nominal_slack_s']), cycle)
            self.assertEqual(float(logic.get('offset')), 120 if signal['name'] == 'De Anza Blvd' else 57)
            self.assertEqual(selected[0]['signal_groups'], '1;5')
            for row in selected:
                i = int(row['phase'])
                phase = phases[i]
                self.assertLess(float(phase.get('minDur')), float(phase.get('maxDur')))
                self.assertAlmostEqual(float(row['max_green_s'])+float(row['yellow_s'])+float(row['red_clear_s']), float(row['applied_split_s']))
                self.assertLessEqual(float(phase.get('latestEnd')), cycle)
                expected = set()
                for group in map(int, row['signal_groups'].split(';')):
                    expected.update(source[signal['name'], group]['served_movements'].split(';'))
                for (name, leg, turn), pair in mapping.items():
                    if name != signal['name']:
                        continue
                    direction = {'S': 'NB', 'N': 'SB', 'W': 'EB', 'E': 'WB'}[leg]
                    links = {link for a, b, link in net.getTLS(signal['sumo_tls_id']).getConnections()
                             if (a.getEdge().getID(), b.getEdge().getID()) == pair}
                    served = any(phase.get('state')[link] in 'Gg' for link in links)
                    self.assertEqual(served, f'{direction}_{turn}' in expected, (signal['name'], i, leg, turn))
                for successor in map(int, phase.get('next').split()):
                    if successor == i:
                        self.assertEqual(phase.get('name'), 'recall_rest')
                        continue
                    yellow = phases[successor]
                    red = phases[int(yellow.get('next'))]
                    self.assertEqual(yellow.get('state'), ''.join('y' if c == 'G' else 'r' for c in phase.get('state')))
                    self.assertEqual(red.get('state'), 'r'*len(phase.get('state')))
                    self.assertEqual(float(yellow.get('duration')), float(row['yellow_s']))
                    self.assertEqual(float(red.get('duration')), float(row['red_clear_s']))

    def test_local_delay_proxy_excludes_other_cohorts_teleports_and_unfinished(self):
        class Edge:
            def getLength(self): return 100
            def getSpeed(self): return 10
        class Net:
            def getEdge(self, edge): return Edge()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'routes.xml'
            path.write_text('<routes>'+''.join(f'<vehicle id="{vid}" depart="0"><route edges="a b" exitTimes="10 {end}"/></vehicle>' for vid, end in [('ok', 30), ('teleport', 99), ('unfinished', -1), ('other', 99)])+'</routes>')
            values = movement_delays(path, Net(), {('Stelling Rd', 'N', 'L'): ('a', 'b')}, {'ok', 'teleport', 'unfinished'}, {'teleport'})
            self.assertEqual(dict(values), {('Stelling Rd', 'N', 'L'): [10]})
