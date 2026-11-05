import unittest
from research.xrp_policy_uncertainty_easing_v1 import DAY,backtest,execution_config,make_signals
def bars(n=120,p=100.):return [{'timestamp':i*DAY,'open':p,'high':p+1,'low':p-1,'close':p} for i in range(n)]
def signal(row):row.update(macro_signal=True,metric_timestamp=12*DAY,window_start_timestamp=0,prior_median=120,latest_epu=100,recent5_mean=100,previous5_mean=110)
class PolicyTests(unittest.TestCase):
    def test_prior_median_lag_trend(self):
        m=[{'timestamp':i*DAY,'value':200-i} for i in range(100)];s=make_signals(m);self.assertIn(92*DAY,s);self.assertEqual(s[92*DAY]['metric_timestamp'],90*DAY)
    def test_flat_rejected(self):self.assertFalse(make_signals([{'timestamp':i*DAY,'value':100} for i in range(100)]))
    def test_invalid_rejected(self):
        with self.assertRaises(ValueError):make_signals([{'timestamp':1,'value':1},{'timestamp':0,'value':1}])
    def test_next_open_cap(self):
        x=bars();signal(x[14]);t,_=backtest(x,0,120*DAY,execution_config());self.assertEqual(t[0]['entry_timestamp'],15*DAY);self.assertLessEqual(t[0]['leg_notional'],2000.000001)
    def test_gap_stop(self):
        x=bars();signal(x[14]);x[16].update(open=90,high=101,low=89,close=100);t,_=backtest(x,0,120*DAY,execution_config());self.assertEqual(t[0]['reason'],'GAP_STOP')
    def test_stress_worse(self):
        x=bars();signal(x[14]);a,_=backtest(x,0,120*DAY,execution_config());b,_=backtest(x,0,120*DAY,execution_config(2));self.assertLess(b[0]['pnl'],a[0]['pnl'])
    def test_drawdown_marked(self):
        x=bars();signal(x[14]);t,c=backtest(x,0,120*DAY,execution_config());self.assertIn(t[0]['intratrade_min_equity'],[p['equity'] for p in c])
if __name__=='__main__':unittest.main()
