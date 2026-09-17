import asyncio
import json
import os
import time
from datetime import datetime, timezone, timedelta

import httpx
import psycopg
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

from market_data import market_get
import app_v8_fly_engine as ind

app = FastAPI(title="V10 Precision XRP")

BUILD = "v10-precision-xrp-20260917-1"
SYMBOL = "XRPUSDC"
BINANCE_API = "https://data-api.binance.vision"
DATABASE_URL = os.getenv("DATABASE_URL")
STARTING_BALANCE = 10000.0
TRADING_MODE = "PAPER"

# High-precision profile: fewer entries, stronger confirmation, smaller risk.
RISK_PER_TRADE = 0.0015
FEE_RATE = 0.0005
SLIPPAGE_RATE = 0.0002
ROUND_TRIP_COST = 2 * (FEE_RATE + SLIPPAGE_RATE)
MIN_STOP_RATE = 0.0035
MAX_STOP_RATE = 0.0080
MAX_NOTIONAL_SHARE = 0.35
COOLDOWN_AFTER_LOSS_MIN = 10
MAX_TRADES_PER_UTC_DAY = 6
DAILY_LOSS_LIMIT_R = 2.0

BREAKOUT_LOOKBACK = 20
RETEST_SECONDS = 150
RETEST_TOL_ATR = 0.10
MIN_VOLUME_RATIO = 1.45
MAX_SPREAD_PCT = 0.00045
BOOK_LONG_MIN = 0.57
BOOK_SHORT_MAX = 0.43
MIN_ADX_15M = 20.0
MIN_EMA_SEP_15M = 0.0010
MIN_ATR_RATE = 0.0020
MAX_ATR_RATE = 0.0120
MIN_SCORE = 9

PARTIAL_TAKE_R = 0.55
PARTIAL_FRACTION = 0.70
FINAL_TAKE_R = 1.20
BREAKEVEN_NET_R = 0.55
MAX_TRADE_MINUTES = 35

paper_balance = STARTING_BALANCE
paper_position = None
trade_history = []
last_entry_candle = None
cooldown_until = None
watch = None
last_cycle_at = None
last_error = None
http_client = None
bot_task = None


def utcnow():
    return datetime.now(timezone.utc)


def get_db():
    return psycopg.connect(DATABASE_URL) if DATABASE_URL else None


def init_db():
    if not DATABASE_URL:
        return
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS v10_precision_trades(
                id SERIAL PRIMARY KEY,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                entry_price DOUBLE PRECISION NOT NULL,
                exit_price DOUBLE PRECISION NOT NULL,
                qty DOUBLE PRECISION NOT NULL,
                gross_pnl DOUBLE PRECISION NOT NULL,
                fees DOUBLE PRECISION NOT NULL,
                pnl DOUBLE PRECISION NOT NULL,
                initial_risk_usdc DOUBLE PRECISION,
                score INTEGER,
                reason TEXT,
                opened_at TIMESTAMPTZ,
                closed_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS v10_precision_state(
                id INTEGER PRIMARY KEY,
                state JSONB NOT NULL
            )
        """)
        conn.commit()


def load_state():
    global paper_balance, paper_position, last_entry_candle, cooldown_until, trade_history
    if not DATABASE_URL:
        return
    with get_db() as conn:
        row = conn.execute("SELECT state FROM v10_precision_state WHERE id=1").fetchone()
        if row:
            s = row[0] or {}
            paper_balance = float(s.get("paper_balance", STARTING_BALANCE))
            paper_position = s.get("paper_position")
            last_entry_candle = s.get("last_entry_candle")
            cd = s.get("cooldown_until")
            cooldown_until = datetime.fromisoformat(cd) if cd else None
        rows = conn.execute("""
            SELECT symbol,side,entry_price,exit_price,qty,gross_pnl,fees,pnl,
                   initial_risk_usdc,score,reason,opened_at,closed_at
            FROM v10_precision_trades ORDER BY id DESC LIMIT 300
        """).fetchall()
    trade_history = [{
        "symbol":r[0],"side":r[1],"entry_price":r[2],"exit_price":r[3],"qty":r[4],
        "gross_pnl":r[5],"fees":r[6],"pnl":r[7],"initial_risk_usdc":r[8],"score":r[9],
        "reason":r[10],"opened_at":r[11].isoformat() if r[11] else None,
        "closed_at":r[12].isoformat() if r[12] else None,
    } for r in rows]


def save_state():
    if not DATABASE_URL:
        return
    s = {
        "paper_balance": paper_balance,
        "paper_position": paper_position,
        "last_entry_candle": last_entry_candle,
        "cooldown_until": cooldown_until.isoformat() if cooldown_until else None,
    }
    with get_db() as conn:
        conn.execute("""
            INSERT INTO v10_precision_state(id,state) VALUES(1,%s::jsonb)
            ON CONFLICT(id) DO UPDATE SET state=EXCLUDED.state
        """, (json.dumps(s),))
        conn.commit()


def save_trade(t):
    if not DATABASE_URL:
        return
    with get_db() as conn:
        conn.execute("""
            INSERT INTO v10_precision_trades(symbol,side,entry_price,exit_price,qty,gross_pnl,fees,pnl,
                initial_risk_usdc,score,reason,opened_at,closed_at)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (t["symbol"],t["side"],t["entry_price"],t["exit_price"],t["qty"],t["gross_pnl"],
              t["fees"],t["pnl"],t["initial_risk_usdc"],t["score"],t["reason"],t["opened_at"],t["closed_at"]))
        conn.commit()


