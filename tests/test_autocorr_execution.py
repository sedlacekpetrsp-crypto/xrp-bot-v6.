import unittest
from unittest.mock import patch
from dataclasses import replace
from research.autocorr_regime_v1 import Config,backtest,signal

class ExecutionTests(unittest.TestCase):
    def bars(self):
        return [dict(timestamp=i*900000,open=100.,high=100.5,low=99.5,close=100.) for i in range(130)]
    def run_one(self,bars,c=Config()):
        with patch('research.autocorr_regime_v1.signal',side_effect=lambda b,i,c: (1.,'TEST') if i==97 else None):
            return backtest(bars,c)[0]
    def test_next_open_fees_and_slippage(self):
        t=self.run_one(self.bars());c=Config()
        self.assertEqual(t['entry_index'],98)
        self.assertAlmostEqual(t['entry'],100*(1+c.slippage))
        self.assertAlmostEqual(t['pnl'],t['qty']*(t['exit']-t['entry'])-c.fee*t['qty']*(t['entry']+t['exit']))
        stress=self.run_one(self.bars(),replace(c,fee=2*c.fee,slippage=2*c.slippage))
        self.assertLess(stress['pnl'],t['pnl'])
    def test_ambiguous_stop_first(self):
        b=self.bars();b[98].update(high=110.,low=90.)
        self.assertEqual(self.run_one(b)['reason'],'STOP')
    def test_gap_stop(self):
        b=self.bars();b[99].update(open=95.,high=96.,low=94.,close=95.)
        t=self.run_one(b)
        self.assertEqual(t['reason'],'GAP_STOP')
        self.assertAlmostEqual(t['exit'],95*(1-Config().slippage))
    def test_signal_prefix_invariance(self):
        b=self.bars()
        for i,v in enumerate(b):
            p=100*1.001**i;v.update(open=p,close=p,high=p*1.001,low=p*.999)
        expected=signal(b[:111],110)
        for v in b[111:]:v['close']=100000
        self.assertEqual(signal(b,110),expected)
