import paper_stop_policy
"""Independent XRP NEWS_LONG PAPER account; no exchange order API.
Shares read-only FLY market confirmation, never its paused cycle or accounting.
"""
import asyncio
import copy
import hashlib
import json
import math
import re
import time
from datetime import datetime, timezone

import news_signal
import v8_fly_layer
from swing_paper import connect

BUILD = 'NEWS-PAPER-20261011-1'
SYMBOL = 'XRPUSDC'
RISK = .0014
MAX_NOTIONAL = .35
RR = 1.6
runtime = {}
_tasks = []


def iso(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat()


def initial():
    return dict(balance=10000., position=None, trades=[], count=0, wins=0,
                used_headlines=[], last_candle=0, cooldown=0, day=None,
                day_start=10000., day_pnl=0., last_cycle_at=None, reason='Spouštím NEWS PAPER')


def headline_keys(news):
    return sorted({hashlib.sha256(re.sub(r'\W+', ' ', h['title'].lower()).strip().encode()).hexdigest()
                   for h in news.get('headlines', []) if h.get('score', 0) >= 2})


def news_blocker(news):
    if news.get('status') != 'running':
        return 'Zprávy nejsou aktuální nebo zdroje nejsou dostupné'
    if news.get('bearish'):
        return 'Negativní zprávy blokují LONG'
    if not news.get('bullish') or not headline_keys(news):
        return 'Čekám na čerstvou pozitivní zprávu z RSS zdrojů'
    return None


def net(p, price):
    fill = price * (1 - p['slip'])
    fees = (p['entry_price'] + fill) * p['qty'] * p['fee']
    return (fill - p['entry_price']) * p['qty'] - fees, fill, fees


def advance(state, quote, analysis, news, now, config):
    s = copy.deepcopy(state)
    day = iso(now)[:10]
    if s['day'] != day:
        s.update(day=day, day_start=s['balance'], day_pnl=0.)
    valid = bool(quote and 0 <= now-quote['time'] <= 15000
                 and math.isfinite(quote['price']) and quote['price'] > 0)
    closed = False
    if valid and s['position']:
        p = s['position']; price = quote['price']
        if price <= p['stop_loss'] or price >= p['take_profit']:
            pnl, fill, fees = net(p, price)
            trade = dict(p, exit_price=fill, pnl=pnl, fees=fees,
                         closed_at=iso(now), reason='STOP LOSS' if price <= p['stop_loss'] else 'TAKE PROFIT')
            s['balance'] += pnl; s['day_pnl'] += pnl
            s['count'] += 1; s['wins'] += int(pnl > 0)
            s['trades'].insert(0, trade); s['trades'] = s['trades'][:500]
            s.update(position=None, cooldown=now + (30 if pnl < 0 else 15)*60000)
            closed = True
    reason = news_blocker(news)
    keys = headline_keys(news)
    if not valid:
        reason = 'Čekám na aktuální cenu'
    elif s['position']:
        reason = 'Spravuji otevřený NEWS_LONG'
    elif closed or now < s['cooldown']:
        reason = 'Pauza po uzavřeném obchodu'
    elif s['day_pnl'] <= -s['day_start']*.0075 or s['balance'] <= 0:
        reason = 'Denní limit ztráty'
    elif not reason:
        if not set(keys) - set(s['used_headlines']):
            reason = 'Tuto zprávu už jsem obchodoval'
        elif not analysis or not 0 <= now-analysis.get('checked_ms', 0) <= 25000:
            reason = 'Čekám na aktuální potvrzení trhu'
        elif analysis.get('signal') != 'LONG' or analysis.get('setup') != 'NEWS_LONG':
            reason = (analysis.get('no_trade_reason') or 'Čekám na potvrzení ceny, objemu a nákupní převahy')
        elif analysis.get('news_keys') != keys:
            reason = 'Nové zprávy čekají na potvrzení trhu'
        elif not 0 <= now-(analysis['candle_time']+60000) <= 90000:
            reason = 'Signální svíčka není aktuální a uzavřená'
        elif analysis['candle_time'] <= s['last_candle']:
            reason = 'Tuto svíčku už jsem obchodoval'
        else:
            price = quote['price']; atr = float(analysis.get('atr') or 0)
            anchor = float(analysis.get('price') or 0)
            distance = max(atr*config['atr_mult'], price*config['min_stop'])
            if not math.isfinite(atr) or atr <= 0 or not math.isfinite(anchor) or anchor <= 0 or abs(price-anchor) > atr*.5:
                reason = 'Cena se vzdálila od potvrzeného vstupu'
            elif distance/price > config['max_stop']:
                reason = 'Stop-loss je mimo povolený rozsah'
            else:
                fee, slip = config['fee'], config['slip']
                entry = price*(1+slip); stop = entry-distance
                stop_fill = stop*(1-slip)
                loss = entry-stop_fill+fee*(entry+stop_fill)
                qty = min(s['balance']*RISK/loss, s['balance']*MAX_NOTIONAL/entry)
                target = (RR*loss+entry*(1+fee))/((1-fee)*(1-slip))
                s['position'] = dict(id=f'news:{analysis["candle_time"]}', symbol=SYMBOL,
                    setup='NEWS_LONG', side='LONG', entry_price=entry, qty=qty,
                    stop_loss=stop, take_profit=target, risk_usdc=qty*loss, fee=fee, slip=slip,
                    opened_at=iso(now), headline_keys=keys, headlines=news['headlines'],
                    signal_candle=analysis['candle_time'])
                paper_stop_policy.apply(s['position'], fee, slip)
                s['used_headlines'] = sorted(set(s['used_headlines']) | set(keys))
                s['last_candle'] = analysis['candle_time']
                reason = 'Otevřen NEWS_LONG v PAPER'
    s['reason'] = reason
    s['last_cycle_at'] = iso(now)
    return s


def init_db(url):
    with connect(url) as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS news_paper_state (id INTEGER PRIMARY KEY, state JSONB NOT NULL)')
        conn.execute('CREATE TABLE IF NOT EXISTS news_paper_trades (id TEXT PRIMARY KEY, trade JSONB NOT NULL)')
        conn.execute('INSERT INTO news_paper_state VALUES (1,%s::jsonb) ON CONFLICT DO NOTHING', (json.dumps(initial()),))


def tick(url, quote, analysis, news, now, config):
    with connect(url) as conn:
        state = conn.execute('SELECT state FROM news_paper_state WHERE id=1 FOR UPDATE').fetchone()[0]
        if state.get('last_cycle_at') and state['last_cycle_at'] >= iso(now):
            return state
        old_count = state['count']
        state = advance(state, quote, analysis, news, now, config)
        if state['count'] > old_count:
            t = state['trades'][0]
            conn.execute('INSERT INTO news_paper_trades VALUES (%s,%s::jsonb)', (t['id'], json.dumps(t)))
        conn.execute('UPDATE news_paper_state SET state=%s::jsonb WHERE id=1', (json.dumps(state),))
    return state


async def scan_once(base):
    news = news_signal.cached_state(SYMBOL)
    if news_blocker(news):
        runtime.update(analysis=None, data_error=None)
        return
    # Verify candle timing independently; the legacy FLY analysis predates this guard.
    frames = await asyncio.gather(base.get_klines(SYMBOL, '1m'), base.get_klines(SYMBOL, '5m'))
    now = int(time.time()*1000)
    for rows, step in zip(frames, (60000, 300000)):
        if len(rows) < 30 or not 0 <= now-(int(rows[-2][0])+step) <= step+30000:
            raise ValueError('Zastaralá data svíček')
    analysis = await v8_fly_layer.strategy(SYMBOL, news_only=True)
    analysis.update(checked_ms=int(time.time()*1000), news_keys=headline_keys(analysis['news']))
    runtime.update(analysis=analysis, data_error=None)


async def scanner(base):
    while True:
        try:
            await asyncio.wait_for(scan_once(base), timeout=20)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            runtime.update(analysis=None, data_error=type(exc).__name__+': '+str(exc))
        await asyncio.sleep(10)


async def worker(base):
    ready = False
    config = dict(fee=base.FEE_RATE, slip=base.SLIPPAGE_RATE,
                  min_stop=base.MIN_STOP_RATE, max_stop=base.MAX_STOP_RATE,
                  atr_mult=base.SETUP_PARAMS['BREAKOUT']['atr_mult'])
    while True:
        try:
            if not ready:
                await asyncio.to_thread(init_db, base.DATABASE_URL)
                ready = True
            price = float(await asyncio.wait_for(base.get_live_price(SYMBOL, max_age=1), timeout=6))
            if not math.isfinite(price) or price <= 0:
                raise ValueError('Neplatná cena')
            now = int(time.time()*1000)
            quote = dict(price=price, time=now)
            state = await asyncio.to_thread(tick, base.DATABASE_URL, quote,
                runtime.get('analysis'), news_signal.cached_state(SYMBOL), now, config)
            runtime.update(state=state, quote=quote, last_error=None)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            runtime['last_error'] = type(exc).__name__+': '+str(exc)
            print('NEWS_PAPER', runtime['last_error'], flush=True)
        await asyncio.sleep(5)


def snapshot():
    now = int(time.time()*1000)
    s = runtime.get('state') or initial(); q = runtime.get('quote')
    fresh = bool(q and 0 <= now-q['time'] < 30000)
    age = now-datetime.fromisoformat(s['last_cycle_at']).timestamp()*1000 if s['last_cycle_at'] else math.inf
    position = s['position']
    upnl = net(position, q['price'])[0] if position and fresh else None
    running = len(_tasks) == 2 and all(not t.done() for t in _tasks)
    return dict(bot='NEWS_LONG', build=BUILD, mode='PAPER', running=running,
        healthy=running and fresh and age < 45000 and not runtime.get('last_error') and not runtime.get('data_error'),
        balance=s['balance'], equity=s['balance']+(upnl or 0) if fresh else None,
        position=dict(position, current_price=q['price'] if fresh else None, unrealized_net_pnl=upnl) if position else None,
        trades=s['trades'][:50], trades_count=s['count'], net_pnl=s['balance']-10000,
        reason=s['reason'], last_cycle_at=s['last_cycle_at'],
        persistence='postgres' if runtime.get('state') else 'pending',
        risk_pct=RISK*100, net_rr=RR, news=news_signal.cached_state(SYMBOL),
        analysis=runtime.get('analysis'), last_error=runtime.get('last_error'), data_error=runtime.get('data_error'))


def install(app, base):
    from fastapi.responses import JSONResponse
    # NEWS_LONG belongs exclusively to this independent worker, even if FLY is resumed.
    base.ENABLED_SETUPS.discard('NEWS_LONG')

    @app.get('/news-paper/status')
    async def status():
        return JSONResponse(snapshot(), headers={'Cache-Control': 'no-store'})

    @app.on_event('startup')
    async def start():
        if not _tasks:
            _tasks.extend([asyncio.create_task(scanner(base)), asyncio.create_task(worker(base))])

    @app.on_event('shutdown')
    async def stop():
        for task in _tasks:
            task.cancel()
        await asyncio.gather(*_tasks, return_exceptions=True)
        _tasks.clear()
