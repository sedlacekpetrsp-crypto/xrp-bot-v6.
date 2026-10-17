import asyncio
import copy
import gzip
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import httpx
import app_v8 as core
import fast_scalper as live_fast
import lead_lag_scalper as live_lead
import v8_fly_layer as live_fly
import research_market_evidence as r

NOW = 1792215000000


def candles(interval, count=250):
    step = {'1m':60000,'5m':300000}[interval]
    end = NOW//step*step
    return [[end+(i-count+1)*step,100,101,99,100,10,end+(i-count+2)*step-1] for i in range(count)]


def bundle():
    return dict(started_at='2026-10-17T05:30:00+00:00',finished_at='2026-10-17T05:30:10+00:00',
        frames={s+':'+i:dict(data=candles(i,n)) for s,i,n in r.FRAMES},
        books={s:dict(data=dict(bids=[['99.99','10']],asks=[['100.01','10']])) for s in r.SYMBOLS},
        quotes={s:dict(data=dict(price='100')) for s in r.SYMBOLS},
        news={s:dict(status='running',checked_at='2026-10-17T05:29:00Z',bullish=False,bearish=False,score=0) for s in r.SYMBOLS},
        errors={},quality=dict(inputs_complete=True,synchronized=True,news_ready=True))


class IsolationTests(unittest.IsolatedAsyncioTestCase):
    async def test_full_wait_and_rejections_observed_without_live_state_or_inputs_changing(self):
        core_before=(copy.deepcopy(core.trade_history),core.paper_position)
        fast_before=copy.deepcopy(live_fast.state)
        lead_before=copy.deepcopy(live_lead.state)
        fly_binding=getattr(live_fly,'m',None)
        observer=r.SignalObserver(core)
        source=bundle();before=copy.deepcopy(source)
        results=await observer.evaluate(source)
        self.assertEqual(results['errors'],{})
        self.assertEqual(len(results['fly']),3)
        self.assertEqual(len(results['fast']),3)
        self.assertEqual(results['leadlag']['signal'],'WAIT')
        self.assertTrue(all(x['fast_signal']=='WAIT' and x['fast_blockers'] for x in results['fast']))
        self.assertEqual(source,before)
        self.assertEqual(core_before,(core.trade_history,core.paper_position))
        self.assertEqual(live_fast.state,fast_before)
        self.assertEqual(live_lead.state,lead_before)
        self.assertIs(getattr(live_fly,'m',None),fly_binding)
        for name in ('DATABASE_URL','open_trade','close_trade','save_trade','get_live_price','app','http_client'):
            self.assertFalse(hasattr(observer.core,name),name)

    async def test_incomplete_inputs_mark_errors_never_assume_neutral_book(self):
        sample=bundle();del sample['books']['XRPUSDC']
        result=await r.SignalObserver(core).evaluate(sample)
        self.assertIn('XRPUSDC',result['errors'])
        self.assertIn('LEADLAG',result['errors'])
        self.assertNotIn('XRPUSDC',[x['symbol'] for x in result['fly']])

    async def test_missing_leader_is_visible_not_silently_eligible(self):
        sample=bundle();del sample['frames']['BTCUSDT:1m']
        result=await r.SignalObserver(core).evaluate(sample)
        self.assertIsNone(result['leadlag'])
        self.assertIn('LEADLAG',result['errors'])

    def test_context_allowlist_excludes_secrets_and_identifies_source_and_config(self):
        with patch.object(core,'DATABASE_URL','DO_NOT_ARCHIVE_THIS'):
            observer=r.SignalObserver(core);context=observer.context()
        encoded=r.json_bytes(context)
        self.assertNotIn(b'DO_NOT_ARCHIVE_THIS',encoded)
        self.assertEqual(context['constants']['ROUND_TRIP_COST'],core.ROUND_TRIP_COST)
        self.assertEqual(len(context['source_hashes']['v8_fly_layer.py']),64)


