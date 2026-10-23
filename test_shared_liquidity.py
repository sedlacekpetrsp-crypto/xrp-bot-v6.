import asyncio
import json
import time
from types import SimpleNamespace
from unittest.mock import patch
import httpx
import pytest
import lh_whale as lh
import liquidity_local as local
import liquidity_monitor as monitor


def candles(minutes):
    step=minutes*60000
    end=int(time.time()*1000)//step*step
    return [[end-step*(60-i),100,101,99,100,10,end-step*(59-i)-1] for i in range(60)]

async def klines(symbol,interval,limit):
    return candles({'5m':5,'15m':15,'1h':60}[interval])

def test_blocked_futures_fail_closed_and_backoff():
    async def run():
        calls=[]
        def response(req):
            calls.append(req)
            return httpx.Response(451)
        core=SimpleNamespace(get_klines=klines,LH_LOCAL_ONLY=True)
        with patch.object(lh,'_futures_retry_at',0), patch.object(lh,'signal_from_closed_candles',return_value=SimpleNamespace(side='LONG',stop=98,reason='test')):
            async with httpx.AsyncClient(transport=httpx.MockTransport(response)) as client:
                a=await lh.analyze(core,client)
                n=len(calls)
                b=await lh.analyze(core,client)
                assert len(calls)==n
                assert a['signal']==b['signal']=='WAIT'
                assert a['data_status']==b['data_status']=='blocked'
                s=lh.initial(); s['activated_at']=1
                assert lh.advance(s,dict(price=100,time=a['candle']),a,a['candle'])['position'] is None
    asyncio.run(run())

@pytest.mark.parametrize('module',[lh,local])
def test_exit_management_survives_missing_signals(module):
    s=module.initial();s['activated_at']=1
    s=module.advance(s,dict(price=100,time=300010),dict(candle=300000,signal='LONG',stop=98),300010)
    assert s['position']
    s=module.advance(s,dict(price=97,time=300020),None,300020)
    assert s['position'] is None and s['count']==1
    assert s['trades'][0]['reason']=='STOP LOSS'

def test_local_analysis_never_calls_remote_service():
    async def run():
        class NoNetwork:
            async def get(self,*a,**kw): raise AssertionError('remote call')
        a=await local.analyze(SimpleNamespace(get_klines=klines),NoNetwork())
        assert a['signal']=='WAIT' and a['data_status']=='available'
    asyncio.run(run())

def test_monitor_schema_and_stale_state():
    now=int(time.time()*1000)
    s=local.initial();s['last_cycle_at']=local.iso(now)
    with patch.object(local,'runtime',dict(state=s,quote=dict(price=100,time=now-60000),persistence='postgres')):
        d=monitor.snapshot()
        assert d['mode']=='PAPER' and d['signal_source']=='local'
        assert d['status_available'] and not d['status_fresh']
        assert isinstance(d['positions'],dict) and isinstance(d['analysis'],dict)
        assert d['persistence']=='postgres'

def test_local_storage_isolated_and_atomic():
    statements=[]
    class DB:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def execute(self,sql,args=None):
            statements.append(sql)
            return self
        def fetchone(self): return [local.initial()]
    with patch.object(local,'connect',return_value=DB()):
        local.init_db('test')
        local.tick('test',dict(price=100,time=300010),None,300010)
    assert any('FOR UPDATE' in x for x in statements)
    assert all('lh_whale_' not in x and 'bestof_' not in x and 'v9_' not in x for x in statements)
    assert any('UPDATE liquidity_v2_state' in x for x in statements)

def test_install_once_and_shutdown():
    from fastapi import FastAPI
    async def run():
        app=FastAPI()
        async def worker(core): await asyncio.Event().wait()
        with patch.object(local,'worker',worker), patch.object(local,'_task',None):
            local.install(app,SimpleNamespace())
            await app.router.on_startup[0]()
            first=local._task
            await app.router.on_startup[0]()
            assert local._task is first
            await app.router.on_shutdown[0]()
            assert first.cancelled()
    asyncio.run(run())

def test_combined_routes_local_and_pause_preserved():
    import app_v8_fly as app
    assert {'FLY','FAST','LEADLAG'} <= app.PAUSED_BOTS
    for bot in ('FLY','FAST','LEADLAG'):
        assert app.portfolio_entry_allowed(bot,'XRPUSDT','LONG')[0] is False
    async def run():
        with patch.object(monitor,'snapshot',return_value={'mode':'PAPER','execution':'shared-paid-service'}):
            for endpoint in (app.liquidity_v2_status,app.liquidity_hunter_status):
                assert json.loads((await endpoint()).body)['execution']=='shared-paid-service'
    asyncio.run(run())
