"""Experimental forward PAPER V18/V56. Public data only, no exchange orders.

User authorized experimental deployment 2026-11-04. These candidates FAILED
the historical acceptance gates; forward results must not be called validated.
Signal rules ported from elite-research-v1 at 01c30707; execution uses observed
quotes (not retrospective candle opens). Independent persistent virtual books.
"""
import asyncio
import copy
import json
import math
import os
import time
from statistics import mean

import httpx
from market_data import market
from swing_paper import connect
import risk_guard

BUILD = 'elite-forward-paper-20261104-1'
SERVICE = 'srv-dang770ae00c73em1sm0'
FEE, ADVERSE, RISK, ALLOCATION = .001, .0004, .005, .35
FAMILIES = ('V18', 'V56')
runtime = dict(build=BUILD, mode='PAPER', validation='EXPERIMENTAL_NOT_APPROVED',
               status='starting', last_error=None, accounts={})
_task = None


def initial():
    return dict(cash=10000., position=None, trades=0, realized_pnl=0., costs=0.,
                peak=10000., drawdown_pct=0., equity=10000., last_tick=0,
                last_signal=None, provider=None, history=[], started_at=None)


def candles(raw, step, now):
    rows=[]; previous=None
    for r in raw:
        t=int(r[0]); o,h,l,c=map(float,r[1:5])
        if t%step or not all(math.isfinite(v) and v>0 for v in (o,h,l,c)) or not l<=min(o,c)<=max(o,c)<=h:
            raise ValueError('Invalid candle')
        if previous is not None and t-previous!=step: raise ValueError('Candle gap')
        previous=t
        # Shared market cache can retain an in-progress candle for 15 seconds.
        # Wait 30 seconds after close before consuming it as final.
        if t+step<=now-30000: rows.append([t,o,h,l,c])
    if not rows or now-(rows[-1][0]+step)>=step+90000: raise ValueError('Stale candles')
    return rows


def signal(family, x, btc=None):
    """Return stop distance, exit flag, max holding milliseconds."""
    c=[r[4] for r in x]; k=len(x)-1
    if k<(200 if family=='V18' else 48): raise ValueError('Insufficient warmup')
    atr=mean(max(x[j][2]-x[j][3],abs(x[j][2]-x[j-1][4]),abs(x[j][3]-x[j-1][4])) for j in range(k-13,k+1))
    if family=='V18':
        b={r[0]:r for r in btc}
        bc=[b[r[0]][4] for r in x[-201:]]
        allowed=bc[-1]>mean(bc[-168:])>mean(bc[-192:-24])
        buy=c[k]>max(r[2] for r in x[k-72:k]) and allowed
        return (3*atr if buy else 0,c[k]<min(r[3] for r in x[k-24:k]),0)
    if family!='V56': raise ValueError('Unknown family')
    a=[None]*9+[mean(c[:10])]
    for j in range(10,len(c)):
        path=sum(abs(c[n]-c[n-1]) for n in range(j-9,j+1))
        er=abs(c[j]-c[j-10])/path if path else 0
        smooth=(er*(2/3-2/31)+2/31)**2
        a.append(a[-1]+smooth*(c[j]-a[-1]))
    weekly=mean(c[k-41:k+1]); old=mean(c[k-47:k-5])
    buy=c[k-1]<=a[k-1] and c[k]>a[k] and a[k]>a[k-6] and weekly>old and c[k]>weekly
    return (3*atr if buy else 0,c[k]<a[k] and c[k-1]<a[k-1],14*86400000)


def append_history(old, new, step):
    if not old: return new
    additions=[r for r in new if r[0]>old[-1][0]]
    if additions and additions[0][0]-old[-1][0]!=step: raise ValueError('History gap; no fabricated catch-up')
    result=old+additions
    if len(result)>10000: raise ValueError('History capacity reached')
    return result