class QualityTests(unittest.TestCase):
    def test_reject_invalid_or_crossed_books(self):
        valid=dict(bids=[['100','2'],['99','3']],asks=[['101','2'],['102','3']])
        r.validate_book(valid)
        for bad in (dict(bids=[],asks=valid['asks']),
                    dict(bids=[['102','2']],asks=valid['asks']),
                    dict(bids=list(reversed(valid['bids'])),asks=valid['asks']),
                    dict(bids=[['100','NaN']],asks=valid['asks'])):
            with self.assertRaises(ValueError):r.validate_book(bad)

    def test_reject_gaps_future_and_insufficient_frames(self):
        rows=candles('1m');r.validate_frame(rows,'1m',NOW,200)
        gap=copy.deepcopy(rows);del gap[5]
        future=copy.deepcopy(rows);future[-1][0]+=60000;future[-1][6]+=60000
        for bad in (gap,future,rows[:100]):
            with self.assertRaises(ValueError):r.validate_frame(bad,'1m',NOW,200)

    def test_nonfinite_values_cannot_be_archived_as_valid_json(self):
        with self.assertRaises(ValueError):r.json_bytes({'price':float('nan')})


class CaptureTests(unittest.IsolatedAsyncioTestCase):
    async def test_public_request_set_bounded_and_failure_visible(self):
        requests=[]
        async def request(client,url,params,timeout):
            requests.append((url,params))
            if url.endswith('/depth'):
                if params['symbol']=='SOLUSDC':raise RuntimeError('unavailable')
                data=bundle()['books'][params['symbol']]['data']
            elif url.endswith('/price'):data={'price':'100'}
            else:data=candles(params['interval'],params['limit'])
            return httpx.Response(200,json=data,request=httpx.Request('GET',url))
        with patch.object(r.time,'time',return_value=NOW/1000),patch.object(r.news_signal,'cached_state',side_effect=lambda s:bundle()['news'][s]):
            sample=await r.capture(None,'https://public.example',request)
        self.assertEqual(len(requests),15)
        self.assertTrue(all(u.endswith(('/api/v3/depth','/api/v3/klines','/api/v3/ticker/price')) for u,p in requests))
        self.assertIn('books:SOLUSDC',sample['errors'])
        self.assertFalse(sample['quality']['inputs_complete'])
        self.assertNotIn('SOLUSDC',sample['books'])


class FakeCursor:
    def __init__(self,value):self.value=value
    def fetchone(self):return self.value


class FakeConnection:
    def __init__(self,used=0,duplicate=False):self.used=used;self.duplicate=duplicate;self.calls=[]
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def execute(self,query,args=()):
        self.calls.append((query,args))
        if 'pg_total_relation_size' in query:return FakeCursor((self.used,))
        if 'RETURNING bucket' in query:return FakeCursor(None if self.duplicate else (1,))
        return FakeCursor(None)


class PersistenceTests(unittest.TestCase):
    def sample(self):
        sample=bundle();sample['signals']=dict(errors={},fly=[],fast=[],leadlag=None)
        return sample

    def test_budget_stops_before_writes_without_deleting_old_data(self):
        conn=FakeConnection(used=r.MAX_ARCHIVE_BYTES)
        with patch.object(r,'connect',return_value=conn):
            result=r.store_sample('test','run',{},self.sample())
        self.assertFalse(result['saved']);self.assertEqual(result['reason'],'archive_full')
        self.assertFalse(any('INSERT' in q or 'DELETE' in q or 'UPDATE' in q for q,a in conn.calls))

    def test_roundtrip_archive_and_duplicate_bucket(self):
        for duplicate in (False,True):
            conn=FakeConnection(duplicate=duplicate);sample=self.sample()
            with patch.object(r,'connect',return_value=conn):
                result=r.store_sample('test','run',{},sample)
            self.assertEqual(result['saved'],not duplicate)
            q,args=next((q,a) for q,a in conn.calls if 'RETURNING bucket' in q)
            self.assertEqual(json.loads(gzip.decompress(args[4])),sample)
            self.assertTrue(args[3]);self.assertEqual(len(args[5]),64)
            self.assertIn('ON CONFLICT DO NOTHING',q)
            self.assertFalse(any('trades' in q or 'bot_state' in q for q,a in conn.calls))


if __name__=='__main__':unittest.main()
