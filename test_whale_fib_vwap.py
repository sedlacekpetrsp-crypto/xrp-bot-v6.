import asyncio
import copy
import time
import unittest
from unittest.mock import patch, AsyncMock
import app_blue_whale_mirror as w

def row(i,c,o=None,spread=.03):
    o=c if o is None else o
    return [i*300000,o,max(c,o)+spread,min(c,o)-spread,c,10,(i+1)*300000-1]

def fib_rows(short=False):
    prices=[100.8-i*.005 for i in range(70)]+[100,100.2,100.4,100.6,100.8,101,101.2,101.4,101.6,101.8,102,101.8,101.5,101.2,100.9,100.7,100.6,100.55,100.65]
    rs=[row(i,c,c-.01) for i,c in enumerate(prices)]
    if short:
        rs=[[r[0],202-r[1],202-r[3],202-r[2],202-r[4],r[5],r[6]] for r in rs]
    return rs

class WhaleTests(unittest.TestCase):
    def setUp(self):
        self.saved=copy.deepcopy(w.state)
        w.state.update(balance=10000,equity=10000,open_positions=[],open_position=None,trades=[],seen_signal_ids=[],market_prices={'BTCUSDT':100,'ETHUSDT':200},persistence='postgres',persistence_error=None)
        self.db=patch.object(w,'DATABASE_URL',None);self.db.start()
    def tearDown(self):
        w.state.clear();w.state.update(self.saved);self.db.stop()
    def signal(self,side='LONG',symbol='BTCUSDT',sid=1):
        price=100 if symbol=='BTCUSDT' else 200
        stop=price*(.99 if side=='LONG' else 1.01)
        return dict(id=sid,text=side,side=side,symbol=symbol,strategy='FIB_618_786',entry=price,tp=price*(1.04 if side=='LONG' else .96),stop=dict(low=stop,high=stop,raw=str(stop),masked=False))
    def test_fib_long_and_short_exact_levels(self):
        for short in (False,True):
            sig,d=w.fib_candidate(fib_rows(short))
            self.assertIsNotNone(sig,d)
            self.assertEqual(sig['side'],'SHORT' if short else 'LONG')
            span=d['swing_high']-d['swing_low']
            self.assertAlmostEqual(d['fib_618'],d['swing_low']+.618*span if short else d['swing_high']-.618*span)
            self.assertAlmostEqual(d['fib_786'],d['swing_low']+.786*span if short else d['swing_high']-.786*span)
    def test_fib_no_reversal_no_trade(self):
        rs=fib_rows();rs[-1]=row(len(rs)-1,100.5,100.65)
        self.assertIsNone(w.fib_candidate(rs)[0])
    def test_fib_broken_origin_rejected(self):
        rs=fib_rows();rs[-1][3]=99
        self.assertIsNone(w.fib_candidate(rs)[0])
    def test_vwap_reentry_both_directions(self):
        rs=[row(i,99.5 if i%2 else 100.5) for i in range(70)]
        rs[-2]=row(68,97.5,98);rs[-1]=row(69,99,98.7)
        for short in (False,True):
            r=rs if not short else [[x[0],200-x[1],200-x[3],200-x[2],200-x[4],x[5],x[6]] for x in rs]
            sig,d=w.vwap_candidate(r)
            self.assertIsNotNone(sig,d)
            self.assertEqual(sig['side'],'SHORT' if short else 'LONG')
            self.assertEqual(sig['tp'],d['vwap'])
    def test_vwap_strong_trend_waits_for_pullback_instead_of_veto(self):
        rs=[row(i,100+i*.1) for i in range(70)]
        sig,d=w.vwap_candidate(rs)
        self.assertIsNone(sig)
        self.assertEqual(d['strategy'],'VWAP_TREND_PULLBACK')
        self.assertEqual(d['trend_side'],'LONG')
        self.assertIn('pullback',d['reason'])

    def test_vwap_strong_trend_pullback_long_and_short(self):
        prices=[100+i*.1 for i in range(68)]+[105.9,106.25]
        rs=[row(i,c) for i,c in enumerate(prices)]
        rs[-1]=row(69,106.25,106.05)
        for short in (False,True):
            r=rs if not short else [[x[0],212-x[1],212-x[3],212-x[2],212-x[4],x[5],x[6]] for x in rs]
            sig,d=w.vwap_candidate(r)
            self.assertIsNotNone(sig,d)
            self.assertEqual(sig['strategy'],'VWAP_TREND_PULLBACK')
            self.assertEqual(sig['side'],'SHORT' if short else 'LONG')
            self.assertEqual(d['trend_side'],sig['side'])
            if sig['side']=='LONG':
                self.assertGreater(sig['tp'],sig['entry'])
            else:
                self.assertLess(sig['tp'],sig['entry'])
    def test_live_and_stale_candles(self):
        rs=[row(i,100) for i in range(70)]
        self.assertEqual(len(w.closed_candles(rs,rs[-1][0]+1000,5)),69)
        with self.assertRaises(ValueError):w.closed_candles(rs,rs[-1][6]+700000,5)
    def test_long_short_stop_risk_includes_costs(self):
        for side in ('LONG','SHORT'):
            w.state.update(balance=10000,equity=10000,open_positions=[],trades=[])
            self.assertTrue(w.open_paper(self.signal(side),side,100))
            p=w.state['open_positions'][0]
            self.assertLessEqual(p['risk_dollars'],20)
            self.assertIn(1,w.state['seen_signal_ids'])
            w.close_paper(p,p['stop'],'SL')
            t=w.state['trades'][-1]
            self.assertLessEqual(-t['net_pnl'],20)
            self.assertAlmostEqual(w.state['balance'],10000+t['net_pnl'])
    def test_costs_reject_small_target(self):
        s=self.signal();s['tp']=100.1
        self.assertFalse(w.open_paper(s,'LONG',100))
    def test_multi_asset_mark_and_two_position_limit(self):
        self.assertTrue(w.open_paper(self.signal(),'LONG',100))
        self.assertTrue(w.open_paper(self.signal('SHORT','ETHUSDT',2),'SHORT',200))
        w.mark_to_market()
        self.assertGreater(w.state['equity'],9950)
        self.assertLess(w.state['equity'],10000)
        self.assertFalse(w.open_paper(self.signal('LONG','XRPUSDT',3),'LONG',200))
        self.assertLessEqual(sum(p['risk_dollars'] for p in w.state['open_positions']),40)
    def test_duplicate_asset_rejected(self):
        self.assertTrue(w.open_paper(self.signal(),'LONG',100))
        self.assertFalse(w.open_paper(self.signal('SHORT',sid=2),'SHORT',100))
    def test_missing_mark_does_not_invent_equity(self):
        self.assertTrue(w.open_paper(self.signal(),'LONG',100))
        w.state['market_prices']={};w.mark_to_market()
        self.assertIsNone(w.state['equity'])
    def test_persisted_payload_keeps_history_and_tags(self):
        w.state['trades']=[dict(signal_id=5,net_pnl=-58.93,strategy='LEGACY_TELEGRAM')]
        w.state['balance']=9941.07
        self.assertTrue(w.open_paper(self.signal(),'LONG',100))
        payload=w._persistent_payload()
        self.assertEqual(payload['trades'][0]['net_pnl'],-58.93)
        self.assertEqual(payload['open_positions'][0]['strategy'],'FIB_618_786')
        self.assertEqual(payload['seen_signal_ids'],[1])
    def test_scanner_opens_once_and_rejects_unavailable_persistence(self):
        class Response:
            def json(self):return {'price':'100'}
        candidate=dict(side='LONG',entry=100,stop=99,tp=104,key='test-swing',strategy='FIB_618_786',confirmation={})
        with patch.object(w,'SYMBOLS',('BTCUSDT',)), patch.object(w,'market_get',new=AsyncMock(return_value=Response())), patch.object(w,'closed_candles',return_value=[]), patch.object(w,'fib_candidate',side_effect=lambda _: (copy.deepcopy(candidate),{'strategy':'FIB_618_786','reason':'ready'})), patch.object(w,'vwap_candidate',return_value=(None,{'strategy':'VWAP_REVERSION','reason':'waiting'})):
            asyncio.run(w.scan_entries(None))
            self.assertEqual(len(w.state['open_positions']),1)
            p=w.state['open_positions'][0]
            w.close_paper(p,100,'TEST')
            asyncio.run(w.scan_entries(None))
            self.assertEqual(w.state['open_positions'],[])
            self.assertIn('již',w.state['signal_checks'][0]['reason'])
            w.state['seen_signal_ids']=[];w.state['persistence_error']='db unavailable'
            asyncio.run(w.scan_entries(None))
            self.assertEqual(w.state['open_positions'],[])
            self.assertIn('ukládání',w.state['signal_checks'][0]['reason'])

if __name__=='__main__':unittest.main()
