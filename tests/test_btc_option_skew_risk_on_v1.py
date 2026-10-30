import datetime as dt,math,unittest
from dataclasses import replace
from research.btc_option_skew_risk_on_v1 import Config,DAY,backtest,option_trade,skew_observation
UTC=dt.timezone.utc
def friday():return int(dt.datetime(2024,6,14,tzinfo=UTC).timestamp()*1000)
def raw(side,iv,trade_id,strike):return dict(trade_id=str(trade_id),timestamp=friday()+12*3_600_000,iv=iv,index_price=65000,amount=.3,instrument_name=f'BTC-26JUL24-{strike}-{side}')
def obs(call=70,put=60):return skew_observation([raw('C',call,i,75000) for i in range(5)]+[raw('P',put,10+i,57500) for i in range(5)],friday())
def bars(n=80):
    start=friday()+3*DAY-30*DAY;return [dict(timestamp=start+i*DAY,open=100.,high=101.,low=99.,close=100.) for i in range(n)]
class Tests(unittest.TestCase):
    def test_delta_and_maturity_band(self):
        self.assertGreater(option_trade(raw('C',60,1,75000))['delta'],0);self.assertLess(option_trade(raw('P',60,2,57500))['delta'],0)
    def test_median_positive_skew_and_monday_lag(self):
        x=obs();self.assertTrue(x['eligible'] and x['signal']);self.assertEqual(x['risk_reversal'],10);self.assertEqual(x['entry_timestamp'],friday()+3*DAY);self.assertLess(x['window_end'],x['entry_timestamp'])
    def test_insufficient_side_is_not_imputed(self):
        x=skew_observation([raw('C',60,i,75000) for i in range(5)],friday());self.assertFalse(x['eligible']);self.assertNotIn('signal',x)
    def test_deduplication(self):
        a=[raw('C',70,i,75000) for i in range(5)]+[raw('P',60,10+i,57500) for i in range(5)];self.assertEqual(skew_observation(a+a,friday())['raw_trades'],10)
    def test_stop_first_and_cost_stress(self):
        r=bars();i=30;r[i]['skew_signal']=obs();r[i].update(high=120,low=80);a,_=backtest(r,0,10**18);b,_=backtest(r,0,10**18,replace(Config(),fee=.0019,slippage=.0004));self.assertEqual(a[0]['reason'],'STOP');self.assertLess(b[0]['pnl'],a[0]['pnl'])
    def test_gap_stop_and_limits(self):
        r=bars();i=30;r[i]['skew_signal']=obs();r[i+1].update(open=80,high=81,low=79,close=80);t,_=backtest(r,0,10**18);self.assertEqual(t[0]['reason'],'GAP_STOP');self.assertLessEqual(t[0]['leg_notional'],2000+1e-8);self.assertLessEqual(t[0]['qty']*(t[0]['entry']-t[0]['stop']),50+1e-8)
    def test_nonoverlap_and_future_invariance(self):
        r=bars();r[30]['skew_signal']=obs();r[31]['skew_signal']=dict(obs(),entry_timestamp=r[31]['timestamp']);a=backtest(r,0,r[50]['timestamp'])[0];q=[dict(x) for x in r];q[70].update(high=901,close=900);self.assertEqual(a,backtest(q,0,q[50]['timestamp'])[0]);self.assertEqual(len(a),1)
if __name__=='__main__':unittest.main()
