import unittest
from dataclasses import replace
from research.btc_lead_lag_v1 import Config, backtest, signal, validate, STEP

class LeadLagTests(unittest.TestCase):
    def markets(self, n=80):
        return {s:[dict(timestamp=i*STEP, open=100., high=100.4, low=99.6, close=100.) for i in range(n)] for s in ('BTCUSDT','XRPUSDT')}

    def triggered(self):
        m=self.markets();m['BTCUSDT'][30]['close']=101.2;m['BTCUSDT'][30]['high']=101.3
        return m

    def test_closed_signal_enters_next_open_and_times_out(self):
        t=backtest(self.triggered(),0,80*STEP)[0]
        self.assertEqual((t['signal_index'],t['entry_index'],t['exit_index']),(30,31,36))
        self.assertEqual(t['reason'],'TIME')

    def test_signal_and_future_prefix_invariance(self):
        m=self.triggered();before=signal(m,30)
        self.assertIsNotNone(before)
        for bars in m.values():
            for b in bars[31:]:b.update(open=1e6,high=1e6,low=1e6,close=1e6)
        self.assertEqual(signal(m,30),before)

    def test_costs_sizing_and_stress(self):
        m=self.triggered();t=backtest(m,0,80*STEP)[0]
        stress=backtest(m,0,80*STEP,replace(Config(),fee=.0019,slippage=.0004))[0]
        self.assertAlmostEqual(t['gross']-t['fees']-t['slippage_cost'],t['pnl'])
        self.assertLess(stress['pnl'],t['pnl'])
        self.assertLessEqual(t['entry']*t['qty'],2000.000001)
        self.assertLessEqual((t['entry']-t['stop'])*t['qty'],50.000001)

    def test_stop_precedes_target_and_gap_is_worse_open(self):
        m=self.triggered();m['XRPUSDT'][31].update(high=110.,low=90.)
        self.assertEqual(backtest(m,0,80*STEP)[0]['reason'],'STOP')
        m=self.triggered();m['XRPUSDT'][32].update(open=90.,high=91.,low=89.,close=90.)
        t=backtest(m,0,80*STEP)[0]
        self.assertEqual(t['reason'],'GAP_STOP');self.assertAlmostEqual(t['exit'],90*(1-Config().slippage))

    def test_no_overlap_ignores_open_position_signal(self):
        m=self.triggered();m['BTCUSDT'][32]['close']=101.3;m['BTCUSDT'][32]['high']=101.4
        self.assertEqual(len(backtest(m,0,40*STEP)),1)

    def test_gap_suppresses_signal_without_imputation(self):
        m=self.triggered()
        for bars in m.values():bars.pop(20)
        validate(m);self.assertIsNone(signal(m,29))

    def test_alignment_and_invalid_ohlc_rejected(self):
        m=self.markets();m['BTCUSDT']=m['BTCUSDT'][1:]
        with self.assertRaises(ValueError):validate(m)
        m=self.markets();m['XRPUSDT'][2]['low']=101.
        with self.assertRaises(ValueError):validate(m)

    def test_flat_market_no_trade(self):
        self.assertEqual(backtest(self.markets(),0,80*STEP),[])

if __name__=='__main__':unittest.main()
