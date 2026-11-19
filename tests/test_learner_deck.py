"""Keep the presentation's numbers tied to the frozen research outputs."""
import json
from pathlib import Path
import re
import unittest

from tools import demo

ROOT = Path(__file__).resolve().parents[1]
DECK = ROOT / "dashboard/signal-learner"


def visible(slide):
    """Slide text a viewer sees, without speaker notes or markup."""
    return re.sub(r"<[^>]+>", " ", slide.split('<aside class="notes">')[0])


class LearnerDeckTests(unittest.TestCase):
    def setUp(self):
        self.deck = (DECK / "index.html").read_text()
        self.slides = re.findall(r'<section class="slide\b.*?</section>', self.deck, re.S)
        facts = json.loads((ROOT / "reports/learner_story/facts.json").read_text())["facts"]
        self.facts = {(f["road"], f["name"]): f["value"] for f in facts}

    def pct(self, road):
        return f"&minus;{round(-100 * self.facts[(road, 'learner_change')])}%"

    def test_slides_keep_notes_media_and_backup_split(self):
        self.assertEqual(len(self.slides), 17)
        for slide in self.slides:
            self.assertRegex(slide, r'<aside class="notes">[^<]+</aside>')
        self.assertIn("150 seconds", self.slides[0])
        self.assertIn('src="wolfe_side_by_side.mp4"', self.slides[3])
        self.assertIn('src="wolfe_side_by_side_poster.png"', self.slides[3])
        self.assertEqual([("data-backup" in s) for s in self.slides], [False] * 6 + [True] * 11)

    def test_demo_link_is_served_by_the_launcher(self):
        link = re.search(r'href="(console/[^"#]*)', self.slides[2]).group(1)
        self.assertIn(link + "index.html", demo.ASSETS)

    def test_numbers_match_saved_facts(self):
        f = self.facts
        wolfe = visible(self.slides[3])
        self.assertIn(str(round(f[("wolfe", "old_delay")])), wolfe)
        self.assertIn(str(round(f[("wolfe", "learner_delay")])), wolfe)
        self.assertIn(self.pct("wolfe"), wolfe)
        self.assertIn("all 20", wolfe)
        self.assertEqual(len(f[("wolfe", "test_seeds")]), 20)

        posthoc = f[("deanza", "deanza_posthoc")]
        deanza = visible(self.slides[8])
        self.assertEqual(f[("deanza", "decision")], "no change")
        self.assertIn(str(round(posthoc["old_delay_s"])), deanza)
        self.assertIn(str(round(posthoc["rejected_plan"]["all_requested_delay_s"]["mean"])), deanza)
        self.assertIn(f"{100 * posthoc['change_share']:.1f}% worse", deanza)
        self.assertIn(f"{posthoc['seeds_worse']} of {len(posthoc['seeds'])}", deanza)

        limits = visible(self.slides[9])
        self.assertIn(f"+{round(f[('wolfe', 'learner_worst_origin_change')])} s", limits)
        self.assertIn(f"{round(10 * f[('deanza', 'go_back_noop_undone')])} of 10", limits)

        roads = visible(self.slides[13])
        for road in ("homestead", "stevens_creek", "wolfe"):
            self.assertIn(self.pct(road), roads)
        self.assertEqual(f[("deanza", "learner_change")], 0)
        self.assertIn("No change", roads)

        score = visible(self.slides[15])
        self.assertIn(str(round(f[("wolfe", "old_unfinished")])), score)
        self.assertIn(str(round(f[("wolfe", "learner_unfinished")])), score)

    def test_vta_credit_and_one_limits_slide(self):
        self.assertIn("VTA, 2024 CMP Monitoring and Conformance Report", self.slides[13])
        for i, slide in enumerate(self.slides):
            text = visible(slide)
            if "VTA" in text:
                self.assertIn("VTA, 2024 CMP Monitoring and Conformance Report", text)
            for hedge in ("not measured", "sketch", "we have not shown", "POST-HOC"):
                self.assertNotIn(hedge, text.lower() if hedge.islower() else text)
            if i != 9:
                self.assertNotIn("+203", text)

    def test_pdf_has_one_page_per_slide(self):
        pdf = (DECK / "signal-learner.pdf").read_bytes()
        self.assertEqual(len(re.findall(rb"/Type\s*/Page\b", pdf)), len(self.slides))


if __name__ == "__main__":
    unittest.main()