def advance(state, family, data, now):
    s=copy.deepcopy(state); events=[]
    if now<=s['last_tick']: return s,events
    if s['provider'] and s['provider']!=data['provider']: raise ValueError('Provider changed; manual review required')
    s['provider']=data['provider']
    price=float(data['price'])
    if not math.isfinite(price) or price<=0: raise ValueError('Invalid quote')
    step=3600000 if family=='V18' else 14400000
    x=data[family]
    if family=='V56':
        s['history']=append_history(s['history'],x,step); x=s['history']
    decision=signal(family,x,data['BTC'])
    close_time=x[-1][0]+step
    if not 0<=now-close_time<step+90000: raise ValueError('Invalid signal time')
    new_signal=s['last_signal'] is not None and close_time>s['last_signal']
    # First observation establishes a boundary: never enter on pre-start signals.
    if s['started_at'] is None: s['started_at']=now
    exited=False
    p=s['position']
    if p:
        exit_price=None; reason=None
        bars=data['5m']
        if s['last_tick'] and bars[0][0]>s['last_tick']: raise ValueError('Stop history gap')
        # Exclude the entry candle's pre-entry low. Quote polling covers that
        # partial candle; this known sampling limitation is disclosed in status.
        for r in bars:
            if r[0]>=p['entered_at'] and r[0]+300000>s['last_tick'] and r[3]<=p['stop']:
                exit_price=min(price,p['stop'],r[1]); reason='STOP_OBSERVED'; break
        if exit_price is None and price<=p['stop']: exit_price=price; reason='STOP_QUOTE'
        if exit_price is None and new_signal and decision[1]: exit_price=price; reason='SIGNAL'
        if exit_price is None and p['expires'] and now>=p['expires']: exit_price=price; reason='TIME'
        if exit_price is not None:
            fill=exit_price*(1-ADVERSE); proceeds=p['qty']*fill*(1-FEE)
            cost=p['qty']*(exit_price-fill+fill*FEE)
            s['cash']+=proceeds; s['costs']+=cost
            pnl=proceeds-p['debit']; s['realized_pnl']+=pnl; s['trades']+=1
            events.append(dict(id=family+':'+str(p['entered_at'])+':close',kind='CLOSE',at=now,
                               price=fill,qty=p['qty'],pnl=pnl,reason=reason,entry=p))
            s['position']=None; exited=True
    # Entry only just after a NEW closed signal, using a contemporaneous quote.
    rg_ok, rg_mult = risk_guard.gate(s, s['cash'], now, peak=s.get('peak')) if not s['position'] else (False, 0.0)
    if rg_ok and not s['position'] and not exited and new_signal and 0<=now-close_time<=90000 and decision[0]>0:
        entry=price*(1+ADVERSE); stop=entry-decision[0]
        if stop>0:
            loss=entry*(1+FEE)-stop*(1-ADVERSE)*(1-FEE)
            qty=min(s['cash']*RISK*rg_mult/loss,s['cash']*ALLOCATION/(entry*(1+FEE)))
            debit=qty*entry*(1+FEE); s['cash']-=debit
            s['costs']+=qty*(entry-price+entry*FEE)
            s['position']=dict(entered_at=now,qty=qty,entry=entry,stop=stop,debit=debit,
                               signal_closed_at=close_time,expires=now+decision[2] if decision[2] else 0)
            events.append(dict(id=family+':'+str(now)+':open',kind='OPEN',at=now,**s['position']))
    s['last_signal']=close_time; s['last_tick']=now
    s['equity']=s['cash']+(s['position']['qty']*price*(1-ADVERSE)*(1-FEE) if s['position'] else 0)
    s['peak']=max(s['peak'],s['equity'])
    s['drawdown_pct']=max(s['drawdown_pct'],100*(s['peak']-s['equity'])/s['peak'])
    s['risk_guard']=risk_guard.update(s.get('risk_guard'),s['equity'],s['peak'],now)
    return s,events


