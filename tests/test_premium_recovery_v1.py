import unittest
from dataclasses import replace
from research.premium_recovery_v1 import Config,STEP,backtest,signal,validate


def data(n=40):
    bars=[dict(timestamp=i*STEP,open=1.,high=1.01,low=.99,close=1.) for i in range(n)]
    premium=[dict(timestamp=i*STEP,open=.0002,high=.0003,low=.0001,close=.0002) for i in range(n)]
    premium[30].update(open=-.002,high=-.0019,low=-.0021,close=-.002)
    premium[31].update(open=-.0019,high=-.0013,low=-.002,close=-.0014)
    return bars,premium


class Tests(unittest.TestCase):
    def config(self): return Config(window=10,quantile=.1,atr_window=4,max_hold=3)
    def test_signal_and_future_invariance(self):
        bars,premium=data(); c=self.config(); found=signal(bars,premium,31,c); self.assertIsNotNone(found)
        premium[32].update(open=.9,high=1.,low=.8,close=.9)
        self.assertEqual(found,signal(bars,premium,31,c))
    def test_gap_suppresses(self):
        bars,premium=data(); bars.pop(25); premium.pop(25)
        self.assertIsNone(signal(bars,premium,30,self.config()))
    def test_next_open_and_time(self):
        bars,premium=data(); trades=backtest(bars,premium,0,10**18,self.config()); self.assertEqual(len(trades),1)
        self.assertEqual(trades[0]['entry_index'],trades[0]['signal_index']+1); self.assertEqual(trades[0]['exit_index']-trades[0]['entry_index'],2)
    def test_gap_stop(self):
        bars,premium=data(); bars[33].update(open=.8,high=1.1,low=.7,close=.8)
        trade=backtest(bars,premium,0,10**18,self.config())[0]; self.assertEqual(trade['reason'],'GAP_STOP'); self.assertLess(trade['exit'],trade['stop'])
    def test_costs_sizing(self):
        bars,premium=data(); c=self.config(); base=backtest(bars,premium,0,10**18,c)[0]; stress=backtest(bars,premium,0,10**18,replace(c,fee=c.fee*2,slippage=c.slippage*2))[0]
        self.assertLess(stress['pnl'],base['pnl']); self.assertLessEqual(base['qty']*base['entry'],2000+1e-7); self.assertLessEqual(base['qty']*(base['entry']-base['stop']),50+1e-7)
    def test_validation(self):
        bars,premium=data(); validate(bars,premium); premium[2]['low']=2
        with self.assertRaises(ValueError): validate(bars,premium)


if __name__=='__main__': unittest.main()
