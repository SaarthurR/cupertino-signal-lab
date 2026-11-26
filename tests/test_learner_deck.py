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
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", slide.split('<aside class="notes">')[0]))


class LearnerDeckTests(unittest.TestCase):
    def setUp(self):
        self.deck = (DECK / "index.html").read_text()
        self.slides = re.findall(r'<section class="slide\b.*?</section>', self.deck, re.S)
        facts = json.loads((ROOT / "reports/learner_story/facts.json").read_text())["facts"]
        self.facts = {(f["road"], f["name"]): f["value"] for f in facts}

    def test_talk_end_backup_and_notes(self):
        self.assertEqual(len(self.slides), 18)
        for slide in self.slides:
            self.assertRegex(slide, r'<aside class="notes">[^<]+</aside>')
        self.assertEqual([("data-backup" in s) for s in self.slides], [False] * 8 + [True] * 9 + [False])
        self.assertIn("End of talk", visible(self.slides[7]))
        self.assertEqual(re.findall(r'href="#(\d+)"', self.slides[7]), list(map(str, range(10, 19))))
        self.assertEqual(re.findall(r'data-label="Backup (B\d)"', "".join(self.slides[8:17])), [f"B{i}" for i in range(1, 10)])
        self.assertIn("60 seconds", visible(self.slides[17]))

    def test_demo_slide_embeds_the_served_console(self):
        link = re.search(r'<iframe id="console" src="(console/)#/wolfe/review"', self.slides[3]).group(1)
        self.assertIn(link + "index.html", demo.ASSETS)
        self.assertIn('src="img/live.png"', self.slides[3])
        for src in re.findall(r'<img[^>]+src="([^"]+)"', self.deck):
            self.assertIn(src, demo.ASSETS)

    def test_numbers_match_saved_facts(self):
        f = self.facts
        pct = f"−{round(-100 * f[('wolfe', 'learner_change')])}%"
        result = visible(self.slides[4])
        self.assertIn(str(round(f[("wolfe", "old_delay")])), result)
        self.assertIn(str(round(f[("wolfe", "learner_delay")])), result)
        self.assertIn(pct, result)
        self.assertIn("all 20", result)
        self.assertEqual(len(f[("wolfe", "test_seeds")]), 20)
        self.assertIn(f"from about {round(f[('wolfe', 'old_unfinished')])} to {round(f[('wolfe', 'learner_unfinished')])}", self.slides[4])

        numbers = visible(self.slides[8])
        self.assertIn(f"{f[('wolfe', 'old_delay')]:.1f} → {f[('wolfe', 'learner_delay')]:.1f} s", numbers)
        self.assertIn(f"−{-100 * f[('wolfe', 'learner_change')]:.1f}%", numbers)
        self.assertIn(f"{f[('wolfe', 'copy_old_delay')]:.1f} → {f[('wolfe', 'copy_old_delay')] * (1 + f[('wolfe', 'predicted_change')]):.1f} s", numbers)
        self.assertIn(f"−{round(-100 * f[('wolfe', 'predicted_change')])}%", numbers)

        posthoc = f[("deanza", "deanza_posthoc")]
        deanza = visible(self.slides[13])
        self.assertEqual(f[("deanza", "decision")], "no change")
        self.assertIn(f"{f[('deanza', 'old_delay')]:.1f} s", deanza)
        self.assertIn(f"{100 * -f[('deanza', 'predicted_change')]:.1f}%", deanza)
        self.assertIn(f"{round(10 * f[('deanza', 'go_back_noop_undone')])} of 10", deanza)
        self.assertIn(f"{posthoc['old_delay_s']:.1f} s", deanza)
        self.assertIn(f"{posthoc['rejected_plan']['all_requested_delay_s']['mean']:.1f} s, +{100 * posthoc['change_share']:.1f}%", deanza)
        self.assertIn(f"{posthoc['seeds_worse']} of {len(posthoc['seeds'])}", deanza)

        worst = visible(self.slides[14])
        self.assertIn(f"+{round(f[('wolfe', 'learner_worst_origin_change')])} s", worst)
        self.assertIn(f"{f[('wolfe', 'old_worst_origin_delay')]:,.1f} → {f[('wolfe', 'learner_worst_origin_delay')]:,.1f} s", worst)
        self.assertIn(f"about {round(f[('wolfe', 'learner_worst_origin_change')])} s", visible(self.slides[5]))

    def test_vta_credit_and_limit_wording(self):
        for i, slide in enumerate(self.slides):
            text = visible(slide)
            if "VTA" in text:
                self.assertIn("VTA, 2024 CMP Monitoring and Conformance Report", text)
            if i != 14:
                self.assertNotIn("+203", text)
            self.assertNotIn("got worse", slide.lower())
        self.assertIn("Worst-off start point on Wolfe got slower", visible(self.slides[5]))
        self.assertIn("Worst-origin delay score", visible(self.slides[14]))

    def test_pdf_has_one_page_per_slide(self):
        pdf = (DECK / "signal-learner.pdf").read_bytes()
        self.assertEqual(len(re.findall(rb"/Type\s*/Page\b", pdf)), len(self.slides))


if __name__ == "__main__":
    unittest.main()
