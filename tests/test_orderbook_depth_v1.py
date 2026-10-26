import unittest
from dataclasses import replace
from research.orderbook_depth_v1 import Config,STEP,backtest,signal,validate

def data(n=50):
    b=[dict(timestamp=i*STEP,open=1.,high=1.01,low=.99,close=1.) for i in range(n)]
    d=[dict(timestamp=i*STEP,bid_notional=1_000.,ask_notional=1_000.) for i in range(n)]
    d[31]['bid_notional']=2_000.; return b,d

class Tests(unittest.TestCase):
    def c(self): return Config(window=10,quantile=.9,atr_window=4,max_hold=3)
    def test_signal_causal(self):
        b,d=data(); found=signal(b,d,31,self.c()); self.assertIsNotNone(found); d[32]['bid_notional']=9e9; self.assertEqual(found,signal(b,d,31,self.c()))
    def test_gap_suppresses(self):
        b,d=data(); b.pop(25); d.pop(25); self.assertIsNone(signal(b,d,30,self.c()))
    def test_next_open_time(self):
        b,d=data(); t=backtest(b,d,0,10**18,self.c())[0]; self.assertEqual(t['entry_index'],t['signal_index']+1); self.assertEqual(t['exit_index']-t['entry_index'],2)
    def test_gap_stop(self):
        b,d=data(); b[33].update(open=.8,high=1.2,low=.7,close=1.); t=backtest(b,d,0,10**18,self.c())[0]; self.assertEqual(t['reason'],'GAP_STOP'); self.assertLess(t['exit'],t['stop'])
    def test_costs_sizing(self):
        b,d=data(); c=self.c(); a=backtest(b,d,0,10**18,c)[0]; z=backtest(b,d,0,10**18,replace(c,fee=c.fee*2,slippage=c.slippage*2))[0]
        self.assertLess(z['pnl'],a['pnl']); self.assertLessEqual(a['qty']*a['entry'],2000+1e-6); self.assertLessEqual(a['qty']*(a['entry']-a['stop']),50+1e-6)
    def test_validation(self):
        b,d=data(); validate(b,d); d[2]['ask_notional']=0
        with self.assertRaises(ValueError): validate(b,d)

if __name__=='__main__': unittest.main()
