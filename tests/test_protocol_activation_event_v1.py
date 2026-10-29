import unittest
from dataclasses import replace
from research.protocol_activation_event_v1 import Config,DAY,backtest,event_signals

def bars(n=40):
    return [dict(timestamp=i*DAY,open=100.,high=101.,low=99.,close=100.) for i in range(n)]

class TestProtocolActivation(unittest.TestCase):
    def rec(self,date='1970-01-20T12:00:00.000Z',name='A',ident='1'):
        return dict(id=ident,date=date,ledger_index=1,tx_hash='f',name=name)
    def test_strict_next_open_and_group(self):
        s=event_signals([self.rec(),self.rec('1970-01-20T13:00:00.000Z','B','2')]);g=s[20*DAY]
        self.assertEqual(g['names'],['A','B']);self.assertLess(g['latest_activation_timestamp'],20*DAY)
    def test_missing_date_is_not_invented(self):self.assertEqual(event_signals([dict(id='x',date=None,ledger_index=1,tx_hash='x')]),{})
    def test_conflicting_duplicate_fails(self):
        with self.assertRaises(ValueError):event_signals([self.rec(),self.rec(name='B')])
    def test_stop_before_target_and_cost_stress(self):
        r=bars();r[20]['activation_signal']=event_signals([self.rec()])[20*DAY];r[20].update(high=110.,low=90.)
        a,_=backtest(r,0,40*DAY);b,_=backtest(r,0,40*DAY,replace(Config(),fee=.0019,slippage=.0004))
        self.assertEqual(a[0]['reason'],'STOP');self.assertLess(b[0]['pnl'],a[0]['pnl'])
    def test_gap_stop_and_limits(self):
        r=bars();r[20]['activation_signal']=event_signals([self.rec()])[20*DAY];r[21].update(open=80.,high=81.,low=79.,close=80.)
        t,_=backtest(r,0,40*DAY);self.assertEqual(t[0]['reason'],'GAP_STOP');self.assertEqual(t[0]['raw_exit'],80.)
        self.assertLessEqual(t[0]['leg_notional'],t[0]['entry_equity']*.2+1e-9);self.assertLessEqual(t[0]['qty']*(t[0]['entry']-t[0]['stop']),t[0]['entry_equity']*.005+1e-9)
    def test_no_overlap_and_prefix_invariance(self):
        r=bars(70);s=event_signals([self.rec(),self.rec('1970-01-22T12:00:00.000Z','B','2')])
        for x in r:
            if x['timestamp'] in s:x['activation_signal']=s[x['timestamp']]
        t,_=backtest(r,0,70*DAY);self.assertEqual(len(t),1)
        q=[dict(x) for x in r];q[50].update(high=1000.,close=999.);u,_=backtest(q,0,40*DAY);v,_=backtest(r,0,40*DAY);self.assertEqual(u,v)

if __name__=='__main__':unittest.main()
