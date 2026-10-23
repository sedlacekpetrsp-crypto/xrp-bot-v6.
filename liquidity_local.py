import paper_stop_policy
"""Local Liquidity Hunter V2 PAPER portfolio with closed-candle confirmation.
No exchange order routes. Atomic state/trade persistence, no BEST modifications.
"""
import asyncio
import copy
import json
import math
import os
import time
from datetime import datetime, timezone
import httpx
from swing_paper import connect
from liquidity_hunter import signal_from_closed_candles

BUILD = 'LIQUIDITY-LOCAL-2026-10-23-1'
SYMBOL = 'XRPUSDT'
FEE, SLIP, RISK, RR = .0005, .0002, .005, 2.0
runtime = {}
_task = None

def iso(ms):
    return datetime.fromtimestamp(ms/1000, timezone.utc).isoformat()

def initial():
    return dict(balance=10000., position=None, seen=0, cooldown=0, trades=[], count=0,
                wins=0, activated_at=None, last_cycle_at=None, equity=10000., peak=10000., max_drawdown_pct=0.)

def net(p, price):
    fill = price*(1-p['direction']*SLIP)
    fees = (p['entry_price']+fill)*p['qty']*FEE
    return p['direction']*(fill-p['entry_price'])*p['qty']-fees, fill, fees

def advance(state, quote, analysis, now):
    s = copy.deepcopy(state)
    if s['activated_at'] is None: s['activated_at'] = now
    valid = quote and 0 <= now-quote['time'] <= 15000
    just_closed = False
    if valid and s['position']:
        p = s['position']; price = quote['price']; side = p['direction']
        stop = side*(price-p['stop_loss']) <= 0
        target = side*(price-p['take_profit']) >= 0
        if stop or target:
            pnl, fill, fees = net(p,price)
            t = dict(id=p['id'],symbol=SYMBOL,side=p['side'],setup='LIQUIDITY_HUNTER_V2',
                     entry_price=p['entry_price'],exit_price=fill,qty=p['qty'],pnl=pnl,fees=fees,
                     reason='STOP LOSS' if stop else 'TAKE PROFIT',opened_at=p['opened_at'],closed_at=iso(now))
            s['balance'] += pnl; s['count'] += 1; s['wins'] += int(pnl>0)
            s['trades'].insert(0,t); s['trades'] = s['trades'][:500]
            s['position'] = None; s['cooldown'] = now+(20 if pnl<0 else 5)*60000
            just_closed = True
    if valid and analysis and not s['position'] and not just_closed:
        stamp = analysis['candle']
        # WAIT data can be retried until closed-candle confirmation.
        if analysis.get('signal') in ('LONG','SHORT') and stamp>s['seen']:
            s['seen'] = stamp
            if stamp>=s['activated_at'] and 0<=now-stamp<=120000 and now>=s['cooldown']:
                side = 1 if analysis['signal']=='LONG' else -1
                entry = quote['price']*(1+side*SLIP); stop = analysis['stop']
                distance = side*(entry-stop)
                if .001<=distance/entry<=.05 and s['balance']>0:
                    stopfill = stop*(1-side*SLIP)
                    loss = -side*(stopfill-entry)+FEE*(entry+stopfill)
                    qty = min(s['balance']*RISK/loss, s['balance']*.35/entry)
                    # Solve target for net profit = RR * expected net stop loss.
                    exitfill = (RR*loss+side*entry+FEE*entry)/(side-FEE)
                    target = exitfill/(1-side*SLIP)
                    if target>0 and qty>0:
                        s['position'] = dict(id=f'liquidity-v2:{stamp}',symbol=SYMBOL,side=analysis['signal'],
                            direction=side,entry_price=entry,entry_market=quote['price'],qty=qty,stop_loss=stop,
                            take_profit=target,risk_usdt=qty*loss,opened_at=iso(now),signal_candle=stamp)
                        paper_stop_policy.apply(s['position'], FEE, SLIP)
    s['equity_stale'] = not valid
    if valid:
        s['equity'] = s['balance']+(net(s['position'],quote['price'])[0] if s['position'] else 0)
        s['peak'] = max(s['peak'],s['equity'])
        s['max_drawdown_pct'] = max(s['max_drawdown_pct'],100*(s['peak']-s['equity'])/s['peak'])
    s['last_cycle_at'] = iso(now)
    return s

def init_db(url):
    with connect(url) as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS liquidity_v2_state (id INTEGER PRIMARY KEY, state JSONB NOT NULL)')
        conn.execute('CREATE TABLE IF NOT EXISTS liquidity_v2_trades (id TEXT PRIMARY KEY, trade JSONB NOT NULL)')
        conn.execute('INSERT INTO liquidity_v2_state VALUES (1,%s::jsonb) ON CONFLICT DO NOTHING',(json.dumps(initial()),))

def tick(url,quote,analysis,now):
    with connect(url) as conn:
        state = conn.execute('SELECT state FROM liquidity_v2_state WHERE id=1 FOR UPDATE').fetchone()[0]
        if state.get('last_cycle_at') and state['last_cycle_at']>=iso(now): return state
        previous_count = state['count']; state = advance(state,quote,analysis,now)
        if state['count']>previous_count:
            t = state['trades'][0]
            conn.execute('INSERT INTO liquidity_v2_trades VALUES (%s,%s::jsonb)',(t['id'],json.dumps(t)))
        conn.execute('UPDATE liquidity_v2_state SET state=%s::jsonb WHERE id=1',(json.dumps(state),))
    return state

