"""Dedicated European LH-Whale PAPER runtime; does not start other strategies."""
import os
import httpx
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from market_data import market_get
import lh_whale

class SpotMarket:
    DATABASE_URL = os.getenv('DATABASE_URL')
    client = None

    async def get_klines(self,symbol,interval='5m',limit=250):
        r=await market_get(self.client,'https://data-api.binance.vision/api/v3/klines',
                           params=dict(symbol=symbol,interval=interval,limit=limit),timeout=10)
        r.raise_for_status()
        return r.json()

    async def get_live_price(self,symbol,max_age=1):
        r=await market_get(self.client,'https://data-api.binance.vision/api/v3/ticker/price',
                           params=dict(symbol=symbol),timeout=6)
        r.raise_for_status()
        return float(r.json()['price'])

core=SpotMarket()
app=FastAPI(title='LH-Whale Europe PAPER')

@app.on_event('startup')
async def start_client():
    core.client=httpx.AsyncClient(timeout=10)

lh_whale.install(app,core)

@app.on_event('shutdown')
async def close_client():
    if core.client: await core.client.aclose()

@app.get('/')
@app.get('/health')
async def health():
    d=lh_whale.snapshot()
    return JSONResponse(d,headers={'Cache-Control':'no-store'})
