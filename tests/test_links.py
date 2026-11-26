import unittest

from tools import check_links


class DocLinks(unittest.TestCase):
    def test_slug_matches_github_anchors(self):
        self.assertEqual(check_links.slug('6. Judge questions and short answers'), '6-judge-questions-and-short-answers')
        self.assertEqual(check_links.slug('Demo script (85 seconds)'), 'demo-script-85-seconds')

    def test_every_local_doc_link_opens(self):
        checked, bad = check_links.find_broken(web=False)
        self.assertGreater(checked, 0)
        self.assertEqual(bad, [], 'broken links:\n' + '\n'.join(bad))


if __name__ == '__main__':
    unittest.main()
