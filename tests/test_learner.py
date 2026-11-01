from pathlib import Path
import random
import shutil
import statistics
import sys
import tempfile
import unittest
from unittest import mock
import xml.etree.ElementTree as ET

from learner import card, check, learn, practice, road
from signal_lab import pipeline as p
from world import trial

LEARNER = p.ROOT/'src/learner'
ACCESS = []


def _audit(event, args):
    if event == 'open' and isinstance(args[0], (str, Path)):
        ACCESS.append(str(args[0]))
    elif event == 'subprocess.Popen':
        ACCESS.extend(part for arg in args[1] or () for part in str(arg).split(','))


sys.addaudithook(_audit)


class GuardTests(unittest.TestCase):
    """The learner sees only the road (map, signals, loops, old timing) and its own outputs."""

    def test_learner_source_has_no_path_to_world_demand(self):
        for path in LEARNER.glob('*.py'):
            text = path.read_text()
            for word in ('world', 'learner_truth', 'learner_heldout', 'routes_pm_peak', 'routes_night',
                         'tmc', 'turns_pm', 'vta_counts', 'candidate_routes.rou'):
                self.assertNotIn(word, text, f'{path.name} mentions {word}')

    def test_learner_steps_open_only_road_files_and_own_outputs(self):
        name = 'homestead'
        cfg = road.load(name)
        feed = road.OUT/name/'feed'
        if not feed.exists():
            self.skipTest('needs the committed Homestead feed')
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)/'learner'
            shutil.copytree(feed, out/name/'feed')
            allowed = [p.ROOT/'src', p.ROOT/'.venv', p.ROOT/'roads', out] + \
                [road.file(cfg, k) for k in ('net', 'detectors', 'timing_inputs', 'old_timing')]
            with mock.patch.object(road, 'OUT', out):
                ACCESS.clear()
                learn.learn(name)
                practice.practice(name, trials=1, search_seeds=range(1), confirm_seeds=range(1))
                card.recommend(name)
                rows = learn.read(name, 'feed')[0]
                check.decide(name, rows, 0)
                opened = list(ACCESS)
        inside = {Path(a).resolve() for a in opened if a.startswith(str(p.ROOT))}
        bad = [a for a in inside if not any(a == x or x in a.parents for x in allowed)]
        self.assertTrue(inside)
        self.assertEqual(bad, [], 'learner opened files outside the road and its own outputs')


class FeedToDemandTests(unittest.TestCase):
    def test_pattern_counts_and_dedicated_turns(self):
        cfg = road.load('homestead')
        network = road.net(cfg)
        rels = road.relations(cfg, network)
        lanes = [l.getID() for incoming in rels for l in network.getEdge(incoming).getLanes()]
        days = [[dict(window_end=f'2026-10-31T16:{m:02d}:00-07:00', lane=lane, count=str(day+1))
                 for m in (35, 40, 45) for lane in lanes] for day in range(3)]
        pattern = learn.pattern(days, lambda r: r['lane'])
        begin = road.window(cfg)[0]
        self.assertEqual(pattern[begin, lanes[0]], (6, statistics.pstdev([3, 6, 9])))
        owner = learn.exclusive_lanes(network, rels)
        with tempfile.TemporaryDirectory() as temp:
            exact = learn.count_files(cfg, network, pattern, temp)
            edges = ET.parse(Path(temp)/'edges.xml').getroot()
            turns = ET.parse(Path(temp)/'turns.xml').getroot()
        self.assertEqual([i.get('begin') for i in edges], [str(begin-cfg['warmup_s']), str(begin)])
        first, second = ({e.get('id'): int(e.get('entered')) for e in i} for i in edges)
        self.assertEqual(first, second)
        for incoming in rels:
            self.assertEqual(second[incoming], 6*len(network.getEdge(incoming).getLanes()))
        for relation in turns[1]:
            pair = relation.get('from'), relation.get('to')
            serving = [l for l, targets in owner.items() if pair[1] in targets and l.rsplit('_', 1)[0] == pair[0]]
            self.assertTrue(serving and all(len(owner[l]) == 1 for l in serving))
            self.assertEqual(int(relation.get('count')), 6*len(serving))
            self.assertIn(pair, exact)
        shared = {(l.rsplit('_', 1)[0], o) for l, t in owner.items() if len(t) > 1 for o in t}
        self.assertTrue(shared)
        self.assertFalse(shared & exact, 'turns through shared lanes are unknown, not counted')


