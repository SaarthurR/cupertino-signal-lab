import unittest

from signal_lab import closed_loop as c


class Connection:
    def __init__(self):
        self.calls, self.program = [], {}
        self.trafficlight = self

    def getProgram(self, tls):
        return self.program.get(tls, 'old')

    def getPhase(self, tls):
        return 0

    def getNextSwitch(self, tls):
        return 110

    def setProgram(self, tls, program):
        self.program[tls] = program
        self.calls.append(tls)

    def setPhase(self, tls, phase):
        pass

    def setPhaseDuration(self, tls, duration):
        pass


class ClosedLoopTest(unittest.TestCase):
    def test_approval_waits_five_minutes(self):
        self.assertFalse(c.approval_due(None, 1000, None))
        self.assertFalse(c.approval_due(('light', 1000), 1299, None))
        self.assertTrue(c.approval_due(('light', 1000), 1300, None))

    def test_switches_stay_fifteen_minutes_apart(self):
        self.assertFalse(c.approval_due(('light', 1000), 1300, 500))
        self.assertTrue(c.approval_due(('light', 1000), 1400, 500))

    def test_switch_moves_all_five_signals(self):
        connection = Connection()
        changes = c.switch(connection, 'sim/tls_advisor_light.add.xml', 100)
        self.assertEqual(len(set(connection.calls)), 5)
        self.assertEqual(len(changes), 5)
        self.assertTrue(all(change['phase'] == 0 for change in changes))


if __name__ == '__main__':
    unittest.main()
