import math,unittest
from dataclasses import replace
from research.btc_variance_risk_premium_v1 import Config,DAY,backtest,make_signals
def bars(n=80,step=0.):
    out=[]
    for i in range(n):
        c=100*math.exp(step*i);out.append(dict(timestamp=i*DAY,open=c,high=c*1.01,low=c*.99,close=c))
    return out
class Tests(unittest.TestCase):
    def test_population_rv_and_two_day_lag(self):
        b=bars(step=.01);d=[dict(timestamp=x['timestamp'],close=50.) for x in b];s=make_signals(d,b,replace(Config(),premium_min=1.));g=s[22*DAY]
        self.assertEqual(g['metric_timestamp'],20*DAY);self.assertAlmostEqual(g['rv20'],0.,10)
    def test_gap_suppresses_lookback(self):
        b=bars();d=[dict(timestamp=x['timestamp'],close=50.) for x in b];del b[10];self.assertNotIn(22*DAY,make_signals(d,b))
    def test_threshold_is_inclusive(self):
        b=bars();d=[dict(timestamp=x['timestamp'],close=15.) for x in b];self.assertIn(22*DAY,make_signals(d,b))
    def test_stop_first_and_stress(self):
        r=bars();r[30]['vrp_signal']=dict(metric_timestamp=28*DAY,dvol_close=50.,rv20=20.,premium=30.);r[30].update(high=120.,low=80.)
        a,_=backtest(r,0,80*DAY);b,_=backtest(r,0,80*DAY,replace(Config(),fee=.0019,slippage=.0004));self.assertEqual(a[0]['reason'],'STOP');self.assertLess(b[0]['pnl'],a[0]['pnl'])
    def test_gap_stop_sizing_and_cap(self):
        r=bars();r[30]['vrp_signal']=dict(metric_timestamp=28*DAY,dvol_close=50.,rv20=20.,premium=30.);r[31].update(open=80.,high=81.,low=79.,close=80.)
        t,_=backtest(r,0,80*DAY);self.assertEqual(t[0]['reason'],'GAP_STOP');self.assertLessEqual(t[0]['leg_notional'],2000+1e-8);self.assertLessEqual(t[0]['qty']*(t[0]['entry']-t[0]['stop']),50+1e-8)
    def test_no_overlap_and_future_prefix(self):
        r=bars();sig=dict(metric_timestamp=28*DAY,dvol_close=50.,rv20=20.,premium=30.);r[30]['vrp_signal']=sig;r[31]['vrp_signal']=dict(sig,metric_timestamp=29*DAY)
        t,_=backtest(r,0,80*DAY);self.assertEqual(len(t),1);q=[dict(x) for x in r];q[70].update(high=999.,close=900.);self.assertEqual(backtest(r,0,50*DAY)[0],backtest(q,0,50*DAY)[0])
if __name__=='__main__':unittest.main()
