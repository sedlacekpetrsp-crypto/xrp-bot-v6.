import unittest
from research.xrp_labor_resilience_v1 import DAY,SignalConfig,backtest,execution_config,make_signals
def bars(n=80,p=100.): return [{'timestamp':i*DAY,'open':p,'high':p+1,'low':p-1,'close':p} for i in range(n)]
class LaborTests(unittest.TestCase):
    def test_strict_prior_median_lag_and_trend(self):
        values=[200-i for i in range(60)]; macro=[{'timestamp':i*7*DAY,'value':v} for i,v in enumerate(values)]; s=make_signals(macro); self.assertIn(54*7*DAY,s); self.assertEqual(s[54*7*DAY]['metric_timestamp'],52*7*DAY); self.assertEqual(s[54*7*DAY]['median_start_timestamp'],0)
    def test_flat_trend_rejected(self):
        macro=[{'timestamp':i*7*DAY,'value':200} for i in range(60)]; self.assertFalse(make_signals(macro))
    def test_invalid_macro_rejected(self):
        with self.assertRaises(ValueError): make_signals([{'timestamp':0,'value':0}])
    def test_next_open_cap_and_nonoverlap(self):
        x=bars(); x[14].update(macro_signal=True,metric_timestamp=12*DAY,median_start_timestamp=0,prior_median=120,latest_claims=100,recent4_mean=100,previous4_mean=110); t,_=backtest(x,0,80*DAY,execution_config()); self.assertEqual(t[0]['entry_timestamp'],15*DAY); self.assertLessEqual(t[0]['leg_notional'],2000.000001)
    def test_gap_stop(self):
        x=bars(); x[14].update(macro_signal=True,metric_timestamp=12*DAY,median_start_timestamp=0,prior_median=120,latest_claims=100,recent4_mean=100,previous4_mean=110); x[16].update(open=90,high=101,low=89,close=100); t,_=backtest(x,0,80*DAY,execution_config()); self.assertEqual(t[0]['reason'],'GAP_STOP')
    def test_stress_worse(self):
        x=bars(); x[14].update(macro_signal=True,metric_timestamp=12*DAY,median_start_timestamp=0,prior_median=120,latest_claims=100,recent4_mean=100,previous4_mean=110); a,_=backtest(x,0,80*DAY,execution_config()); b,_=backtest(x,0,80*DAY,execution_config(2)); self.assertLess(b[0]['pnl'],a[0]['pnl'])
    def test_marked_drawdown(self):
        x=bars(); x[14].update(macro_signal=True,metric_timestamp=12*DAY,median_start_timestamp=0,prior_median=120,latest_claims=100,recent4_mean=100,previous4_mean=110); t,c=backtest(x,0,80*DAY,execution_config()); self.assertIn(t[0]['intratrade_min_equity'],[p['equity'] for p in c])
if __name__=='__main__': unittest.main()
