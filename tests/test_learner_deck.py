"""Keep the presentation's evidence labels distinct from frozen research outputs."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LearnerDeckTests(unittest.TestCase):
    def setUp(self):
        self.deck = (ROOT / "dashboard/signal-learner/index.html").read_text()
        self.slides = re.findall(r'<section class="slide\b.*?</section>', self.deck, re.S)

    def test_all_slides_retain_speaker_notes_and_media(self):
        self.assertEqual(len(self.slides), 16)
        for slide in self.slides:
            self.assertRegex(slide, r'<aside class="notes">[^<]+</aside>')
        self.assertIn('src="wolfe_side_by_side.mp4"', self.slides[8])
        self.assertIn('src="wolfe_side_by_side_poster.png"', self.slides[8])

    def test_evidence_boundaries_survive_export_source_edits(self):
        self.assertIn("Team observation", self.slides[1])
        self.assertIn("870.49", self.slides[9])
        self.assertIn("643.11", self.slides[9])
        self.assertIn("divided by all requested trips", self.slides[9])
        self.assertIn("Delay score per requested trip", self.slides[11])
        self.assertIn("137.6", self.slides[6])
        limits = self.slides[12].split('<aside class="notes">')[0]
        self.assertIn("signal-turn passages, not unique vehicles", limits)
        self.assertNotIn("fewer trips", limits)
        self.assertIn("+203 s", limits)
        self.assertIn("4 of 10", limits)
        self.assertIn("VTA, 2024 CMP Monitoring and Conformance Report", self.slides[11])
        self.assertIn("original results unchanged", self.slides[14])
        self.assertIn("no integration built yet", self.slides[13])