async def fetch(path, params):
    r = await market_get(http_client, BINANCE_API + path, params=params, timeout=12)
    r.raise_for_status()
    return r.json()


async def klines(interval, limit=250):
    return await fetch("/api/v3/klines", {"symbol":SYMBOL,"interval":interval,"limit":limit})


async def live_price():
    d = await fetch("/api/v3/ticker/price", {"symbol":SYMBOL})
    return float(d["price"])


async def depth():
    return await fetch("/api/v3/depth", {"symbol":SYMBOL,"limit":20})


def _ohlcv(rows):
    closed = rows[:-1]
    return (
        [float(x[2]) for x in closed], [float(x[3]) for x in closed],
        [float(x[4]) for x in closed], [float(x[5]) for x in closed],
        int(closed[-1][0])
    )


def _book_stats(d):
    bids, asks = d.get("bids") or [], d.get("asks") or []
    if not bids or not asks:
        return .5, 1.0
    bv = sum(float(p)*float(q) for p,q in bids)
    av = sum(float(p)*float(q) for p,q in asks)
    bid, ask = float(bids[0][0]), float(asks[0][0])
    mid = (bid+ask)/2
    return bv/max(bv+av,1e-12), (ask-bid)/max(mid,1e-12)


def _today_stats():
    today = utcnow().date()
    rows = [t for t in trade_history if t.get("closed_at") and datetime.fromisoformat(t["closed_at"]).date() == today]
    risk = sum(float(t.get("initial_risk_usdc") or 0) for t in rows)
    pnl = sum(float(t.get("pnl") or 0) for t in rows)
    loss_r = max(0.0, -pnl / max(risk/len(rows), 1e-12)) if rows else 0.0
    return len(rows), loss_r


