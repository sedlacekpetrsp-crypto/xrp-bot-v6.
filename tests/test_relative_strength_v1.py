import unittest
from unittest.mock import patch
from dataclasses import replace
from research.relative_strength_v1 import backtest,state,validate,Config

class RelativeStrengthTests(unittest.TestCase):
    def markets(self,n=1000):
        return {s:[dict(timestamp=i*3600000,open=100.,high=100.5,low=99.5,close=100.) for i in range(n)] for s in ('XRPUSDT','BTCUSDT','ETHUSDT')}
    def run_one(self,m=None,c=Config(),end=1000*3600000,leave=None):
        m=m or self.markets()
        with patch('research.relative_strength_v1.state',side_effect=lambda m,i:(i==743,i==leave,1.)):
            return backtest(m,720*3600000,end,c)
    def test_closed_daily_signal_next_open_and_holding(self):
        ts=self.run_one();self.assertEqual(len(ts),1)
        self.assertEqual((ts[0]['signal_index'],ts[0]['entry_index'],ts[0]['exit_index']),(743,744,912))
        self.assertEqual(ts[0]['reason'],'TIME')
    def test_cost_reconciliation_and_stress(self):
        t=self.run_one()[0];c=Config();stress=self.run_one(c=replace(c,fee=c.fee*2,slippage=c.slippage*2))[0]
        self.assertAlmostEqual(t['gross']-t['fees']-t['slippage_cost'],t['pnl'])
        self.assertLess(stress['pnl'],t['pnl'])
        self.assertLessEqual(t['qty']*t['entry'],2000.000001)
        self.assertLessEqual(t['qty']*(t['entry']-t['stop']),50.000001)
    def test_gap_stop(self):
        m=self.markets();m['XRPUSDT'][750].update(open=90.,high=91.,low=89.,close=90.)
        t=self.run_one(m)[0];self.assertEqual(t['reason'],'GAP_STOP');self.assertAlmostEqual(t['exit'],90*.9998)
    def test_stop_on_entry_bar(self):
        m=self.markets();m['XRPUSDT'][744]['low']=95.
        t=self.run_one(m)[0];self.assertEqual(t['reason'],'STOP');self.assertEqual(t['exit_index'],744)
    def test_regime_exit_and_boundary(self):
        self.assertEqual(self.run_one(leave=767)[0]['exit_index'],768)
        t=self.run_one(end=800*3600000)[0]
        self.assertEqual((t['exit_index'],t['reason']),(799,'END'))
    def test_alignment_and_gap(self):
        m=self.markets();m['BTCUSDT']=m['BTCUSDT'][1:]
        with self.assertRaises(ValueError):validate(m)
        m=self.markets();m['ETHUSDT'][500]['timestamp']+=3600000
        with self.assertRaises(ValueError):validate(m)
    def test_signal_positive_and_future_invariance(self):
        m=self.markets()
        for s,rate in [('XRPUSDT',.0003),('BTCUSDT',.0001),('ETHUSDT',.0001)]:
            for i,b in enumerate(m[s]):
                p=100*(1+rate)**i;b.update(open=p,high=p+1,low=p-1,close=p)
        v=state(m,743);self.assertTrue(v[0]);self.assertFalse(v[1])
        for bars in m.values():
            for b in bars[744:]:b['close']=1e9
        self.assertEqual(state(m,743),v)
    def test_flat_no_trade(self):
        m=self.markets();self.assertEqual(backtest(m,720*3600000,1000*3600000),[])

    def test_real_gap_suppresses_signal_without_imputation(self):
        m=self.markets()
        for s in m:m[s].pop(500)
        validate(m)
        self.assertIsNone(state(m,743))
    def test_hold_uses_elapsed_time_across_gap(self):
        m=self.markets()
        for s in m:m[s].pop(800)
        t=self.run_one(m)[0]
        self.assertEqual(m['XRPUSDT'][t['exit_index']]['timestamp'],912*3600000)
