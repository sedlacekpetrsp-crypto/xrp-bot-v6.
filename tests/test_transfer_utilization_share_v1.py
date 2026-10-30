import unittest
from dataclasses import replace
from research.transfer_utilization_share_v1 import Config,DAY,backtest,make_signals
def metric(shares):return [dict(timestamp=i*DAY,tx_count=100.,transfer_count=100*s) for i,s in enumerate(shares)]
def bars(n=50):return [dict(timestamp=i*DAY,open=100.,high=101.,low=99.,close=100.) for i in range(n)]
class Tests(unittest.TestCase):
    def test_nearest_rank_excludes_current_and_lag(self):
        c=replace(Config(),lookback=5,quantile=.8);s=make_signals(metric([.1,.2,.3,.4,.5,.4]),c);self.assertIn(7*DAY,s);self.assertEqual(s[7*DAY]['metric_timestamp'],5*DAY);self.assertAlmostEqual(s[7*DAY]['threshold'],.4)
    def test_gap_and_bad_counts_fail(self):
        r=metric([.1]*181);r[5]['timestamp']+=DAY
        with self.assertRaises(ValueError):make_signals(r)
        with self.assertRaises(ValueError):make_signals([dict(timestamp=0,tx_count=0,transfer_count=1)])
    def test_stop_first_and_cost_stress(self):
        r=bars();r[20]['transfer_share_signal']=dict(metric_timestamp=18*DAY,share=.5,threshold=.4,tx_count=100.,transfer_count=50.);r[20].update(high=120.,low=80.)
        a,_=backtest(r,0,50*DAY);b,_=backtest(r,0,50*DAY,replace(Config(),fee=.0019,slippage=.0004));self.assertEqual(a[0]['reason'],'STOP');self.assertLess(b[0]['pnl'],a[0]['pnl'])
    def test_gap_stop_limits(self):
        r=bars();r[20]['transfer_share_signal']=dict(metric_timestamp=18*DAY,share=.5,threshold=.4,tx_count=100.,transfer_count=50.);r[21].update(open=80.,high=81.,low=79.,close=80.);t,_=backtest(r,0,50*DAY);self.assertEqual(t[0]['reason'],'GAP_STOP');self.assertLessEqual(t[0]['leg_notional'],2000+1e-8);self.assertLessEqual(t[0]['qty']*(t[0]['entry']-t[0]['stop']),50+1e-8)
    def test_no_overlap_and_prefix(self):
        r=bars(70);s=dict(metric_timestamp=18*DAY,share=.5,threshold=.4,tx_count=100.,transfer_count=50.);r[20]['transfer_share_signal']=s;r[21]['transfer_share_signal']=dict(s,metric_timestamp=19*DAY);self.assertEqual(len(backtest(r,0,70*DAY)[0]),1);q=[dict(x) for x in r];q[60].update(high=1000.,close=999.);self.assertEqual(backtest(r,0,50*DAY)[0],backtest(q,0,50*DAY)[0])
if __name__=='__main__':unittest.main()
