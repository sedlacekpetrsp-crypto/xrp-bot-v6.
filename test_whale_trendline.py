import asyncio
import copy
import time
import unittest
from datetime import timedelta
from unittest.mock import AsyncMock, patch
import whale_trendline as t
import app_blue_whale_mirror as w


def candles():
    end=int(time.time()*1000)//14400000*14400000
    rows=[]
    for i in range(240):
        line=100+i*.01
        rows.append([end+(i-240)*14400000,line+1.4,line+1.7,line+1.3,line+1.5,10,end+(i-239)*14400000-1])
    for i in (180,210):rows[i][3]=100+i*.01
    rows[-1][1]=102.49;rows[-1][2]=103;rows[-1][3]=102.40;rows[-1][4]=102.9
    return rows

class TrendlineTests(unittest.TestCase):
    def setUp(self):
        self.saved=copy.deepcopy(w.state)
        w.state.update(balance=10000,equity=10000,open_positions=[],open_position=None,trades=[],seen_signal_ids=[],trendline_seen_keys=[],trendline_last_candle=None,market_prices={'XRPUSDT':100},persistence='postgres',persistence_error=None)
        self.db=patch.object(w,'DATABASE_URL',None);self.db.start()
    def tearDown(self):
        w.state.clear();w.state.update(self.saved);self.db.stop()
    def signal(self, stop=96):
        return dict(id=42,text='LONG',side='LONG',symbol='XRPUSDT',strategy=t.STRATEGY,entry=100,tp=108,stop=dict(low=stop,high=stop,raw=str(stop),masked=False))
    def test_confirmed_rising_support(self):
        rs=candles();s,d=t.candidate(rs)
        self.assertIsNotNone(s,d)
        self.assertAlmostEqual(d['support'],102.39)
        self.assertAlmostEqual(s['entry']-s['stop'],2*d['atr'])
        self.assertIn(str(rs[180][0]),s['key'])
        self.assertIsNone(t.candidate(rs[:-1])[0])
    def test_broken_support_and_unconfirmed_pivots_rejected(self):
        rs=candles();rs[220][4]=99
        self.assertIsNone(t.candidate(rs)[0])
        rs=candles();rs[210][3]=103.4
        rs[-3][3]=101 # two right-hand candles: cannot become a confirmed anchor
        self.assertIsNone(t.candidate(rs)[0])
    def test_3_percent_risk_including_costs_and_2r_target(self):
        self.assertTrue(w.open_paper(self.signal(),'LONG',100))
        p=w.state['open_positions'][0]
        self.assertAlmostEqual(p['risk_dollars'],300)
        self.assertAlmostEqual(p['actual_risk_rate'],.03)
        self.assertAlmostEqual(p['tp']-p['entry'],2*(p['entry']-p['stop']))
        w.close_paper(p,p['stop'],'SL')
        self.assertLessEqual(-w.state['trades'][0]['net_pnl'],300)
        self.assertAlmostEqual(w.state['balance'],10000+w.state['trades'][0]['net_pnl'])
    def test_no_leverage_and_symbol_guard(self):
        self.assertTrue(w.open_paper(self.signal(99),'LONG',100))
        p=w.state['open_positions'][0]
        self.assertLessEqual(p['notional'],10000)
        self.assertLess(p['actual_risk_rate'],.03)
        self.assertFalse(w.open_paper(self.signal(),'SHORT',100))
    def test_legacy_risk_and_history_unchanged(self):
        s=self.signal(99);s['strategy']='FIB_618_786'
        w.state['trades']=[dict(signal_id=1,strategy='LEGACY_TELEGRAM',net_pnl=-30)]
        self.assertTrue(w.open_paper(s,'LONG',100))
        self.assertLessEqual(w.state['open_positions'][0]['risk_dollars'],12)
        self.assertEqual(t.snapshot(w.state)['trades'],0)
        self.assertIsNone(t.snapshot(w.state)['win_rate'])
        self.assertEqual(w._persistent_payload()['trades'][0]['net_pnl'],-30)
    def test_scan_uses_fresh_closed_candle_and_persists_dedup(self):
        rows=candles();cand,diag=t.candidate(rows)
        class Response:
            def json(self):return {'price':cand['entry']}
        now=(rows[-1][6]+60001)/1000
        with patch.object(w,'market_get',AsyncMock(return_value=Response())), patch.object(w,'closed_candles',return_value=rows), patch.object(w.time,'time',return_value=now):
            first=asyncio.run(w.scan_trendline(None))
            self.assertIn('Obchod otevřen',first['reason'])
            self.assertEqual(len(w.state['open_positions']),1)
            second=asyncio.run(w.scan_trendline(None))
            self.assertIn('vyhodnocen',second['reason'])
            self.assertEqual(len(w.state['open_positions']),1)
            self.assertEqual(w._persistent_payload()['trendline_seen_keys'],[cand['key']])
    def test_stale_signal_and_db_failure_no_entry(self):
        rows=candles()
        class Response:
            def json(self):return rows
        with patch.object(w,'market_get',AsyncMock(return_value=Response())), patch.object(w,'closed_candles',return_value=rows), patch.object(w.time,'time',return_value=(rows[-1][6]+600001)/1000):
            self.assertIn('starší',asyncio.run(w.scan_trendline(None))['reason'])
            self.assertFalse(w.state['open_positions'])
        w.state['persistence_error']='unavailable'
        with patch.object(w,'market_get',AsyncMock(return_value=Response())), patch.object(w,'closed_candles',return_value=rows), patch.object(w.time,'time',return_value=(rows[-1][6]+60001)/1000):
            self.assertIn('ukládání',asyncio.run(w.scan_trendline(None))['reason'])
            self.assertFalse(w.state['open_positions'])
    def test_no_time_exit_or_breakeven_for_trendline(self):
        self.assertTrue(w.open_paper(self.signal(),'LONG',100))
        pos=w.state['open_positions'][0];pos['opened_at']=(w.utcnow()-timedelta(days=7)).isoformat()
        old_stop=pos['stop']
        class Response:
            def json(self):return {'price':106}
        async def sleep(seconds):
            if seconds==w.SCAN_SECONDS:raise asyncio.CancelledError()
        with patch.object(w,'market_get',AsyncMock(return_value=Response())), patch.object(w,'scan_entries',AsyncMock()),patch.object(w.asyncio,'sleep',sleep), patch.object(w.httpx,'AsyncClient',return_value=AsyncMock()):
            with self.assertRaises(asyncio.CancelledError):asyncio.run(w.bot_loop())
        self.assertEqual(len(w.state['open_positions']),1)
        self.assertEqual(pos['stop'],old_stop)
        self.assertFalse(pos['breakeven'])

if __name__=='__main__':unittest.main()