async def analysis():
    k1,k5,k15,book = await asyncio.gather(klines("1m"),klines("5m"),klines("15m"),depth())
    h1,l1,c1,v1,ct = _ohlcv(k1); h5,l5,c5,v5,_ = _ohlcv(k5); h15,l15,c15,v15,_ = _ohlcv(k15)
    px = float(k1[-1][4])
    atr1 = ind.atr_wilder(h1,l1,c1)
    adx15 = ind.adx_wilder(h15,l15,c15)
    e9_1,e21_1 = ind.ema(c1,9),ind.ema(c1,21)
    e9_5,e21_5 = ind.ema(c5,9),ind.ema(c5,21)
    e20_15,e50_15 = ind.ema(c15,20),ind.ema(c15,50)
    rsi = ind.rsi_wilder(c1)
    mh,mhp = ind.macd_hist(c1)
    vw = ind.vwap(h1,l1,c1,v1)
    imb, spread = _book_stats(book)
    prevv = v1[-21:-1]; vr = v1[-1] / (sum(prevv)/len(prevv)) if prevv and sum(prevv)>0 else 0
    bh = max(h1[-BREAKOUT_LOOKBACK-1:-1]); bl = min(l1[-BREAKOUT_LOOKBACK-1:-1])
    atr_rate = atr1/px if atr1 and px else 0
    sep15 = abs(e20_15-e50_15)/px if e20_15 is not None and e50_15 is not None and px else 0
    long15 = e20_15 is not None and e50_15 is not None and e20_15 > e50_15 and c15[-1] > e20_15
    short15 = e20_15 is not None and e50_15 is not None and e20_15 < e50_15 and c15[-1] < e20_15
    long5 = e9_5 is not None and e21_5 is not None and e9_5 > e21_5 and c5[-1] > e9_5
    short5 = e9_5 is not None and e21_5 is not None and e9_5 < e21_5 and c5[-1] < e9_5
    mac_up = mh is not None and mh > 0 and (mhp is None or mh >= mhp)
    mac_dn = mh is not None and mh < 0 and (mhp is None or mh <= mhp)
    long_checks = {
        "trend15":long15,"trend5":long5,"ema1":e9_1 is not None and e21_1 is not None and e9_1>e21_1,
        "rsi":rsi is not None and 52<=rsi<=68,"macd":mac_up,"vwap":vw is not None and c1[-1]>=vw,
        "volume":vr>=MIN_VOLUME_RATIO,"book":imb>=BOOK_LONG_MIN,"spread":spread<=MAX_SPREAD_PCT,
        "adx":adx15 is not None and adx15>=MIN_ADX_15M,"sep15":sep15>=MIN_EMA_SEP_15M,
        "volatility":MIN_ATR_RATE<=atr_rate<=MAX_ATR_RATE,
    }
    short_checks = {
        "trend15":short15,"trend5":short5,"ema1":e9_1 is not None and e21_1 is not None and e9_1<e21_1,
        "rsi":rsi is not None and 32<=rsi<=48,"macd":mac_dn,"vwap":vw is not None and c1[-1]<=vw,
        "volume":vr>=MIN_VOLUME_RATIO,"book":imb<=BOOK_SHORT_MAX,"spread":spread<=MAX_SPREAD_PCT,
        "adx":adx15 is not None and adx15>=MIN_ADX_15M,"sep15":sep15>=MIN_EMA_SEP_15M,
        "volatility":MIN_ATR_RATE<=atr_rate<=MAX_ATR_RATE,
    }
    return {
        "symbol":SYMBOL,"price":px,"candle_time":ct,"atr":atr1,"atr_rate":atr_rate,"adx15":adx15,
        "volume_ratio":vr,"book_imbalance":imb,"spread_pct":spread,"breakout_high":bh,"breakout_low":bl,
        "long_score":sum(long_checks.values()),"short_score":sum(short_checks.values()),
        "long_checks":long_checks,"short_checks":short_checks,
    }


def _net_per_unit(side, entry_exec, exit_market):
    x = exit_market*(1-SLIPPAGE_RATE if side=="LONG" else 1+SLIPPAGE_RATE)
    gross = x-entry_exec if side=="LONG" else entry_exec-x
    return gross-(entry_exec+x)*FEE_RATE


def _target_market(side, entry_exec, target_net_per_unit):
    f,s=FEE_RATE,SLIPPAGE_RATE
    if side=="LONG":
        x=(target_net_per_unit+entry_exec*(1+f))/(1-f); return x/(1-s)
    x=(entry_exec*(1-f)-target_net_per_unit)/(1+f); return x/(1+s)


def open_position(a, side, price, trigger):
    global paper_position,last_entry_candle
    entry=price*(1+SLIPPAGE_RATE if side=="LONG" else 1-SLIPPAGE_RATE)
    dist=max(float(a["atr"])*0.85, price*MIN_STOP_RATE)
    if dist/price>MAX_STOP_RATE:return False
    sl=entry-dist if side=="LONG" else entry+dist
    nloss=-_net_per_unit(side,entry,sl)
    if nloss<=0:return False
    risk=paper_balance*RISK_PER_TRADE
    qty=min(risk/nloss,paper_balance*MAX_NOTIONAL_SHARE/entry)
    if qty<=0:return False
    paper_position={"symbol":SYMBOL,"side":side,"entry_price":entry,"entry_market":price,"qty":qty,"initial_qty":qty,
        "stop_loss":sl,"take_profit":_target_market(side,entry,nloss*FINAL_TAKE_R),"risk_distance":dist,
        "initial_risk_usdc":qty*nloss,"score":a["long_score"] if side=="LONG" else a["short_score"],
        "trigger":trigger,"partial_taken":False,"partial_realized_gross":0.0,"partial_realized_fees":0.0,
        "partial_realized_pnl":0.0,"opened_at":utcnow().isoformat()}
    last_entry_candle=a["candle_time"];save_state();return True


def partial_exit(price):
    global paper_balance
    p=paper_position
    if not p or p.get("partial_taken"):return
    q=float(p["qty"])*PARTIAL_FRACTION; remain=float(p["qty"])-q
    x=price*(1-SLIPPAGE_RATE if p["side"]=="LONG" else 1+SLIPPAGE_RATE)
    e=float(p["entry_price"]);gross=(x-e)*q if p["side"]=="LONG" else (e-x)*q
    fees=(e*q+x*q)*FEE_RATE;net=gross-fees;paper_balance+=net
    p["qty"]=remain;p["partial_taken"]=True;p["partial_realized_gross"]=gross;p["partial_realized_fees"]=fees;p["partial_realized_pnl"]=net
    p["stop_loss"]=_target_market(p["side"],e,0.0);save_state()


