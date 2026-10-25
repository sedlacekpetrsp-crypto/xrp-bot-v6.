import unittest
from dataclasses import replace
from unittest.mock import patch
from research.oi_crowding_v1 import *
class Tests(unittest.TestCase):
    def data(self,n=400):
        b=[dict(timestamp=i*STEP,open=100.,high=100.5,low=99.5,close=100.) for i in range(n)]
        m=[dict(timestamp=i*STEP,open_interest=1000.,long_short=1.+(i%3-1)*.001,taker_ratio=1.) for i in range(n)];return b,m
    def run_one(self,b=None,m=None,c=Config()):
        b,m=(b,m) if b else self.data()
        with patch('research.oi_crowding_v1.signal',side_effect=lambda b,m,i,c:dict(atr=1.,z=-3.,oi_change=-.02,taker_ratio=1.2) if i==300 else None):return backtest(b,m,0,400*STEP,c)
    def test_next_open_and_time(self):
        t=self.run_one()[0];self.assertEqual((t['signal_index'],t['entry_index'],t['exit_index']),(300,301,336))
    def test_costs_and_sizing(self):
        t=self.run_one()[0];s=self.run_one(c=replace(Config(),fee=.0019,slippage=.0004))[0];self.assertAlmostEqual(t['gross']-t['fees']-t['slippage_cost'],t['pnl']);self.assertLess(s['pnl'],t['pnl']);self.assertLessEqual(t['entry']*t['qty'],2000.0001);self.assertLessEqual((t['entry']-t['stop'])*t['qty'],50.0001)
    def test_stop_priority_gap(self):
        b,m=self.data();b[301].update(high=110.,low=90.);self.assertEqual(self.run_one(b,m)[0]['reason'],'STOP')
        b,m=self.data();b[302].update(open=90.,high=91.,low=89.,close=90.);self.assertEqual(self.run_one(b,m)[0]['reason'],'GAP_STOP')
    def test_real_signal_future_invariance(self):
        b,m=self.data();m[300].update(long_short=.9,taker_ratio=1.2,open_interest=980.);v=signal(b,m,300);self.assertIsNotNone(v)
        for x in m[301:]:x.update(long_short=9.,taker_ratio=9.,open_interest=9.)
        self.assertEqual(signal(b,m,300),v)
    def test_gap_suppresses_and_alignment(self):
        b,m=self.data();b.pop(100);m.pop(100);validate(b,m);self.assertIsNone(signal(b,m,299))
        b,m=self.data();m.pop()
        with self.assertRaises(ValueError):validate(b,m)
    def test_no_trade(self):
        b,m=self.data();self.assertEqual(backtest(b,m,0,400*STEP),[])
if __name__=='__main__':unittest.main()
