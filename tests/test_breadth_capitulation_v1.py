import unittest
from dataclasses import replace

from research.breadth_capitulation_v1 import Config, STEP, backtest, signal, validate_series


def market(n=80, falling=False):
    out=[]
    for i in range(n):
        close=1.0 if not falling or i < 24 else 1.0-0.005*(i-23)
        out.append(dict(timestamp=i*STEP,open=close,high=close+0.01,low=close-0.01,close=close))
    return out


class Tests(unittest.TestCase):
    def config(self):
        return Config(lookback=3,members_down=2,member_drop=-0.01,median_drop=-0.01,xrp_drop=-0.01,atr_window=4,max_hold=3)

    def setup_data(self):
        xrp=market(falling=True)
        basket={s:market(falling=True) for s in ('A','B','C')}
        return xrp,basket

    def test_causal_signal_and_prefix_invariance(self):
        xrp,basket=self.setup_data(); c=self.config(); i=30
        maps={s:{b['timestamp']:b['close'] for b in bars} for s,bars in basket.items()}
        first=signal(xrp,maps,i,c); self.assertIsNotNone(first)
        for bars in basket.values(): bars[i+1]['close']=99
        future_changed={s:{b['timestamp']:b['close'] for b in bars} for s,bars in basket.items()}
        self.assertEqual(first,signal(xrp,future_changed,i,c))

    def test_missing_member_suppresses(self):
        xrp,basket=self.setup_data(); c=self.config(); i=30
        basket['A']=[b for b in basket['A'] if b['timestamp']!=xrp[i]['timestamp']]
        maps={s:{b['timestamp']:b['close'] for b in bars} for s,bars in basket.items()}
        self.assertIsNone(signal(xrp,maps,i,c))

    def test_next_open_and_no_overlap(self):
        xrp,basket=self.setup_data(); trades=backtest(xrp,basket,0,10**18,self.config())
        self.assertTrue(trades)
        for t in trades: self.assertEqual(t['entry_index'],t['signal_index']+1)
        for a,b in zip(trades,trades[1:]): self.assertGreater(b['entry_index'],a['exit_index'])

    def test_stop_first_and_gap(self):
        xrp,basket=self.setup_data(); c=self.config(); i=30
        xrp[i+2].update(open=.70,high=1.2,low=.6,close=.7)
        trade=backtest(xrp,basket,xrp[i+1]['timestamp'],xrp[i+5]['timestamp'],c)[0]
        self.assertEqual(trade['reason'],'GAP_STOP')
        self.assertLess(trade['exit'],trade['stop'])

    def test_costs_and_sizing(self):
        xrp,basket=self.setup_data(); c=self.config()
        base=backtest(xrp,basket,0,10**18,c)[0]
        stress=backtest(xrp,basket,0,10**18,replace(c,fee=c.fee*2,slippage=c.slippage*2))[0]
        self.assertLess(stress['pnl'],base['pnl'])
        self.assertLessEqual(base['qty']*base['entry'],2000+1e-7)
        self.assertLessEqual(base['qty']*(base['entry']-base['stop']),50+1e-7)

    def test_validation(self):
        bars=market(); validate_series(bars); bars[2]['low']=2
        with self.assertRaises(ValueError): validate_series(bars)


if __name__ == '__main__': unittest.main()