def close_position(price, reason):
    global paper_balance,paper_position,cooldown_until,trade_history
    p=paper_position
    if not p:return
    q=float(p["qty"]);e=float(p["entry_price"]);x=price*(1-SLIPPAGE_RATE if p["side"]=="LONG" else 1+SLIPPAGE_RATE)
    gross=(x-e)*q if p["side"]=="LONG" else (e-x)*q;fees=(e*q+x*q)*FEE_RATE;net=gross-fees
    tg=gross+float(p.get("partial_realized_gross") or 0);tf=fees+float(p.get("partial_realized_fees") or 0);tn=net+float(p.get("partial_realized_pnl") or 0)
    paper_balance+=net;now=utcnow();t={"symbol":SYMBOL,"side":p["side"],"entry_price":e,"exit_price":x,"qty":float(p["initial_qty"]),
        "gross_pnl":tg,"fees":tf,"pnl":tn,"initial_risk_usdc":p["initial_risk_usdc"],"score":p["score"],
        "reason":reason+(" | PARTIAL70@0.55R" if p.get("partial_taken") else ""),"opened_at":p["opened_at"],"closed_at":now.isoformat()}
    save_trade(t);trade_history.insert(0,t);trade_history=trade_history[:300]
    cooldown_until=now+timedelta(minutes=COOLDOWN_AFTER_LOSS_MIN if tn<0 else 1);paper_position=None;save_state()


async def manage_position():
    if not paper_position:return
    p=paper_position;px=await live_price();e=float(p["entry_price"]);initial_q=float(p["initial_qty"]);risk=max(float(p["initial_risk_usdc"]),1e-12)
    net_r=_net_per_unit(p["side"],e,px)*initial_q/risk
    if not p.get("partial_taken") and net_r>=PARTIAL_TAKE_R:partial_exit(px);p=paper_position
    if (p["side"]=="LONG" and px<=float(p["stop_loss"])) or (p["side"]=="SHORT" and px>=float(p["stop_loss"])):
        close_position(px,"BREAK_EVEN" if p.get("partial_taken") else "STOP_LOSS");return
    if (p["side"]=="LONG" and px>=float(p["take_profit"])) or (p["side"]=="SHORT" and px<=float(p["take_profit"])):
        close_position(px,"TAKE_PROFIT");return
    age=(utcnow()-datetime.fromisoformat(p["opened_at"])).total_seconds()/60
    if age>=MAX_TRADE_MINUTES:close_position(px,"TIME_EXIT")


async def cycle():
    global watch,last_cycle_at,last_error
    try:
        await manage_position()
        if paper_position:return
        if cooldown_until and utcnow()<cooldown_until:return
        trades_today,loss_r=_today_stats()
        if trades_today>=MAX_TRADES_PER_UTC_DAY or loss_r>=DAILY_LOSS_LIMIT_R:return
        a=await analysis();px=await live_price();now=time.time()
        # Arm only when all context filters pass. Entry itself requires breakout -> retest -> continuation.
        long_ok=a["long_score"]>=MIN_SCORE and a["long_checks"]["trend15"] and a["long_checks"]["trend5"] and a["long_checks"]["volume"] and a["long_checks"]["book"]
        short_ok=a["short_score"]>=MIN_SCORE and a["short_checks"]["trend15"] and a["short_checks"]["trend5"] and a["short_checks"]["volume"] and a["short_checks"]["book"]
        side="LONG" if long_ok else "SHORT" if short_ok else None
        trigger=a["breakout_high"] if side=="LONG" else a["breakout_low"] if side=="SHORT" else None
        if not side:watch=None;return
        crossed=(side=="LONG" and px>trigger) or (side=="SHORT" and px<trigger)
        atr=max(float(a["atr"] or 0),1e-12);tol=atr*RETEST_TOL_ATR
        if crossed and (not watch or watch.get("side")!=side or abs(float(watch.get("trigger",0))-trigger)>tol):
            watch={"side":side,"trigger":trigger,"crossed_at":now,"retested":False,"candle_time":a["candle_time"]};return
        if not watch or watch.get("side")!=side:return
        if now-float(watch["crossed_at"])>RETEST_SECONDS:watch=None;return
        if not watch.get("retested"):
            if trigger-tol<=px<=trigger+tol:watch["retested"]=True
            return
        continuation=(side=="LONG" and px>=trigger+tol*0.35) or (side=="SHORT" and px<=trigger-tol*0.35)
        if continuation and a["candle_time"]!=last_entry_candle:
            open_position(a,side,px,trigger);watch=None
    except Exception as exc:
        last_error=repr(exc)
        raise
    finally:
        last_cycle_at=utcnow().isoformat()


