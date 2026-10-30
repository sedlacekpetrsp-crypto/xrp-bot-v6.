import datetime as dt,math,unittest
from dataclasses import replace
from research.weekly_inverse_vol_basket_v1 import Config,DAY,backtest,capped_inverse_vol_weights,features,validate_markets

def markets(days=100,gap=False):
    start=int(dt.datetime(2021,1,1,tzinfo=dt.timezone.utc).timestamp()*1000);out={}
    for n,s in enumerate(('BTCUSDT','ETHUSDT','XRPUSDT'),1):
        rows=[];price=100.0
        for i in range(days):
            move=(.002*n if i%3 else -.001*n);op=price;cl=price*(1+move);rows.append(dict(timestamp=start+i*DAY,open=op,high=max(op,cl)*1.01,low=min(op,cl)*.99,close=cl));price=cl
        out[s]=rows
    if gap:out['ETHUSDT'].pop(40)
    return out

class BasketTests(unittest.TestCase):
    def test_inverse_weights_sum_and_cap(self):
        w=capped_inverse_vol_weights({'a':.1,'b':.3,'c':.5},.5);self.assertAlmostEqual(sum(w.values()),1);self.assertEqual(w['a'],.5);self.assertTrue(max(w.values())<=.5)
    def test_features_are_strictly_past_only(self):
        m=markets();a=features(m,40);m['BTCUSDT'][40]['close']*=20;b=features(m,40);self.assertEqual(a,b)
    def test_gap_rejected(self):
        with self.assertRaises(ValueError):validate_markets(markets(gap=True))
    def test_three_overlapping_sleeves_and_no_symbol_overlap(self):
        m=markets();t,curve,_=backtest(m,m['BTCUSDT'][31]['timestamp'],m['BTCUSDT'][-1]['timestamp']+DAY)
        self.assertTrue(t);self.assertLessEqual(max(x['positions'] for x in curve),3)
        for s in m:
            q=sorted([x for x in t if x['symbol']==s],key=lambda x:x['entry_timestamp'])
            self.assertTrue(all(a['exit_timestamp']<=b['entry_timestamp'] for a,b in zip(q,q[1:])))
        self.assertTrue(all(x['target_weight']<=.5+1e-12 for x in t))
    def test_gap_stop_uses_worse_open(self):
        m=markets();c=Config(stop_atr=1.0);t,_,_=backtest(m,m['BTCUSDT'][31]['timestamp'],m['BTCUSDT'][-1]['timestamp']+DAY,c)
        entry=t[0];j=next(i for i,b in enumerate(m[entry['symbol']]) if b['timestamp']==entry['entry_timestamp'])
        # A deterministic direct rerun with the following open below its frozen stop.
        m=markets();probe=features(m,j,c);self.assertIsNotNone(probe)
        for s in m:m[s][j+1]['open']=m[s][j+1]['low']=1.0
        t,_,_=backtest(m,m['BTCUSDT'][j]['timestamp'],m['BTCUSDT'][j+2]['timestamp'],c)
        self.assertTrue(any(x['exit_reason']=='gap_stop' and x['exit_raw']==1.0 for x in t))
    def test_pnl_and_fees_identity(self):
        m=markets();t,_,_=backtest(m,m['BTCUSDT'][31]['timestamp'],m['BTCUSDT'][-1]['timestamp']+DAY)
        for x in t:self.assertAlmostEqual(x['pnl'],x['qty']*(x['exit_fill']-x['entry_fill'])-x['fees'],9)
    def test_double_cost_cannot_improve_same_path(self):
        m=markets();start=m['BTCUSDT'][31]['timestamp'];end=m['BTCUSDT'][-1]['timestamp']+DAY
        a,_,_=backtest(m,start,end,Config(stop_atr=100));b,_,_=backtest(m,start,end,replace(Config(stop_atr=100),fee=.0019,slippage=.0004))
        self.assertEqual([(x['entry_timestamp'],x['exit_timestamp'],x['symbol']) for x in a],[(x['entry_timestamp'],x['exit_timestamp'],x['symbol']) for x in b])
        self.assertLess(sum(x['pnl'] for x in b),sum(x['pnl'] for x in a))

if __name__=='__main__':unittest.main()