class BoundsTests(unittest.TestCase):
    def test_learner_plans_keep_order_clearances_and_minimums(self):
        rng = random.Random(0)
        for name in ('homestead', 'stevens_creek'):
            cfg = road.load(name)
            old = practice.old_params(cfg)
            source = ET.parse(road.file(cfg, 'old_timing')).getroot().findall('tlLogic')
            for trial_index in range(15):
                params = {k: rng.uniform(*practice.bounds(k, old['cycle_s'])) for k in old if practice.searched(k)}
                with tempfile.TemporaryDirectory() as temp:
                    path = Path(temp)/'plan.xml'
                    try:
                        practice.plan(cfg, params, path)
                    except ValueError:
                        continue  # the search scores these as infeasible
                    logics = ET.parse(path).getroot().findall('tlLogic')
                low, high = practice.bounds('cycle_s', old['cycle_s'])
                for before, after in zip(source, logics):
                    cycle = float(next(v.get('value') for v in after.findall('param') if v.get('key') == 'cycleTime'))
                    self.assertTrue(low <= cycle <= high)
                    self.assertTrue(0 <= float(after.get('offset')) < cycle)
                    self.assertEqual(after.get('programID'), 'learner')
                    gap = lambda logic: next(v.get('value') for v in logic.findall('param') if v.get('key') == 'max-gap')
                    self.assertEqual(float(gap(before)), float(gap(after)))
                    for a, b in zip(before.findall('phase'), after.findall('phase'), strict=True):
                        self.assertEqual((a.get('state'), a.get('next')), (b.get('state'), b.get('next')))
                        if a.get('minDur') is None:
                            self.assertEqual(a.get('duration'), b.get('duration'))
                        else:
                            self.assertEqual(float(a.get('minDur')), float(b.get('minDur')))
                            self.assertTrue(max(10, float(a.get('minDur'))+1)-1e-6 <= float(b.get('maxDur')) <= 60)
            with tempfile.TemporaryDirectory() as temp:
                with self.assertRaises(ValueError):
                    practice.plan(cfg, {**{k: v for k, v in old.items() if practice.searched(k)},
                                        next(k for k in old if k.startswith('share_')): 1.5}, Path(temp)/'x.xml')


class GoBackRuleTests(unittest.TestCase):
    def rows(self, start, rises, approaches=('A', 'B', 'C', 'D'), base=10., ok=1, raised=('A', 'B')):
        return [dict(window_end=f'2026-10-31T{(start+300*i)//3600:02d}:{(start+300*i)%3600//60:02d}:00-07:00',
                     site='S', approach=a, count='5', occupancy=str(base+(rise if a in raised else 0)), ok=str(ok))
                for i, rise in enumerate(rises) for a in approaches]

    def decide(self, after, approaches=('A', 'B', 'C', 'D')):
        watched = [self.rows(61200, [0]*12, approaches, base=b) for b in (9., 10., 11.)]
        with mock.patch.object(learn, 'read', return_value=watched):
            return check.decide('any', after, 61200)

    def test_goes_back_after_three_bad_windows_only(self):
        self.assertFalse(self.decide(self.rows(61500, [2, -3, 4, 1, 0, 3]))['go_back'])
        self.assertFalse(self.decide(self.rows(61500, [40, 40, 0, 40, 40, 0]))['go_back'])
        decision = self.decide(self.rows(61500, [0, 40, 40, 40, 0]))
        self.assertTrue(decision['go_back'])
        self.assertEqual(decision['time_s'], 61500+300*3)
        self.assertFalse(self.decide(self.rows(61500, [40, 40, 40], ok=0))['go_back'], 'suspect windows are ignored')
        ten = tuple('ABCDEFGHIJ')
        self.assertFalse(self.decide(self.rows(61500, [45, 45, 45], ten, raised=('A',)), ten)['go_back'],
                         'one approach alone is not enough')
        self.assertTrue(self.decide(self.rows(61500, [30, 30, 30], ten), ten)['go_back'])
        # A road-wide rise trips the mean test even when no single approach crosses its own threshold.
        everywhere = [{**r, 'occupancy': str(float(r['occupancy'])+8)} for r in self.rows(61500, [0, 0, 0])]
        self.assertTrue(self.decide(everywhere)['go_back'])


class RefusalTests(unittest.TestCase):
    def test_heldout_test_refuses_once_results_exist(self):
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(trial, 'HELDOUT', Path(temp)), \
                mock.patch.object(trial.w, 'build_world', side_effect=AssertionError('must not run')):
            with self.assertRaisesRegex(RuntimeError, 'refusing'):
                trial.heldout_test()

    def test_learner_will_not_run_on_heldout_roads_outside_the_test(self):
        for name in trial.HELDOUT_ROADS:
            self.assertEqual(road.load(name)['role'], 'heldout')
            with self.assertRaisesRegex(RuntimeError, 'held out'):
                trial.run_learner(name)

    def test_holm(self):
        self.assertEqual(trial.holm([.01, .04]), [.02, .04])
        self.assertEqual(trial.holm([.04, .01]), [.04, .02])
        self.assertEqual(trial.holm([.03, .02]), [.04, .04])


if __name__ == '__main__':
    unittest.main()
