import unittest
from dataclasses import replace
from research.float_expansion_slowdown_v1 import Config,DAY,backtest,make_signals
def metric(vals):return [dict(timestamp=i*DAY,estimated_cap=v*100,current_cap=100.) for i,v in enumerate(vals)]
def bars(n=60):return [dict(timestamp=i*DAY,open=100.,high=101.,low=99.,close=100.) for i in range(n)]
class Tests(unittest.TestCase):
    def test_past_only_nearest_rank_and_lag(self):
        c=replace(Config(),change_n=1,rank_n=5,quantile=.2);s=make_signals(metric([1,2,4,7,11,16,16]),c);g=s[8*DAY];self.assertEqual(g['metric_timestamp'],6*DAY);self.assertEqual(g['change_30pp'],0);self.assertEqual(g['threshold'],100)
    def test_gap_and_bad_metric_fail(self):
        r=metric([1]*400);r[5]['timestamp']+=DAY
        with self.assertRaises(ValueError):make_signals(r)
        with self.assertRaises(ValueError):make_signals([dict(timestamp=0,estimated_cap=1,current_cap=0)])
    def test_stop_first_and_stress(self):
        r=bars();r[20]['float_signal']=dict(metric_timestamp=18*DAY,float_ratio=.5,change_30pp=.1,threshold=.2);r[20].update(high=120.,low=80.);a,_=backtest(r,0,60*DAY);b,_=backtest(r,0,60*DAY,replace(Config(),fee=.0019,slippage=.0004));self.assertEqual(a[0]['reason'],'STOP');self.assertLess(b[0]['pnl'],a[0]['pnl'])
    def test_gap_stop_limits(self):
        r=bars();r[20]['float_signal']=dict(metric_timestamp=18*DAY,float_ratio=.5,change_30pp=.1,threshold=.2);r[21].update(open=80.,high=81.,low=79.,close=80.);t,_=backtest(r,0,60*DAY);self.assertEqual(t[0]['reason'],'GAP_STOP');self.assertLessEqual(t[0]['leg_notional'],2000+1e-8);self.assertLessEqual(t[0]['qty']*(t[0]['entry']-t[0]['stop']),50+1e-8)
    def test_no_overlap_prefix(self):
        r=bars(80);s=dict(metric_timestamp=18*DAY,float_ratio=.5,change_30pp=.1,threshold=.2);r[20]['float_signal']=s;r[21]['float_signal']=dict(s,metric_timestamp=19*DAY);self.assertEqual(len(backtest(r,0,80*DAY)[0]),1);q=[dict(x) for x in r];q[70].update(high=1000.,close=999.);self.assertEqual(backtest(r,0,50*DAY)[0],backtest(q,0,50*DAY)[0])
if __name__=='__main__':unittest.main()
