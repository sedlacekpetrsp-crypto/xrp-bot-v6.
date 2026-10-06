"""Independent forward PAPER portfolios. Public quotes only; no order API.
Atomic PostgreSQL state/trade commits, row locking, persisted signal deduplication.
"""
import asyncio
import copy
import json
import math
import time
from datetime import datetime, timezone

BUILD = 'SWING-PAPER-2026-10-06-1'
SYMBOLS = ['XRPUSDT', 'BTCUSDT', 'ETHUSDT', 'SOLUSDT']
CONFIG = {
    'aroon_1h_4h': {'label': 'AROON 1h · filtr 4h', 'interval': '1h', 'hours': 1, 'directions': 'LONG'},
    'supertrend_4h': {'label': 'SUPERTREND 4h', 'interval': '4h', 'hours': 4, 'directions': 'LONG / SHORT'},
}
FEE, SLIP, CARRY = .00095, .0002, .0001
RISK, POOL = .005, .015
ENTRY_WINDOW = 120000
runtime = {}
_cache = {}
_task = None


def iso(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat()


def ema(values, period):
    value = values[0]
    for x in values[1:]:
        value += 2 / (period + 1) * (x - value)
    return value


def closed_rows(rows, hours, now):
    rows = [[float(v) for v in r[:7]] for r in rows if int(r[6]) < now]
    step = hours * 3600000
    if len(rows) < 251:
        raise ValueError('Nedostatek uzavřených svíček')
    if now - (rows[-1][6] + 1) > step + 45000:
        raise ValueError('Zastaralé svíčky')
    for i, r in enumerate(rows):
        o, h, l, c = r[1:5]
        if not all(math.isfinite(x) for x in r) or not 0 < l <= min(o, c) <= max(o, c) <= h:
            raise ValueError('Neplatná OHLC data')
        if r[0] % step or r[6] != r[0] + step - 1 or (i and r[0] - rows[i-1][0] != step):
            raise ValueError('Mezera nebo nesprávné časování svíček')
    return rows


def analyze(rows, family, higher=None):
    c = [r[4] for r in rows]
    tr = [rows[0][2] - rows[0][3]] + [max(r[2]-r[3], abs(r[2]-p[4]), abs(r[3]-p[4])) for p, r in zip(rows, rows[1:])]
    atr = sum(tr[-14:]) / 14
    bull, bear = c[-1] > ema(c, 200), c[-1] < ema(c, 200)
    side = 0
    if family == 'aroon_1h_4h':
        def aroon(window):
            return (100 * max(range(25), key=lambda i: window[i][2]) / 24,
                    100 * min(range(25), key=lambda i: window[i][3]) / 24)
        up, down = aroon(rows[-25:])
        pu, pd = aroon(rows[-26:-1])
        if up >= 80 and down <= 20 and not (pu >= 80 and pd <= 20) and bull:
            side = 1
        # Filter uses only the latest 4h candle closed by the native signal.
        higher = [r for r in (higher or []) if r[6] <= rows[-1][6]]
        if len(higher) < 250:
            raise ValueError('Chybí uzavřený 4h filtr')
        hc = [r[4] for r in higher]
        allowed = ema(hc, 20) > ema(hc, 50) and hc[-1] > ema(hc, 200)
        if not allowed:
            side = 0
        el, es = down > up, up > down
        detail = dict(aroon_up=up, aroon_down=down, filter_ok=allowed, filter_candle=int(higher[-1][6])+1)
    else:
        upper = lower = None
        direction = 1
        previous = 1
        for j in range(13, len(rows)):
            a = sum(tr[j-13:j+1]) / 14
            u, l = (rows[j][2]+rows[j][3])/2+3*a, (rows[j][2]+rows[j][3])/2-3*a
            previous = direction
            if j > 13:
                if not (u < upper or c[j-1] > upper): u = upper
                if not (l > lower or c[j-1] < lower): l = lower
                direction = (-1 if c[j] < l else 1) if previous == 1 else (1 if c[j] > u else -1)
            upper, lower = u, l
        if direction == 1 and previous == -1 and bull: side = 1
        if direction == -1 and previous == 1 and bear: side = -1
        el, es = direction == -1, direction == 1
        detail = dict(direction=direction)
    return dict(candle=int(rows[-1][6])+1, close=c[-1], atr=atr, side=side,
                exit_long=el, exit_short=es, **detail)


def initial():
    return dict(balance=10000., positions={}, seen={}, cooldown={}, trades=[], count=0, wins=0,
                peak=10000., max_drawdown_pct=0., equity=10000., activated_at=None, last_cycle_at=None)


def net(p, price, now):
    side = p['direction']
    fill = price * (1 - side * SLIP)
    fees = (p['entry_price'] + fill) * p['qty'] * FEE
    carry = p['entry_price'] * p['qty'] * CARRY * max(0, now-p['entry_ms']) / 28800000 if side == -1 else 0.
    return side * (fill-p['entry_price']) * p['qty'] - fees - carry, fill, fees, carry


def advance(state, family, quotes, frames, now):
    """Pure state transition; caller atomically commits resulting state and trades."""
    s = copy.deepcopy(state)
    if s['activated_at'] is None: s['activated_at'] = now
    closed, just_closed = [], set()
    for sym, p in list(s['positions'].items()):
        q = quotes.get(sym)
        if not q or now-q['time'] > 15000: continue
        price, side = q['price'], p['direction']
        d = frames.get(sym)
        reason = None
        if side*(price-p['stop_loss']) <= 0:
            reason = 'STOP / TRAILING STOP'
        elif d and d['candle'] > p['last_trail_candle']:
            if d['exit_long'] if side == 1 else d['exit_short']:
                reason = 'AROON opačná dominance' if family == 'aroon_1h_4h' else 'SUPERTREND změna směru'
            else:
                p['best_close'] = max(p['best_close'],d['close']) if side == 1 else min(p['best_close'],d['close'])
                trail = p['best_close']-side*3*d['atr']
                p['stop_loss'] = max(p['stop_loss'],trail) if side == 1 else min(p['stop_loss'],trail)
                p['last_trail_candle'] = d['candle']
                if side*(price-p['stop_loss']) <= 0: reason = 'TRAILING STOP'
        if reason:
            pnl, fill, fees, carry = net(p,price,now)
            t = dict(id=p['id'],symbol=sym,side=p['side'],setup=CONFIG[family]['label'],
                     entry_price=p['entry_price'],exit_price=fill,qty=p['qty'],pnl=pnl,fees=fees,
                     carry=carry,reason=reason,opened_at=p['opened_at'],closed_at=iso(now))
            s['balance'] += pnl; s['count'] += 1; s['wins'] += int(pnl > 0)
            s['trades'].insert(0,t); s['trades'] = s['trades'][:500]
            del s['positions'][sym]; just_closed.add(sym); closed.append(t)
            s['cooldown'][sym] = now + (20 if pnl < 0 else 5)*60000
    for sym in SYMBOLS:
        d, q = frames.get(sym), quotes.get(sym)
        if not d or not q or now-q['time'] > 15000: continue
        stamp = d['candle']
        if s['seen'].get(sym,0) >= stamp: continue
        s['seen'][sym] = stamp  # consume each candle even if no slot or missing/old signal
        side = d['side']
        if not side or stamp < s['activated_at'] or not 0 <= now-stamp <= ENTRY_WINDOW: continue
        if sym in s['positions'] or sym in just_closed or len(s['positions']) >= 2 or now < s['cooldown'].get(sym,0): continue
        entry = q['price'] * (1+side*SLIP); stop = d['close']-side*2.5*d['atr']
        if not .002 <= side*(entry-stop)/entry <= .12: continue
        stopfill = stop*(1-side*SLIP)
        loss = -side*(stopfill-entry)+FEE*(entry+stopfill)
        balance = s['balance']; ps = s['positions'].values()
        risk = min(balance*RISK,max(0,balance*POOL-sum(p['risk_usdt'] for p in ps)))
        exposure = sum(p['entry_price']*p['qty'] for p in ps)
        qty = min(risk/loss,balance*.35/entry,max(0,balance*.70-exposure)/entry)
        if qty <= 0: continue
        s['positions'][sym] = dict(id=f'{family}:{sym}:{stamp}',symbol=sym,direction=side,
            side='LONG' if side == 1 else 'SHORT',entry_price=entry,qty=qty,stop_loss=stop,
            initial_stop=stop,risk_usdt=qty*loss,best_close=d['close'],last_trail_candle=stamp,
            entry_ms=now,opened_at=iso(now),signal_candle=stamp,setup=CONFIG[family]['label'])
    complete = True; equity = s['balance']
    for sym,p in s['positions'].items():
        q = quotes.get(sym)
        if not q or now-q['time'] > 15000:
            complete = False; continue
        equity += net(p,q['price'],now)[0]
    if complete:
        s['equity'] = equity; s['peak'] = max(s['peak'],equity)
        s['max_drawdown_pct'] = max(s['max_drawdown_pct'],100*(s['peak']-equity)/s['peak'])
    s['equity_stale'] = not complete
    s['last_cycle_at'] = iso(now)
    return s,closed


def connect(url):
    import psycopg
    if not url: raise RuntimeError('PAPER strategie vyžadují PostgreSQL')
    return psycopg.connect(url,connect_timeout=5,options='-c statement_timeout=5000 -c lock_timeout=2000')


def init_db(url):
    with connect(url) as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS swing_paper_accounts (strategy TEXT PRIMARY KEY, state JSONB NOT NULL)')
        conn.execute('CREATE TABLE IF NOT EXISTS swing_paper_trades (id TEXT PRIMARY KEY, strategy TEXT NOT NULL, trade JSONB NOT NULL)')
        for family in CONFIG:
            conn.execute('INSERT INTO swing_paper_accounts VALUES (%s,%s::jsonb) ON CONFLICT DO NOTHING',(family,json.dumps(initial())))


def commit_tick(url,family,quotes,frames,now):
    with connect(url) as conn:
        row = conn.execute('SELECT state FROM swing_paper_accounts WHERE strategy=%s FOR UPDATE',(family,)).fetchone()
        if not row: raise RuntimeError('Chybí účet strategie')
        state = row[0]
        # Another worker may already have committed a newer observation.
        if state.get('last_cycle_at') and state['last_cycle_at'] >= iso(now): return state
        state,trades = advance(state,family,quotes,frames,now)
        for t in trades:
            conn.execute('INSERT INTO swing_paper_trades VALUES (%s,%s,%s::jsonb)',(t['id'],family,json.dumps(t)))
        conn.execute('UPDATE swing_paper_accounts SET state=%s::jsonb WHERE strategy=%s',(json.dumps(state),family))
    return state


async def frame(core,sym,hours):
    now = int(time.time()*1000); key = (sym,hours); step = hours*3600000
    cached = _cache.get(key)
    if cached and now < cached[-1][6]+1+step: return cached
    raw = await asyncio.wait_for(core.get_klines(sym,f'{hours}h',1000),timeout=12)
    rows = closed_rows(raw,hours,int(time.time()*1000))
    _cache[key] = rows
    return rows


async def worker(core):
    ready = False
    while True:
        try:
            if not ready:
                await asyncio.to_thread(init_db,core.DATABASE_URL); ready = True
            # Fetch indicators before fresh quotes; slow candles must not delay stop checks indefinitely.
            frames = {k:{} for k in CONFIG}; errors = {k:{} for k in CONFIG}
            async def load_symbol(sym):
                try:
                    h4 = await frame(core,sym,4)
                    frames['supertrend_4h'][sym] = analyze(h4,'supertrend_4h')
                except Exception as exc:
                    h4 = None; errors['supertrend_4h'][sym] = type(exc).__name__+': '+str(exc)
                try:
                    h1 = await frame(core,sym,1)
                    if h4 is None: raise ValueError('4h filtr není dostupný')
                    frames['aroon_1h_4h'][sym] = analyze(h1,'aroon_1h_4h',h4)
                except Exception as exc: errors['aroon_1h_4h'][sym] = type(exc).__name__+': '+str(exc)
            await asyncio.gather(*(load_symbol(sym) for sym in SYMBOLS))
            quotes = {}
            async def price(sym):
                try:
                    p = float(await asyncio.wait_for(core.get_live_price(sym,max_age=1),timeout=6))
                    if not math.isfinite(p) or p <= 0: raise ValueError('Neplatná cena')
                    quotes[sym] = dict(price=p,time=int(time.time()*1000))
                except Exception as exc:
                    for k in CONFIG: errors[k][sym] = 'Cena nedostupná: '+type(exc).__name__
            await asyncio.gather(*(price(sym) for sym in SYMBOLS))
            now = int(time.time()*1000)
            for family in CONFIG:
                try:
                    s = await asyncio.to_thread(commit_tick,core.DATABASE_URL,family,quotes,frames[family],now)
                    runtime[family] = dict(state=s,quotes=quotes,checks=frames[family],errors=errors[family],persistence='postgres',last_error=None)
                except Exception as exc:
                    runtime.setdefault(family,{})['last_error'] = 'Uložení stavu selhalo: '+type(exc).__name__
                    print('SWING persistence error',family,type(exc).__name__,flush=True)
        except asyncio.CancelledError: raise
        except Exception as exc:
            for family in CONFIG: runtime.setdefault(family,{})['last_error'] = 'Inicializace selhala: '+type(exc).__name__
            print('SWING worker error',type(exc).__name__,flush=True)
        await asyncio.sleep(5)


def snapshot():
    now = int(time.time()*1000); accounts = []
    for family,config in CONFIG.items():
        r = runtime.get(family,{}); s = r.get('state'); positions=[]
        if s:
            for sym,p in s['positions'].items():
                q = r.get('quotes',{}).get(sym); stale = not q or now-q['time'] > 15000
                positions.append(dict(p,current_price=q['price'] if q else None,
                    unrealized_net_pnl=net(p,q['price'],now)[0] if q else None,price_stale=stale))
        age = now-datetime.fromisoformat(s['last_cycle_at']).timestamp()*1000 if s and s.get('last_cycle_at') else float('inf')
        accounts.append(dict(id=family,**config,mode='PAPER',build=BUILD,risk_pct=.5,
            balance=s['balance'] if s else None,equity=s['equity'] if s and not s.get('equity_stale') and age<45000 else None,
            net_pnl=s['balance']-10000 if s else None,max_drawdown_pct=s['max_drawdown_pct'] if s else None,
            trades_count=s['count'] if s else 0,win_rate=100*s['wins']/s['count'] if s and s['count'] else None,
            positions=positions,trades=s['trades'][:50] if s else [],checks=r.get('checks',{}),
            errors=r.get('errors',{}),last_error=r.get('last_error'),persistence=r.get('persistence','pending'),
            healthy=age<45000 and not r.get('last_error') and not r.get('errors'),
            last_cycle_at=s.get('last_cycle_at') if s else None,activated_at=iso(s['activated_at']) if s and s.get('activated_at') else None))
    return dict(build=BUILD,accounts=accounts)


def install(app,core):
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
    @app.get('/swing/status')
    async def status():
        return JSONResponse(snapshot(),headers={'Cache-Control':'no-store'})
