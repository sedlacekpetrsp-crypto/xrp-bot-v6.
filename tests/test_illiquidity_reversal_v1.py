import unittest
from dataclasses import replace
from research.illiquidity_reversal_v1 import Config,STEP,backtest,signal,validate

def data(n=50):
    bars=[dict(timestamp=i*STEP,open=1.,high=1.01,low=.99,close=1.,quote_volume=1_000_000.) for i in range(n)]
    bars[31].update(open=1.,high=1.,low=.97,close=.98,quote_volume=100.)
    return bars

class Tests(unittest.TestCase):
    def config(self): return Config(window=10,quantile=.9,atr_window=4,max_hold=3)
    def test_signal_is_causal(self):
        b=data(); found=signal(b,31,self.config()); self.assertIsNotNone(found); b[32]['close']=9.; self.assertEqual(found,signal(b,31,self.config()))
    def test_gap_suppresses(self):
        b=data(); b.pop(25); self.assertIsNone(signal(b,30,self.config()))
    def test_next_open_and_time(self):
        t=backtest(data(),0,10**18,self.config())[0]; self.assertEqual(t['entry_index'],t['signal_index']+1); self.assertEqual(t['exit_index']-t['entry_index'],2)
    def test_gap_stop_and_ambiguity(self):
        b=data(); b[33].update(open=.8,high=1.2,low=.7,close=1.); t=backtest(b,0,10**18,self.config())[0]; self.assertEqual(t['reason'],'GAP_STOP'); self.assertLess(t['exit'],t['stop'])
    def test_costs_and_sizing(self):
        c=self.config(); base=backtest(data(),0,10**18,c)[0]; stress=backtest(data(),0,10**18,replace(c,fee=c.fee*2,slippage=c.slippage*2))[0]
        self.assertLess(stress['pnl'],base['pnl']); self.assertLessEqual(base['qty']*base['entry'],2000+1e-6); self.assertLessEqual(base['qty']*(base['entry']-base['stop']),50+1e-6)
    def test_validation(self):
        b=data(); validate(b); b[2]['quote_volume']=0
        with self.assertRaises(ValueError): validate(b)

if __name__=='__main__': unittest.main()
