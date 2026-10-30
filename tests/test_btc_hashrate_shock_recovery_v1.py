import unittest
from dataclasses import replace
from research.btc_hashrate_shock_recovery_v1 import Config,DAY,backtest,make_signals
def metric():
    r=[dict(timestamp=i*DAY,hashrate=100.+(i%3)) for i in range(70)];r[40]['hashrate']=70.;r[41]['hashrate']=80.;return r
def bars(n=100):return [dict(timestamp=i*DAY,open=100.,high=101.,low=99.,close=100.) for i in range(n)]
class Tests(unittest.TestCase):
    def test_population_window_excludes_shock_and_current(self):
        s=make_signals(metric());x=s[43*DAY];self.assertEqual(x['prior_timestamp'],40*DAY);self.assertEqual(x['metric_timestamp'],41*DAY);self.assertAlmostEqual(x['mean30'],101.)
    def test_two_day_lag_and_future_invariance(self):
        m=metric();a=make_signals(m);m[60]['hashrate']=99999;self.assertEqual({k:v for k,v in a.items() if k<60*DAY},{k:v for k,v in make_signals(m).items() if k<60*DAY})
    def test_gap_rejected(self):
        m=metric();del m[20]
        with self.assertRaises(ValueError):make_signals(m)
    def test_recovery_required(self):
        m=metric();m[41]['hashrate']=60.;self.assertNotIn(43*DAY,make_signals(m))
    def test_stop_first_and_stress(self):
        r=bars();r[43]['hashrate_signal']=make_signals(metric())[43*DAY];r[43].update(high=120,low=80);a,_=backtest(r,0,10**18);b,_=backtest(r,0,10**18,replace(Config(),fee=.0019,slippage=.0004));self.assertEqual(a[0]['reason'],'STOP');self.assertLess(b[0]['pnl'],a[0]['pnl'])
    def test_gap_stop_sizing_and_cap(self):
        r=bars();r[43]['hashrate_signal']=make_signals(metric())[43*DAY];r[44].update(open=80,high=81,low=79,close=80);t,_=backtest(r,0,10**18);self.assertEqual(t[0]['reason'],'GAP_STOP');self.assertLessEqual(t[0]['leg_notional'],2000+1e-8);self.assertLessEqual(t[0]['qty']*(t[0]['entry']-t[0]['stop']),50+1e-8)
    def test_nonoverlap(self):
        r=bars();s=make_signals(metric())[43*DAY];r[43]['hashrate_signal']=s;r[44]['hashrate_signal']=dict(s,metric_timestamp=42*DAY);self.assertEqual(len(backtest(r,0,10**18)[0]),1)
if __name__=='__main__':unittest.main()
