import unittest
from dataclasses import replace
from research.xrpl_dex_liquidity_replenishment_v1 import Config,DAY,STRIDE,backtest,entry_day,make_signals,summarize
def docs(idx=60_000_000,t=0,scale=1):
    h='A'*64;l=dict(validated=True,ledger_index=idx,ledger_hash=h,close_time_ms=t)
    asks=dict(validated=True,ledger_index=idx,ledger_hash=h,offers=[dict(TakerGets=str(1000_000_000*scale),TakerPays={'value':str(1000*scale)},owner_funds=str(1000_000_000*scale))])
    bids=dict(validated=True,ledger_index=idx,ledger_hash=h,offers=[dict(TakerGets={'value':str(990*scale)},TakerPays=str(1000_000_000*scale),owner_funds=str(990*scale))])
    return l,asks,bids
def bars(n=100):return [dict(timestamp=i*DAY,open=100.,high=101.,low=99.,close=100.) for i in range(n)]
class Tests(unittest.TestCase):
    def test_funded_depth_and_spread(self):
        x=summarize(*docs());self.assertAlmostEqual(x['best_ask'],1);self.assertAlmostEqual(x['best_bid'],.99);self.assertAlmostEqual(x['total_depth_xrp'],2000)
    def test_missing_funds_not_invented(self):
        l,a,b=docs();del a['offers'][0]['owner_funds'];self.assertIsNone(summarize(l,a,b))
    def test_ledger_mismatch_rejected(self):
        l,a,b=docs();b['ledger_hash']='B'*64
        with self.assertRaises(ValueError):summarize(l,a,b)
    def test_growth_cadence_and_48h_lag(self):
        a=summarize(*docs(t=1));b=summarize(*docs(60_000_000+STRIDE,3*DAY+1,2));s=make_signals([a,b]);self.assertEqual(list(s),[6*DAY]);self.assertGreaterEqual(list(s)[0]-b['timestamp'],2*DAY)
    def test_no_growth_or_gap_no_signal(self):
        a=summarize(*docs());b=summarize(*docs(60_000_000+2*STRIDE,DAY,1));self.assertFalse(make_signals([a,b]))
    def test_stop_first_and_stress(self):
        r=bars();r[30]['dex_signal']=dict(observation_timestamp=28*DAY,ledger_index=1,ledger_hash='A',spread=.01,prior_depth_xrp=1,total_depth_xrp=2,ask_depth_xrp=1,bid_depth_xrp=1);r[30].update(high=120,low=80);a,_=backtest(r,0,10**18);b,_=backtest(r,0,10**18,replace(Config(),fee=.0019,slippage=.0004));self.assertEqual(a[0]['reason'],'STOP');self.assertLess(b[0]['pnl'],a[0]['pnl'])
    def test_gap_stop_limits_nonoverlap(self):
        r=bars();s=dict(observation_timestamp=28*DAY,ledger_index=1,ledger_hash='A',spread=.01,prior_depth_xrp=1,total_depth_xrp=2,ask_depth_xrp=1,bid_depth_xrp=1);r[30]['dex_signal']=s;r[31]['dex_signal']=dict(s,observation_timestamp=29*DAY);r[31].update(open=80,high=81,low=79,close=80);t,_=backtest(r,0,10**18);self.assertEqual(len(t),1);self.assertEqual(t[0]['reason'],'GAP_STOP');self.assertLessEqual(t[0]['leg_notional'],2000+1e-8);self.assertLessEqual(t[0]['qty']*(t[0]['entry']-t[0]['stop']),50+1e-8)
if __name__=='__main__':unittest.main()
