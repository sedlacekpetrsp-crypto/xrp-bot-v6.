"""Public market-data provider only. No portfolio, worker, orders or database."""
import asyncio
import time
import httpx
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from market_data import market_get
from lh_whale import analyze

class SpotMarket:
    client=None
    async def get_klines(self,symbol,interval='5m',limit=250):
        r=await market_get(self.client,'https://data-api.binance.vision/api/v3/klines',
                           params=dict(symbol=symbol,interval=interval,limit=limit),timeout=10)
        r.raise_for_status()
        return r.json()

core=SpotMarket()
app=FastAPI(title='LH-Whale public market data')
cache=None
cached_at=0.
lock=asyncio.Lock()

@app.on_event('startup')
async def start():
    core.client=httpx.AsyncClient(timeout=8)

@app.on_event('shutdown')
async def stop():
    if core.client: await core.client.aclose()

@app.get('/lh-whale/signal')
async def signal():
    global cache,cached_at
    async with lock:
        if not cache or time.monotonic()-cached_at>=25:
            try:
                data=await asyncio.wait_for(analyze(core,core.client),timeout=20)
            except Exception as exc:
                print('LH-DATA unavailable',type(exc).__name__,flush=True)
                return JSONResponse(dict(error='Market data unavailable'),status_code=503)
            cache=data;cached_at=time.monotonic()
            print('LH-DATA OK',data['signal'],data['candle'],flush=True)
        return JSONResponse(cache,headers={'Cache-Control':'no-store'})

@app.get('/')
@app.get('/health')
async def health():
    return dict(role='public-market-data-only',trading_worker=False,database=False,
                cached_signal_age_seconds=time.monotonic()-cached_at if cache else None)
