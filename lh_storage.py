"""Authenticated LH-Whale persistence bridge; no database credentials leave Render."""
import asyncio
import json
import os
import secrets
import httpx
from swing_paper import connect

def remote_call(method,payload=None):
    url=os.environ['LH_STORAGE_URL'].rstrip('/')+'/lh-whale/storage'
    token=os.environ['LH_STORAGE_TOKEN']
    with httpx.Client(timeout=12) as client:
        r=client.request(method,url,headers={'Authorization':'Bearer '+token},json=payload)
        r.raise_for_status()
        return r.json()

def remote_tick(quote,analysis,now,advance):
    current=remote_call('GET')
    state=advance(current['state'],quote,analysis,now)
    return remote_call('PUT',dict(expected=current['revision'],state=state))['state']

def install(app,core):
    from fastapi import Request, HTTPException
    from lh_whale import init_db

    def authorize(request):
        token=os.getenv('LH_STORAGE_TOKEN')
        if not token: raise HTTPException(503,'Persistence bridge disabled')
        if not secrets.compare_digest(request.headers.get('authorization',''),'Bearer '+token):
            raise HTTPException(401,'Unauthorized')

    def read():
        init_db(core.DATABASE_URL)
        with connect(core.DATABASE_URL) as conn:
            s=conn.execute('SELECT state FROM lh_whale_state WHERE id=1').fetchone()[0]
        return dict(state=s,revision=s.get('last_cycle_at'))

    def write(payload):
        s=payload.get('state')
        if not isinstance(s,dict) or not isinstance(s.get('trades'),list) or len(s['trades'])>500:
            raise HTTPException(400,'Invalid state')
        with connect(core.DATABASE_URL) as conn:
            previous=conn.execute('SELECT state FROM lh_whale_state WHERE id=1 FOR UPDATE').fetchone()[0]
            if previous.get('last_cycle_at')!=payload.get('expected'):
                raise HTTPException(409,'Concurrent update; retry with fresh state')
            if not s.get('last_cycle_at') or (previous.get('last_cycle_at') and s['last_cycle_at']<=previous['last_cycle_at']):
                raise HTTPException(409,'Outdated observation')
            if s['count']-previous['count'] not in (0,1): raise HTTPException(400,'Invalid trade transition')
            if s['count']>previous['count']:
                t=s['trades'][0]
                conn.execute('INSERT INTO lh_whale_trades VALUES (%s,%s::jsonb)',(t['id'],json.dumps(t)))
            conn.execute('UPDATE lh_whale_state SET state=%s::jsonb WHERE id=1',(json.dumps(s),))
        return dict(state=s,revision=s['last_cycle_at'])

    @app.get('/lh-whale/storage')
    async def get_state(request:Request):
        authorize(request)
        return await asyncio.to_thread(read)

    @app.put('/lh-whale/storage')
    async def put_state(request:Request):
        authorize(request)
        data=await request.body()
        if len(data)>1000000: raise HTTPException(413,'State too large')
        try: payload=json.loads(data)
        except ValueError: raise HTTPException(400,'Invalid JSON')
        return await asyncio.to_thread(write,payload)