def init_db(url):
    with connect(url) as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS elite_forward_accounts (strategy TEXT PRIMARY KEY,state JSONB NOT NULL)')
        conn.execute('CREATE TABLE IF NOT EXISTS elite_forward_events (id TEXT PRIMARY KEY,strategy TEXT NOT NULL,event JSONB NOT NULL)')
        for family in FAMILIES:
            conn.execute('INSERT INTO elite_forward_accounts VALUES (%s,%s::jsonb) ON CONFLICT DO NOTHING',(family,json.dumps(initial())))


def commit_tick(url,data,now):
    output={}
    with connect(url) as conn:
        # Atomic books + event ledger; row locks prevent duplicate overlapping deploy workers.
        for family in FAMILIES:
            s=conn.execute('SELECT state FROM elite_forward_accounts WHERE strategy=%s FOR UPDATE',(family,)).fetchone()[0]
            s,events=advance(s,family,data,now)
            for event in events:
                conn.execute('INSERT INTO elite_forward_events VALUES (%s,%s,%s::jsonb)',(event['id'],family,json.dumps(event,allow_nan=False)))
            conn.execute('UPDATE elite_forward_accounts SET state=%s::jsonb WHERE strategy=%s',(json.dumps(s,allow_nan=False),family))
            output[family]={k:v for k,v in s.items() if k!='history'}
            output[family]['warmup_bars']=len(s['history']) if family=='V56' else len(data['V18'])
    return output


async def capture(client,api):
    began=time.time(); provider=market.provider; result={}
    for name,symbol,interval,step in [('V18','XRPUSDT','1h',3600000),('BTC','BTCUSDT','1h',3600000),
                                      ('V56','XRPUSDT','4h',14400000),('5m','XRPUSDT','5m',300000)]:
        r=await market.get(client,api+'/api/v3/klines',params=dict(symbol=symbol,interval=interval,limit=720),timeout=10)
        r.raise_for_status(); result[name]=candles(r.json(),step,int(time.time()*1000))
    r=await market.get(client,api+'/api/v3/ticker/price',params=dict(symbol='XRPUSDT'),timeout=10)
    r.raise_for_status(); result['price']=float(r.json()['price'])
    if time.time()-began>20 or provider!=market.provider: raise ValueError('Unsynchronized snapshot')
    result['provider']=provider
    return result,int(time.time()*1000)


async def worker(core):
    ready=False
    async with httpx.AsyncClient() as client:
        while True:
            try:
                if not ready:
                    await asyncio.to_thread(init_db,core.DATABASE_URL); ready=True
                data,now=await capture(client,core.BINANCE_API)
                accounts=await asyncio.to_thread(commit_tick,core.DATABASE_URL,data,now)
                runtime.update(status='running',last_error=None,last_saved_at=now,accounts=accounts)
            except asyncio.CancelledError: raise
            except Exception as exc:
                # Do not log credentials or provider URLs from network exceptions.
                runtime.update(status='WAIT',last_error=type(exc).__name__,
                               detail=str(exc) if type(exc) is ValueError else 'Data or persistence unavailable')
            await asyncio.sleep(20)


def install(app,core):
    @app.on_event('startup')
    async def start():
        global _task
        if os.getenv('RENDER_SERVICE_ID')!=SERVICE:
            runtime['status']='disabled_other_service'; return
        if _task is None or _task.done(): _task=asyncio.create_task(worker(core))

    @app.on_event('shutdown')
    async def stop():
        if _task:
            _task.cancel()
            try: await _task
            except asyncio.CancelledError: pass

    @app.get('/elite-paper/status')
    async def status():
        from fastapi.responses import JSONResponse
        return JSONResponse(dict(runtime,running=bool(_task and not _task.done()),
            healthy=runtime['status']=='running' and time.time()*1000-runtime.get('last_saved_at',0)<90000,
            symbol='XRPUSDT',risk_per_trade=RISK,max_allocation=ALLOCATION,
            initial_balance_each=10000,fee_each_side=FEE,slippage_plus_halfspread=ADVERSE,
            limitations='Unvalidated experimental candidates. Quote polling every ~20s; incomplete entry-candle extremes unavailable. Market data outages pause execution. Historical results are not forward results.'),
            headers={'Cache-Control':'no-store'})