async def bot_loop():
    while True:
        try:await cycle()
        except Exception as exc:print("V10 LOOP",repr(exc),flush=True)
        await asyncio.sleep(5)


@app.on_event("startup")
async def startup():
    global http_client,bot_task
    init_db();load_state();http_client=httpx.AsyncClient();bot_task=asyncio.create_task(bot_loop())


@app.on_event("shutdown")
async def shutdown():
    global http_client
    if bot_task:
        bot_task.cancel();await asyncio.gather(bot_task,return_exceptions=True)
    if http_client:
        await http_client.aclose();http_client=None


def snapshot():
    wins=sum(1 for t in trade_history if float(t.get("pnl") or 0)>0);n=len(trade_history);pnl=sum(float(t.get("pnl") or 0) for t in trade_history)
    return {"build":BUILD,"mode":TRADING_MODE,"symbol":SYMBOL,"balance":paper_balance,"position":paper_position,
        "trades":n,"wins":wins,"win_rate":wins/n*100 if n else 0,"pnl":pnl,"history":trade_history[:50],
        "last_cycle_at":last_cycle_at,"last_error":last_error,"rules":{"min_score":MIN_SCORE,"min_volume":MIN_VOLUME_RATIO,
        "book_long":BOOK_LONG_MIN,"book_short":BOOK_SHORT_MAX,"partial_take_r":PARTIAL_TAKE_R,"partial_fraction":PARTIAL_FRACTION,
        "final_take_r":FINAL_TAKE_R,"risk_per_trade":RISK_PER_TRADE}}


@app.get("/analyze")
async def analyze_route():
    data=snapshot()
    try:data["analysis"]=await analysis()
    except Exception as exc:data["analysis_error"]=str(exc)
    return JSONResponse(data,headers={"Cache-Control":"no-store"})


@app.get("/",response_class=HTMLResponse)
async def dashboard():
    return HTMLResponse('''<!doctype html><html lang="cs"><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{background:#08121f;color:#eef3f8;font-family:system-ui;margin:0}.w{max-width:820px;margin:auto;padding:18px}.c{background:#111d2b;border:1px solid #26384c;border-radius:18px;padding:18px;margin:12px 0}.g{color:#33d6a6}.r{color:#ff6b7e}.m{color:#91a0b2}.big{font-size:30px;font-weight:800}</style><div class="w"><h1>V10 Precision XRP</h1><div class="m">PAPER · XRPUSDC · breakout → retest → continuation · přísný multi-timeframe filtr</div><div class="c" id="main">Načítám…</div><div class="c"><b>Proč je V10 přísnější</b><p class="m">15m + 5m trend, ADX, EMA separation, RSI, MACD, VWAP, volume, order book, spread a volatility. Max 6 obchodů/den.</p></div><div class="c"><b>Historie</b><div id="hist"></div></div></div><script>const f=(x,d=2)=>Number(x||0).toFixed(d);async function load(){let d=await (await fetch('analyze',{cache:'no-store'})).json(),p=d.position;main.innerHTML=`<div class="big ${d.pnl>=0?'g':'r'}">PnL ${d.pnl>=0?'+':''}${f(d.pnl)} USDC</div><p>Balance <b>${f(d.balance)}</b> · Win rate <b>${f(d.win_rate,1)} %</b> · Obchody <b>${d.trades}</b></p><p>${p?`${p.symbol} ${p.side} · entry ${f(p.entry_price,6)} · SL ${f(p.stop_loss,6)} · TP ${f(p.take_profit,6)}${p.partial_taken?' · 70 % zisku vybráno':''}`:'Bez otevřené pozice'}</p>`;hist.innerHTML=(d.history||[]).slice(0,20).map(x=>`<p>${x.side} · <span class="${x.pnl>=0?'g':'r'}">${x.pnl>=0?'+':''}${f(x.pnl)} USDC</span> · ${x.reason}</p>`).join('')||'<span class=m>Zatím bez obchodů.</span>'}load();setInterval(load,5000)</script></html>''',headers={"Cache-Control":"no-store"})