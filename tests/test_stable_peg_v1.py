import unittest
from dataclasses import replace
from research.stable_peg_v1 import *
class Tests(unittest.TestCase):
    def bars(self,n=800):return [dict(timestamp=i*STEP,open=1.,high=1.0005,low=.9995,close=1.) for i in range(n)]
    def trigger(self):
        b=self.bars();b[10].update(open=.993,high=.994,low=.992,close=.993);b[11].update(open=.993,high=.994,low=.992,close=.993);return b
    def test_next_open_target(self):
        b=self.trigger();b[12]['high']=1.;t=backtest(b,0,800*STEP)[0];self.assertEqual((t['signal_index'],t['entry_index'],t['exit_index'],t['reason']),(10,11,12,'TARGET'))
    def test_stop_priority_and_gap(self):
        b=self.trigger();b[11].update(high=1.,low=.987);self.assertEqual(backtest(b,0,800*STEP)[0]['reason'],'STOP')
        b=self.trigger();b[12].update(open=.985,high=.986,low=.984,close=.985);self.assertEqual(backtest(b,0,800*STEP)[0]['reason'],'GAP_STOP')
    def test_costs_stress_sizing(self):
        b=self.trigger();b[12]['high']=1.;t=backtest(b,0,800*STEP)[0];s=backtest(b,0,800*STEP,replace(Config(),fee=.0019,slippage=.0004))[0]
        self.assertAlmostEqual(t['gross']-t['fees']-t['slippage_cost'],t['pnl']);self.assertLess(s['pnl'],t['pnl']);self.assertLessEqual(t['entry']*t['qty'],(10000/3)*.2+1e-8);self.assertLessEqual((t['entry']-t['stop'])*t['qty'],(10000/3)*.005+1e-8)
    def test_reject_gap_invalid_and_high_open(self):
        b=self.trigger();b[11].update(open=.997,high=.9975);self.assertEqual(backtest(b,0,800*STEP),[])
        b=self.bars();b.pop(2)
        with self.assertRaises(ValueError):validate(b)
        b=self.bars();b[2]['low']=1.1
        with self.assertRaises(ValueError):validate(b)
    def test_no_signal_no_trade(self):self.assertEqual(backtest(self.bars(),0,800*STEP),[])
if __name__=='__main__':unittest.main()
