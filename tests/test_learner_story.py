import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from learner import card
from signal_lab import pipeline as p


def result(gain=.11, p_value=.002, best=7, old_tele=(10, 10), new_tele=(10, 15), old_side=(100, 100), new_side=(90, 90)):
    stats = lambda tele, side: [dict(seed=10+i, teleports=t, side_all_requested_delay_s=s) for i, (t, s) in enumerate(zip(tele, side))]
    return dict(best_trial=best, confirm_gain=gain, confirm_p=p_value, confirm_old=stats(old_tele, old_side),
                confirm_new=stats(new_tele, new_side), clear_gain=False)


class CardWhyTests(unittest.TestCase):
    def test_names_the_teleport_gate_and_seeds(self):
        text = card.why(result())
        self.assertIn('11.0%', text)
        self.assertIn('teleports more than old + 2 on copy seeds 11', text)
        self.assertNotIn('no clear gain', text)

    def test_names_each_failed_gate(self):
        text = card.why(result(gain=.01, p_value=.2, new_tele=(10, 10), new_side=(120, 120)))
        self.assertIn('gain under 2%', text)
        self.assertIn('p not under 0.05', text)
        self.assertIn('side-street delay 1.20x old', text)
        self.assertNotIn('teleports', text)

    def test_clear_gain_and_no_better_trial(self):
        self.assertEqual(card.why(dict(result(), clear_gain=True)), 'The copy predicts a clear gain.')
        self.assertIn('nothing better', card.why(result(best=0)))


class FactsTests(unittest.TestCase):
    def test_every_fact_has_unit_label_and_existing_source(self):
        from tools import learner_story
        if not (learner_story.HELDOUT/'results.json').exists():
            self.skipTest('needs the committed held-out results')
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(learner_story, 'OUT', Path(temp)):
            learner_story.facts()
            facts = json.loads((Path(temp)/'facts.json').read_text())['facts']
        self.assertEqual({f['road'] for f in facts}, {'wolfe', 'deanza', 'stevens_creek', 'homestead'})
        for f in facts:
            self.assertTrue(f['unit'] and f['label'], f)
            self.assertTrue((p.ROOT/f['source']).exists(), f)
        get = {(f['road'], f['name']): f['value'] for f in facts}
        self.assertAlmostEqual(get['wolfe', 'old_delay'], 870.49, places=1)
        self.assertAlmostEqual(get['wolfe', 'learner_delay'], 643.11, places=1)
        self.assertAlmostEqual(get['deanza', 'learner_delay'], get['deanza', 'old_delay'], places=6)
        self.assertNotIn(('deanza', 'actual_change'), get)


if __name__ == '__main__':
    unittest.main()
