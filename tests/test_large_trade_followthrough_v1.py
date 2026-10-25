import unittest
from dataclasses import replace
from unittest.mock import patch
from research.large_trade_followthrough_v1 import *
class Tests(unittest.TestCase):
    def bars(self,n=220):return [dict(timestamp=i*STEP,open=100.,high=100.5,low=99.5,close=100.,quote_volume=10000.+i,trades=100.) for i in range(n)]
    def run_one(self,b=None,c=Config()):
        b=b or self.bars()
        with patch('research.large_trade_followthrough_v1.signal',side_effect=lambda b,i,c:dict(atr=1.,size_z=3.) if i==170 else None):return backtest(b,0,220*STEP,c)
    def test_next_open_time_exit(self):
        t=self.run_one()[0];self.assertEqual((t['signal_index'],t['entry_index'],t['exit_index']),(170,171,178))
    def test_cost_stress_sizing(self):
        t=self.run_one()[0];s=self.run_one(c=replace(Config(),fee=.0019,slippage=.0004))[0]
        self.assertAlmostEqual(t['gross']-t['fees']-t['slippage_cost'],t['pnl']);self.assertLess(s['pnl'],t['pnl']);self.assertLessEqual(t['entry']*t['qty'],2000.0001);self.assertLessEqual((t['entry']-t['stop'])*t['qty'],50.0001)
    def test_stop_priority_gap(self):
        b=self.bars();b[171].update(high=110.,low=90.);self.assertEqual(self.run_one(b)[0]['reason'],'STOP')
        b=self.bars();b[172].update(open=90.,high=91.,low=89.,close=90.);self.assertEqual(self.run_one(b)[0]['reason'],'GAP_STOP')
    def test_real_signal_and_future_invariance(self):
        b=self.bars();b[168].update(close=100.5,high=100.55,quote_volume=100000.)
        v=signal(b,168);self.assertIsNotNone(v)
        for x in b[169:]:x['quote_volume']=1e12;x['close']=1e6
        self.assertEqual(signal(b,168),v)
    def test_invalid_and_gap(self):
        b=self.bars();b[2]['trades']=0
        with self.assertRaises(ValueError):validate(b)
        b=self.bars();b.pop(100);validate(b);self.assertIsNone(signal(b,168))
    def test_no_trade(self):self.assertEqual(backtest(self.bars(),0,220*STEP),[])
if __name__=='__main__':unittest.main()
