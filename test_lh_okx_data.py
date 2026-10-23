import asyncio
from types import SimpleNamespace
from unittest.mock import patch
import httpx
import pytest
import lh_okx_data as source
import lh_whale as lh
from test_shared_liquidity import klines

STAMP=1800000
OI=[[str(STAMP-300000),'101'],[str(STAMP-600000),'100']]
TOP=[[str(STAMP-300000),'1.2']]
TAKER=[[str(STAMP-300000),'10','12']]

def test_units_and_buy_sell_order():
    normalized=source.normalize(OI,TOP,TAKER,STAMP)
    d=lh.futures_confirmation(*normalized,STAMP,'LONG')
    assert d['score']==3 and d['taker_ratio']==1.2
    assert d['oi_change_pct']==pytest.approx(1)

@pytest.mark.parametrize('rows',[
    [['1200000','1.2']], [['1800000','1.2']],
    [['1500000','nan']], [['1500000','0']],
    [['1500001','1.2']], [['1500000','1.2'],['1500000','1.2']],
])
def test_bad_top_rejected(rows):
    with pytest.raises(ValueError):source.normalize(OI,rows,TAKER,STAMP)

def test_gapped_oi_rejected():
    with pytest.raises(ValueError):source.normalize([OI[0],['900000','100']],TOP,TAKER,STAMP)

def test_current_bucket_never_used():
    a=source.normalize(OI+[[str(STAMP),'900']],TOP+[[str(STAMP),'50']],TAKER+[[str(STAMP),'1','99']],STAMP)
    assert lh.futures_confirmation(*a,STAMP,'LONG')['taker_ratio']==1.2

def test_whale_uses_complete_okx_after_binance_block():
    async def run():
        def response(req):
            if req.url.host=='fapi.binance.com':return httpx.Response(451)
            assert req.url.host=='www.okx.com'
            assert req.url.params['instId']=='XRP-USDT-SWAP'
            now=__import__('time').time()*1000
            stamp=int(now)//300000*300000
            ts=str(stamp-300000)
            rows=([[ts,'101'],[str(stamp-600000),'100']] if 'open-interest' in req.url.path
                  else [[ts,'1.2']] if 'long-short' in req.url.path else [[ts,'10','12']])
            return httpx.Response(200,json=dict(code='0',data=rows))
        core=SimpleNamespace(get_klines=klines,LH_LOCAL_ONLY=True)
        with patch.object(lh,'_futures_retry_at',0),patch.object(lh,'signal_from_closed_candles',return_value=SimpleNamespace(side='LONG',stop=98,reason='test')):
            async with httpx.AsyncClient(transport=httpx.MockTransport(response)) as client:
                d=await lh.analyze(core,client)
                assert d['signal']=='LONG' and d['futures']['score']==3
                assert d['futures_provider']=='okx'
                s=lh.initial();s['activated_at']=1
                s=lh.advance(s,dict(price=100,time=d['candle']+10),d,d['candle']+10)
                assert s['position']['confirmation_variant']=='OKX_TOP5_PAPER'
                s=lh.advance(s,dict(price=97,time=d['candle']+20),None,d['candle']+20)
                assert s['trades'][0]['futures_provider']=='okx'
    asyncio.run(run())

def test_okx_api_error_rejected():
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda req:httpx.Response(200,json=dict(code='50000',data=[])))) as client:
            with pytest.raises(ValueError):await source.fetch(client,STAMP)
    asyncio.run(run())
