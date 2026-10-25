import unittest
from dataclasses import replace

from research.funding_reversal_v1 import Config, STEP, backtest, funding_signal, validate


def bars(n=130, price=1.0):
    return [dict(timestamp=i*STEP, open=price, high=price+0.01, low=price-0.01, close=price) for i in range(n)]


def funding(n=16, interval=8):
    return [dict(timestamp=i*interval*STEP, rate=-0.001 if i == n-1 else 0.0001, interval_hours=interval) for i in range(n)]


class Tests(unittest.TestCase):
    def test_causal_quantile_signal(self):
        f = funding()
        c = Config(funding_window=10)
        self.assertIsNotNone(funding_signal(f, len(f)-1, c))
        altered = [dict(x) for x in f]
        altered.append(dict(timestamp=altered[-1]['timestamp']+8*STEP, rate=9.0, interval_hours=8))
        self.assertEqual(funding_signal(f, len(f)-1, c), funding_signal(altered, len(f)-1, c))

    def test_gap_suppresses_signal(self):
        f = funding()
        f[-2]['timestamp'] += STEP
        self.assertIsNone(funding_signal(f, len(f)-1, Config(funding_window=10)))

    def test_next_open_and_time_exit(self):
        b = bars()
        f = funding()
        c = Config(funding_window=10, atr_window=4, max_hold=3)
        trades = backtest(b, f, 0, 10**18, c)
        self.assertEqual(len(trades), 1)
        self.assertEqual(b[trades[0]['entry_index']]['timestamp'], f[-1]['timestamp']+STEP)
        self.assertEqual(trades[0]['exit_index']-trades[0]['entry_index'], 2)

    def test_stop_priority_and_gap(self):
        b = bars(); f = funding(); c = Config(funding_window=10, atr_window=4)
        ei = int(f[-1]['timestamp']/STEP)+1
        b[ei+1]['open']=b[ei+1]['close']=0.90; b[ei+1]['high']=1.2; b[ei+1]['low']=0.8
        t=backtest(b,f,0,10**18,c)[0]
        self.assertEqual(t['reason'],'GAP_STOP')
        self.assertLess(t['exit'], t['stop'])

    def test_cost_stress_and_sizing(self):
        b=bars(); f=funding(); c=Config(funding_window=10,atr_window=4)
        base=backtest(b,f,0,10**18,c)[0]
        stress=backtest(b,f,0,10**18,replace(c,fee=c.fee*2,slippage=c.slippage*2))[0]
        self.assertLess(stress['pnl'],base['pnl'])
        self.assertLessEqual(base['qty']*base['entry'],2000+1e-7)
        self.assertLessEqual(base['qty']*(base['entry']-base['stop']),50+1e-7)

    def test_validation(self):
        b=bars(); f=funding(); validate(b,f)
        b[2]['low']=2
        with self.assertRaises(ValueError): validate(b,f)


if __name__ == '__main__': unittest.main()
