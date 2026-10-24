import unittest
from datetime import datetime,timezone
from research.weekend_drift_v1 import backtest
class WeekendTests(unittest.TestCase):
    def bars(self):
        start=int(datetime(2026,7,3,tzinfo=timezone.utc).timestamp()*1000)
        return [dict(timestamp=start+i*900000,open=100.,high=100.1,low=99.9,close=100.) for i in range(400)]
    def test_calendar_timing_and_costs(self):
        t=backtest(self.bars())[0]
        self.assertEqual((t['entry_index'],t['exit_index']),(96,288))
        self.assertEqual(t['reason'],'CALENDAR_EXIT')
        self.assertLess(t['pnl'],0)
    def test_gap_stop(self):
        b=self.bars();b[100].update(open=90.,high=91.,low=89.,close=90.)
        t=backtest(b)[0];self.assertEqual(t['reason'],'GAP_STOP');self.assertLess(t['exit'],90)
