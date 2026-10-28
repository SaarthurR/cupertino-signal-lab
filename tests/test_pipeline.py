import subprocess
import sys
import unittest


class Milestones(unittest.TestCase):
    def test_m0_verbs(self):
        for verb in ('build-net', 'build-demand', 'check-demand', 'baseline', 'optimize', 'eval', 'bench', 'dashboard'):
            result = subprocess.run([sys.executable, '-m', 'signal_lab', verb, '--help'], capture_output=True)
            self.assertEqual(result.returncode, 0, verb)
