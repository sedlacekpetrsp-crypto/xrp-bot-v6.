"""Nonblocking dashboard status for the independently hosted reference bot."""
import asyncio
import copy
import time
from datetime import datetime, timezone
import httpx

URL='https://xrp-liquidity-hunter-24-7.onrender.com/liquidity/status'
data=None
received_at=None
error=None
task=None

def snapshot():
    age=time.monotonic()-received_at if received_at is not None else None
    out=copy.deepcopy(data) if data else dict(bot='LIQUIDITY HUNTER',mode='PAPER',running=False)
    fresh=False
    try:
        cycle=datetime.fromisoformat(str(out['last_cycle_at']).replace('Z','+00:00'))
        fresh=0<=(datetime.now(timezone.utc)-cycle).total_seconds()<120
    except (KeyError,ValueError,TypeError): pass
    out.update(status_available=data is not None,status_age_seconds=age,
               status_fresh=bool(age is not None and age<120 and fresh and not error),
               connection_error=error)
    if not out['status_fresh']: out['running']=False
    return out

async def refresh(client):
    global data,received_at,error
    try:
        r=await client.get(URL)
        r.raise_for_status(); d=r.json()
        if not isinstance(d,dict) or d.get('bot')!='LIQUIDITY HUNTER' or d.get('mode')!='PAPER':
            raise ValueError(f"Unexpected liquidity status schema: keys={list(d)[:15]}, bot={str(d.get('bot'))[:50]!r}, mode={str(d.get('mode'))[:50]!r}")
        data=d;received_at=time.monotonic();error=None
        print('LIQUIDITY-MONITOR OK',d.get('last_cycle_at'),flush=True)
    except asyncio.CancelledError: raise
    except Exception as exc:
        error=type(exc).__name__
        print('LIQUIDITY-MONITOR unavailable',error,str(exc)[:250],flush=True)

async def worker():
    # Cold starts can exceed one minute; UI never waits for this network call.
    async with httpx.AsyncClient(timeout=75) as client:
        while True:
            await refresh(client)
            await asyncio.sleep(30)

def install(app):
    @app.on_event('startup')
    async def start():
        global task
        if task is None or task.done(): task=asyncio.create_task(worker())
    @app.on_event('shutdown')
    async def stop():
        if task:
            task.cancel()
            try: await task
            except asyncio.CancelledError: pass
