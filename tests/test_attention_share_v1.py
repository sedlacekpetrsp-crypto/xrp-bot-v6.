import unittest
from dataclasses import replace
from research.attention_share_v1 import ASSETS,Config,STEP,backtest,signal,validate
def data(n=300):
    d={a:[dict(timestamp=i*STEP,open=1.,high=1.01,low=.99,close=1.,quote_volume=100.) for i in range(n)] for a in ASSETS}
    for i in range(264,288): d['XRPUSDT'][i]['quote_volume']=1000.
    return d
class Tests(unittest.TestCase):
    def c(self): return Config(days=10,quantile=.8,max_hold=3)
    def test_signal_causal(self):
        d=data(); f=signal(d,287,self.c()); self.assertIsNotNone(f); d['XRPUSDT'][288]['quote_volume']=1e9; self.assertEqual(f,signal(d,287,self.c()))
    def test_gap_suppresses(self):
        d=data(); [v.pop(100) for v in d.values()]; self.assertIsNone(signal(d,286,self.c()))
    def test_next_open(self):
        t=backtest(data(),0,10**18,self.c())[0]; self.assertEqual(t['entry_index'],t['signal_index']+1); self.assertEqual(t['exit_index']-t['entry_index'],2)
    def test_gap_stop(self):
        d=data(); d['XRPUSDT'][289].update(open=.8,high=1.2,low=.7,close=1.); self.assertEqual(backtest(d,0,10**18,self.c())[0]['reason'],'GAP_STOP')
    def test_costs_sizing(self):
        d=data(); c=self.c(); a=backtest(d,0,10**18,c)[0]; z=backtest(d,0,10**18,replace(c,fee=c.fee*2,slippage=c.slippage*2))[0]; self.assertLess(z['pnl'],a['pnl']); self.assertLessEqual(a['qty']*a['entry'],2000+1e-6); self.assertLessEqual(a['qty']*(a['entry']-a['stop']),50+1e-6)
    def test_validation(self):
        d=data(); validate(d); d['BTCUSDT'][2]['low']=2
        with self.assertRaises(ValueError): validate(d)
if __name__=='__main__': unittest.main()