def closed(raw,minutes,now):
    step = minutes*60000
    rows = [r for r in raw if int(r[6])<now]
    if len(rows)<55 or now-(int(rows[-1][6])+1)>step+45000: raise ValueError('Svíčky chybí nebo jsou zastaralé')
    for i,r in enumerate(rows):
        o,h,l,c,v = map(float,r[1:6])
        if not all(math.isfinite(x) for x in (o,h,l,c,v)) or not 0<l<=min(o,c)<=max(o,c)<=h or v<0:
            raise ValueError('Neplatná OHLC data')
        if int(r[6])!=int(r[0])+step-1 or (i and int(r[0])-int(rows[i-1][0])!=step):
            raise ValueError('Mezera ve svíčkách')
    return rows

async def analyze(core,client):
    raw = await asyncio.gather(*(core.get_klines(SYMBOL,interval,250) for interval in ('5m','15m','1h')))
    now = int(time.time()*1000)
    c5,c15,c1h = [closed(r,m,now) for r,m in zip(raw,(5,15,60))]
    sig = signal_from_closed_candles(
        [float(r[2]) for r in c5], [float(r[3]) for r in c5],
        [float(r[1]) for r in c5], [float(r[4]) for r in c5], [float(r[5]) for r in c5],
        [float(r[4]) for r in c15], [float(r[4]) for r in c1h], stop_atr=1., rr=RR)
    result = dict(candle=int(c5[-1][6])+1, signal='WAIT', data_status='available',
                  reason='Čekám na sweep, reclaim a potvrzení uzavřenou svíčkou')
    if sig:
        result.update(signal=sig.side, stop=sig.stop, reason=sig.reason)
    return result

async def worker(core):
    ready = False; next_scan = 0; analysis = None
    async with httpx.AsyncClient(timeout=8) as client:
        while True:
            try:
                if not ready:
                    await asyncio.to_thread(init_db,core.DATABASE_URL); ready = True
                # Protect open positions before slower signal/statistics requests.
                q = dict(price=float(await asyncio.wait_for(core.get_live_price(SYMBOL,max_age=1),timeout=6)),time=int(time.time()*1000))
                if not math.isfinite(q['price']) or q['price']<=0: raise ValueError('Neplatná cena')
                s = await asyncio.to_thread(tick,core.DATABASE_URL,q,analysis,int(time.time()*1000))
                runtime.update(state=s,quote=q,last_error=None,persistence='postgres')
                if time.monotonic()>=next_scan:
                    try:
                        analysis = await asyncio.wait_for(analyze(core,client),timeout=20)
                        runtime.update(analysis=analysis,data_error=None)
                        print('LIQUIDITY-LOCAL scan',BUILD,analysis['signal'],'postgres',flush=True)
                    except Exception as exc:
                        analysis = None; runtime.update(analysis=None,data_error=type(exc).__name__+': '+str(exc))
                        print('LIQUIDITY-LOCAL data unavailable',BUILD,type(exc).__name__,str(exc),flush=True)
                    next_scan = time.monotonic()+30
            except asyncio.CancelledError: raise
            except Exception as exc:
                runtime['last_error']=type(exc).__name__+': '+str(exc)
                print('LIQUIDITY-LOCAL',type(exc).__name__,flush=True)
            await asyncio.sleep(5)

def snapshot():
    s = runtime.get('state'); q = runtime.get('quote'); now = int(time.time()*1000)
    fresh = bool(q and 0<=now-q['time']<30000)
    age = (now-datetime.fromisoformat(s['last_cycle_at']).timestamp()*1000) if s else float('inf')
    ps=[]
    if s and s['position']:
        p=s['position']; ps=[dict(p,current_price=q['price'] if fresh else None,
            unrealized_net_pnl=net(p,q['price'])[0] if fresh else None,price_stale=not fresh)]
    return dict(bot='LIQUIDITY HUNTER V2',mode='PAPER',build=BUILD,running=_task is not None and not _task.done(),
        execution='shared-paid-service',signal_source='local',
        entries_enabled=bool(runtime.get('analysis') and runtime['analysis'].get('data_status') != 'blocked' and not runtime.get('data_error')),
        data_status=(runtime.get('analysis') or {}).get('data_status', 'unavailable'),
        healthy=age<45000 and fresh and not runtime.get('last_error') and not runtime.get('data_error') and (runtime.get('analysis') or {}).get('data_status') != 'blocked',
        balance=s['balance'] if s else None,equity=s['equity'] if s and fresh else None,
        net_pnl=s['balance']-10000 if s else None,trades_count=s['count'] if s else 0,
        win_rate=100*s['wins']/s['count'] if s and s['count'] else None,positions=ps,
        trades=s['trades'][:50] if s else [],analysis=runtime.get('analysis'),
        market_price=q['price'] if fresh else None,risk_pct=.5,stop_atr=1.,net_rr=RR,
        last_cycle_at=s.get('last_cycle_at') if s else None,persistence=runtime.get('persistence','pending'),
        last_error=runtime.get('last_error'),data_error=runtime.get('data_error'))

def install(app,core,local_only=False):
    from fastapi.responses import JSONResponse
    @app.on_event('startup')
    async def start():
        global _task
        if _task is None or _task.done(): _task=asyncio.create_task(worker(core))
    @app.on_event('shutdown')
    async def stop():
        if _task:
            _task.cancel()
            try: await _task
            except asyncio.CancelledError: pass
    @app.get('/liquidity/status')
    async def status():
        return JSONResponse(snapshot(),headers={'Cache-Control':'no-store'})
