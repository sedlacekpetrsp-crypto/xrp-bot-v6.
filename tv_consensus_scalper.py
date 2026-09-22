"""TradingView-style Consensus Scalper — PAPER ONLY.

This does not scrape or depend on TradingView. It recreates the useful idea from
TradingView Technicals with Binance candles: moving-average consensus,
oscillator/momentum consensus, ADX strength, and score acceleration.
"""
from __future__ import annotations

import asyncio
import os
import time
from datetime import datetime, timezone, timedelta

import psycopg
from psycopg.types.json import Jsonb

BUILD = "tv-consensus-v1-20260922"
MODE = "PAPER"
SYMBOL = "XRPUSDC"

START_BALANCE = float(os.getenv("TV_START_BALANCE", "10000"))
RISK_PER_TRADE = float(os.getenv("TV_RISK_PER_TRADE", "0.0015"))
MAX_NOTIONAL_SHARE = float(os.getenv("TV_MAX_NOTIONAL_SHARE", "0.25"))
SCAN_SECONDS = 15
STATE_HEARTBEAT_SECONDS = 60.0

ENTRY_SCORE_ALIGNED = 68.0
ENTRY_SCORE_COUNTER = 72.0
MIN_SCORE_EDGE = 10.0
MIN_SCORE_ACCEL = 2.0
MIN_ADX = 16.0
MIN_VOLUME_RATIO = 0.85

MIN_STOP_RATE = 0.0035
MAX_STOP_RATE = 0.0075
ATR_STOP_MULT = 0.95
NET_RR = 1.25
MIN_TARGET_NET_RATE = 0.0028

WIN_COOLDOWN_SECONDS = 45
LOSS_COOLDOWN_SECONDS = 150
MAX_CONSECUTIVE_LOSSES = 4
MAX_DAILY_LOSS_PCT = 0.008
SOFT_HOLD_MINUTES = 12.0
HARD_HOLD_MINUTES = 45.0
FLIP_EXIT_MIN_AGE = 1.0

DB_STATE_TABLE = "tv_consensus_state"
DB_TRADE_TABLE = "tv_consensus_trades"

base = None
DATABASE_URL = None
_last_state_save = 0.0

state = {
    "build": BUILD,
    "mode": MODE,
    "status": "starting",
    "error": None,
    "persistence": "memory",
    "persistence_error": None,
    "balance": START_BALANCE,
    "equity": START_BALANCE,
    "open_position": None,
    "trades": [],
    "analysis": {},
    "last_scan": None,
    "last_entry_candle": None,
    "cooldown_until": None,
    "previous_long_score": None,
    "previous_short_score": None,
}


def utcnow():
    return datetime.now(timezone.utc)


def _db():
    return psycopg.connect(DATABASE_URL, connect_timeout=8) if DATABASE_URL else None


def _payload():
    return {
        "balance": state["balance"],
        "equity": state["equity"],
        "open_position": state["open_position"],
        "trades": state["trades"][-300:],
        "last_entry_candle": state["last_entry_candle"],
        "cooldown_until": state["cooldown_until"],
        "previous_long_score": state["previous_long_score"],
        "previous_short_score": state["previous_short_score"],
        "status": state["status"],
        "error": state["error"],
        "last_scan": state["last_scan"],
        "analysis": state["analysis"],
        "build": state["build"],
    }


def init_persistence():
    global DATABASE_URL, _last_state_save
    DATABASE_URL = getattr(base, "DATABASE_URL", None) or os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        state["persistence_error"] = "DATABASE_URL is not configured"
        return
    try:
        with _db() as conn:
            conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {DB_STATE_TABLE}(
                    id integer PRIMARY KEY,
                    state jsonb NOT NULL,
                    updated_at timestamptz NOT NULL DEFAULT now()
                )
            """)
            conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {DB_TRADE_TABLE}(
                    id bigserial PRIMARY KEY,
                    symbol text NOT NULL,
                    side text NOT NULL,
                    entry double precision NOT NULL,
                    exit double precision NOT NULL,
                    qty double precision NOT NULL,
                    gross_pnl double precision NOT NULL,
                    fees double precision NOT NULL,
                    net_pnl double precision NOT NULL,
                    reason text,
                    entry_score double precision,
                    opposing_score double precision,
                    score_accel double precision,
                    trend_15m text,
                    countertrend boolean,
                    risk_dollars double precision,
                    opened_at timestamptz,
                    closed_at timestamptz
                )
            """)
            row = conn.execute(f"SELECT state FROM {DB_STATE_TABLE} WHERE id=1").fetchone()
            if row and isinstance(row[0], dict):
                saved = row[0]
                for key in (
                    "balance","equity","open_position","trades","last_entry_candle",
                    "cooldown_until","previous_long_score","previous_short_score"
                ):
                    if key in saved:
                        state[key] = saved[key]
            else:
                conn.execute(
                    f"INSERT INTO {DB_STATE_TABLE}(id,state,updated_at) VALUES(1,%s,now()) ON CONFLICT(id) DO NOTHING",
                    (Jsonb(_payload()),),
                )
        state["persistence"] = "postgres"
        state["persistence_error"] = None
        _last_state_save = time.monotonic()
    except Exception as e:
        state["persistence_error"] = repr(e)
        print("TV CONSENSUS PERSIST INIT", repr(e), flush=True)


def save_state():
    global _last_state_save
    if not DATABASE_URL:
        return
    try:
        with _db() as conn:
            conn.execute(
                f"""INSERT INTO {DB_STATE_TABLE}(id,state,updated_at) VALUES(1,%s,now())
                    ON CONFLICT(id) DO UPDATE SET state=EXCLUDED.state,updated_at=now()""",
                (Jsonb(_payload()),),
            )
        state["persistence"] = "postgres"
        state["persistence_error"] = None
        _last_state_save = time.monotonic()
    except Exception as e:
        state["persistence_error"] = repr(e)
        print("TV CONSENSUS SAVE STATE", repr(e), flush=True)


def heartbeat_state(force=False):
    if force or time.monotonic() - _last_state_save >= STATE_HEARTBEAT_SECONDS:
        save_state()


def save_trade(t):
    if not DATABASE_URL:
        return
    try:
        with _db() as conn:
            conn.execute(
                f"""INSERT INTO {DB_TRADE_TABLE}(
                    symbol,side,entry,exit,qty,gross_pnl,fees,net_pnl,reason,
                    entry_score,opposing_score,score_accel,trend_15m,countertrend,
                    risk_dollars,opened_at,closed_at
                ) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    t["symbol"],t["side"],t["entry"],t["exit"],t["qty"],
                    t["gross_pnl"],t["fees"],t["net_pnl"],t["reason"],
                    t.get("entry_score"),t.get("opposing_score"),t.get("score_accel"),
                    t.get("trend_15m"),bool(t.get("countertrend")),
                    t.get("risk_dollars"),t["opened_at"],t["closed_at"],
                ),
            )
    except Exception as e:
        state["persistence_error"] = repr(e)
        print("TV CONSENSUS SAVE TRADE", repr(e), flush=True)


def sma(values, period):
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def stochastic(highs, lows, closes, period=14):
    if len(closes) < period:
        return None, None
    ll = min(lows[-period:])
    hh = max(highs[-period:])
    k = 50.0 if hh == ll else 100.0 * (closes[-1] - ll) / (hh - ll)
    ks = []
    for i in range(3):
        end = len(closes) - i
        start = end - period
        if start < 0:
            continue
        lo = min(lows[start:end]); hi = max(highs[start:end])
        ks.append(50.0 if hi == lo else 100.0 * (closes[end-1] - lo) / (hi - lo))
    d = sum(ks) / len(ks) if ks else k
    return k, d


def cci(highs, lows, closes, period=20):
    if len(closes) < period:
        return None
    tp = [(h+l+c)/3.0 for h,l,c in zip(highs[-period:], lows[-period:], closes[-period:])]
    m = sum(tp) / len(tp)
    md = sum(abs(x-m) for x in tp) / len(tp)
    return 0.0 if md == 0 else (tp[-1]-m) / (0.015*md)


def williams_r(highs, lows, closes, period=14):
    if len(closes) < period:
        return None
    hh=max(highs[-period:]); ll=min(lows[-period:])
    return -50.0 if hh == ll else -100.0 * (hh-closes[-1])/(hh-ll)


def momentum(values, period=10):
    if len(values) <= period:
        return 0.0
    return values[-1] - values[-1-period]


def volume_ratio(volumes, period=20):
    if len(volumes) < period+1:
        return 0.0
    avg=sum(volumes[-period-1:-1])/period
    return volumes[-1]/avg if avg>0 else 0.0


def ma_consensus(closes):
    periods=(10,20,30,50,100,200)
    buys=sells=0
    details={}
    for p in periods:
        e=base.ema(closes,p)
        s=sma(closes,p)
        eb = e is not None and closes[-1] > e
        sb = s is not None and closes[-1] > s
        buys += int(eb) + int(sb)
        sells += int(e is not None and closes[-1] < e) + int(s is not None and closes[-1] < s)
        details[f"ema{p}"]="BUY" if eb else "SELL"
        details[f"sma{p}"]="BUY" if sb else "SELL"
    total=max(buys+sells,1)
    return 40.0*buys/total, 40.0*sells/total, buys, sells, details


def oscillator_scores(highs,lows,closes):
    rsi=base.rsi_wilder(closes)
    k,d=stochastic(highs,lows,closes)
    cc=cci(highs,lows,closes)
    wr=williams_r(highs,lows,closes)
    long=short=0.0

    if rsi is not None:
        if 42 <= rsi <= 68: long += 8
        elif rsi < 42: short += 4
        if 32 <= rsi <= 58: short += 8
        elif rsi > 68: short += 4

    if k is not None and d is not None:
        if k > d and k < 85: long += 6
        if k < d and k > 15: short += 6

    if cc is not None:
        if cc > -50: long += 3
        if cc < 50: short += 3

    if wr is not None:
        if wr > -55: long += 3
        if wr < -45: short += 3

    return long, short, {"rsi":rsi,"stoch_k":k,"stoch_d":d,"cci":cc,"williams_r":wr}


def momentum_scores(closes):
    mh,mhp=base.macd_hist(closes)
    mom=momentum(closes,10)
    roc=(closes[-1]/closes[-11]-1.0) if len(closes)>11 and closes[-11] else 0.0
    long=short=0.0
    if mh is not None:
        if mh > 0: long += 10
        if mh < 0: short += 10
        if mhp is not None and mh > mhp: long += 5
        if mhp is not None and mh < mhp: short += 5
    if mom > 0: long += 8
    elif mom < 0: short += 8
    if roc > 0: long += 7
    elif roc < 0: short += 7
    return long, short, {"macd_hist":mh,"macd_hist_prev":mhp,"momentum10":mom,"roc10":roc}


def adx_score(highs,lows,closes):
    a=base.adx_wilder(highs,lows,closes)
    pts=10.0 if a is not None and a>=24 else 6.0 if a is not None and a>=19 else 3.0 if a is not None and a>=MIN_ADX else 0.0
    return pts,a


def trend_15m(closes):
    e20=base.ema(closes,20)
    e50=base.ema(closes,50)
    e200=base.ema(closes,200)
    if e20 is None or e50 is None:
        return "NEUTRAL",0.0
    if closes[-1] > e20 > e50 and (e200 is None or e50 >= e200):
        return "LONG",5.0
    if closes[-1] < e20 < e50 and (e200 is None or e50 <= e200):
        return "SHORT",5.0
    if closes[-1] > e20 > e50:
        return "LONG",3.0
    if closes[-1] < e20 < e50:
        return "SHORT",3.0
    return "NEUTRAL",0.0


async def analyze_market():
    k1,k5,k15=await asyncio.gather(
        base.get_klines(SYMBOL,"1m",250),
        base.get_klines(SYMBOL,"5m",250),
        base.get_klines(SYMBOL,"15m",250),
    )
    a1,a5,a15=k1[:-1],k5[:-1],k15[:-1]
    h1=[float(x[2]) for x in a1]; l1=[float(x[3]) for x in a1]; c1=[float(x[4]) for x in a1]; v1=[float(x[5]) for x in a1]
    h5=[float(x[2]) for x in a5]; l5=[float(x[3]) for x in a5]; c5=[float(x[4]) for x in a5]
    c15=[float(x[4]) for x in a15]

    ma_l,ma_s,ma_buy,ma_sell,ma_detail=ma_consensus(c5)
    os_l,os_s,os_detail=oscillator_scores(h5,l5,c5)
    mo_l,mo_s,mo_detail=momentum_scores(c5)
    adx_pts,adx=adx_score(h5,l5,c5)
    t15,tbonus=trend_15m(c15)

    long_score=ma_l+os_l+mo_l+adx_pts
    short_score=ma_s+os_s+mo_s+adx_pts
    if t15=="LONG": long_score+=tbonus
    elif t15=="SHORT": short_score+=tbonus
    long_score=min(100.0,long_score)
    short_score=min(100.0,short_score)

    prev_l=state.get("previous_long_score")
    prev_s=state.get("previous_short_score")
    accel_l=long_score-float(prev_l) if prev_l is not None else 0.0
    accel_s=short_score-float(prev_s) if prev_s is not None else 0.0

    mh1,mhp1=base.macd_hist(c1)
    rsi1=base.rsi_wilder(c1)
    fast_long=bool(mh1 is not None and mhp1 is not None and mh1>mhp1 and (rsi1 is None or rsi1>=42))
    fast_short=bool(mh1 is not None and mhp1 is not None and mh1<mhp1 and (rsi1 is None or rsi1<=58))

    vr=volume_ratio(v1)
    atr=base.atr_wilder(h1,l1,c1)
    candle=int(a1[-1][0])
    aligned_long=t15 in ("LONG","NEUTRAL")
    aligned_short=t15 in ("SHORT","NEUTRAL")
    long_thr=ENTRY_SCORE_ALIGNED if aligned_long else ENTRY_SCORE_COUNTER
    short_thr=ENTRY_SCORE_ALIGNED if aligned_short else ENTRY_SCORE_COUNTER

    long_ok=(
        long_score>=long_thr and long_score-short_score>=MIN_SCORE_EDGE and
        (accel_l>=MIN_SCORE_ACCEL or fast_long or long_score>=76) and
        (adx is None or adx>=MIN_ADX) and vr>=MIN_VOLUME_RATIO
    )
    short_ok=(
        short_score>=short_thr and short_score-long_score>=MIN_SCORE_EDGE and
        (accel_s>=MIN_SCORE_ACCEL or fast_short or short_score>=76) and
        (adx is None or adx>=MIN_ADX) and vr>=MIN_VOLUME_RATIO
    )

    signal="LONG" if long_ok and not short_ok else "SHORT" if short_ok and not long_ok else "WAIT"
    countertrend=(signal=="LONG" and t15=="SHORT") or (signal=="SHORT" and t15=="LONG")
    score=long_score if signal=="LONG" else short_score if signal=="SHORT" else max(long_score,short_score)
    opposing=short_score if signal=="LONG" else long_score if signal=="SHORT" else min(long_score,short_score)
    accel=accel_l if signal=="LONG" else accel_s if signal=="SHORT" else max(accel_l,accel_s)

    row={
        "symbol":SYMBOL,"price":float(k1[-1][4]),"candle_time":candle,
        "signal":signal,"long_score":round(long_score,2),"short_score":round(short_score,2),
        "score":round(score,2),"opposing_score":round(opposing,2),"score_accel":round(accel,2),
        "long_accel":round(accel_l,2),"short_accel":round(accel_s,2),
        "ma_buy":ma_buy,"ma_sell":ma_sell,"ma_detail":ma_detail,
        "trend_15m":t15,"countertrend":countertrend,
        "adx5":adx,"volume_ratio":vr,"atr1":atr,
        "fast_rsi1":rsi1,"fast_macd_hist1":mh1,"fast_macd_hist_prev1":mhp1,
        "oscillators":os_detail,"momentum":mo_detail,
        "threshold_long":long_thr,"threshold_short":short_thr,
        "reason":f"TV-like consensus L/S={long_score:.1f}/{short_score:.1f} accel={accel_l:.1f}/{accel_s:.1f} 15m={t15} MA={ma_buy}/{ma_sell} ADX={adx if adx is not None else 0:.1f} vol={vr:.2f}x"
    }
    state["previous_long_score"]=long_score
    state["previous_short_score"]=short_score
    state["analysis"]=row
    return row


def net_pnl_for_exit(p, market_price):
    entry=float(p["entry"]); qty=float(p["qty"]); side=p["side"]
    exit_exec=market_price*(1-base.SLIPPAGE_RATE if side=="LONG" else 1+base.SLIPPAGE_RATE)
    gross=(exit_exec-entry)*qty if side=="LONG" else (entry-exit_exec)*qty
    fees=(entry*qty+exit_exec*qty)*base.FEE_RATE
    return exit_exec,gross,fees,gross-fees


def daily_pnl():
    today=utcnow().date()
    total=0.0
    for t in state["trades"]:
        try:
            if datetime.fromisoformat(t["closed_at"]).date()==today:
                total+=float(t.get("net_pnl") or 0)
        except Exception:
            pass
    return total


def consecutive_losses():
    n=0
    for t in reversed(state["trades"]):
        if float(t.get("net_pnl") or 0)<0: n+=1
        else: break
    return n


def cooldown_active():
    raw=state.get("cooldown_until")
    if not raw: return False
    try: return utcnow()<datetime.fromisoformat(raw)
    except Exception: return False


def open_trade(a, market_price):
    if state["open_position"] or a.get("signal") not in ("LONG","SHORT"):
        return False
    if state.get("last_entry_candle")==a.get("candle_time"):
        return False

    side=a["signal"]
    entry=market_price*(1+base.SLIPPAGE_RATE if side=="LONG" else 1-base.SLIPPAGE_RATE)
    atr=float(a.get("atr1") or 0)
    atr_rate=atr/market_price if atr>0 and market_price>0 else MIN_STOP_RATE
    stop_rate=min(MAX_STOP_RATE,max(MIN_STOP_RATE,atr_rate*ATR_STOP_MULT))
    stop=entry*(1-stop_rate) if side=="LONG" else entry*(1+stop_rate)

    _,_,_,loss_one=net_pnl_for_exit({"entry":entry,"qty":1.0,"side":side},stop)
    loss_one=abs(loss_one)
    if loss_one<=0: return False

    size_mult=0.50 if a.get("countertrend") else 1.0
    risk_dollars=float(state["balance"])*RISK_PER_TRADE*size_mult
    qty=min(risk_dollars/loss_one,float(state["balance"])*MAX_NOTIONAL_SHARE*size_mult/entry)
    if qty<=0: return False

    target_net_per_unit=max(loss_one*NET_RR,entry*MIN_TARGET_NET_RATE)
    tp=base.target_market_for_net_profit(side,entry,target_net_per_unit)
    p={
        "symbol":SYMBOL,"side":side,"entry":entry,"stop":stop,"tp":tp,"qty":qty,
        "notional":qty*entry,"risk_dollars":qty*loss_one,
        "entry_score":float(a["score"]),"opposing_score":float(a["opposing_score"]),
        "score_accel":float(a["score_accel"]),"trend_15m":a.get("trend_15m"),
        "countertrend":bool(a.get("countertrend")),"opened_at":utcnow().isoformat(),
        "candle_time":a.get("candle_time"),"peak_net":0.0
    }
    state["open_position"]=p
    state["last_entry_candle"]=a.get("candle_time")
    save_state()
    print(f"TV CONSENSUS OPEN {side} entry={entry:.6f} score={a['score']:.1f} accel={a['score_accel']:.1f} trend15={a.get('trend_15m')}",flush=True)
    return True


def close_trade(market_price, reason):
    p=state["open_position"]
    if not p: return
    exit_exec,gross,fees,net=net_pnl_for_exit(p,market_price)
    state["balance"]=float(state["balance"])+net
    state["equity"]=state["balance"]
    t={**p,"exit":exit_exec,"gross_pnl":gross,"fees":fees,"net_pnl":net,"reason":reason,"closed_at":utcnow().isoformat()}
    state["trades"].append(t)
    state["trades"]=state["trades"][-300:]
    state["open_position"]=None
    seconds=LOSS_COOLDOWN_SECONDS if net<0 else WIN_COOLDOWN_SECONDS
    if net<0 and consecutive_losses()>=MAX_CONSECUTIVE_LOSSES:
        seconds=20*60
    state["cooldown_until"]=(utcnow()+timedelta(seconds=seconds)).isoformat()
    save_trade(t); save_state()
    print(f"TV CONSENSUS CLOSE net={net:.2f} reason={reason}",flush=True)


async def manage_position(a):
    p=state["open_position"]
    if not p: return
    price=await base.get_live_price(SYMBOL,max_age=1.0)
    _,_,_,net=net_pnl_for_exit(p,price)
    p["peak_net"]=max(float(p.get("peak_net") or 0),net)
    state["equity"]=float(state["balance"])+net

    if p["side"]=="LONG":
        if price<=float(p["stop"]): close_trade(price,"TV STOP"); return
        if price>=float(p["tp"]): close_trade(price,"TV TAKE PROFIT"); return
    else:
        if price>=float(p["stop"]): close_trade(price,"TV STOP"); return
        if price<=float(p["tp"]): close_trade(price,"TV TAKE PROFIT"); return

    age=(utcnow()-datetime.fromisoformat(p["opened_at"])).total_seconds()/60.0
    long_score=float(a.get("long_score") or 0); short_score=float(a.get("short_score") or 0)
    if age>=FLIP_EXIT_MIN_AGE:
        if p["side"]=="LONG" and short_score-long_score>=8:
            close_trade(price,"TV CONSENSUS FLIP"); return
        if p["side"]=="SHORT" and long_score-short_score>=8:
            close_trade(price,"TV CONSENSUS FLIP"); return

    continuation=(long_score>=60 and long_score>short_score) if p["side"]=="LONG" else (short_score>=60 and short_score>long_score)
    if age>=SOFT_HOLD_MINUTES and not continuation:
        close_trade(price,"TV NO CONTINUATION"); return
    if age>=HARD_HOLD_MINUTES:
        close_trade(price,"TV MAX HOLD"); return

    save_state()


async def cycle():
    a=await analyze_market()
    state["last_scan"]=utcnow().isoformat()
    state["status"]="running"; state["error"]=None

    if state["open_position"]:
        await manage_position(a)
        return

    state["equity"]=state["balance"]
    if cooldown_active():
        state["status"]="cooldown"; return

    max_daily_loss=max(START_BALANCE,float(state["balance"]))*MAX_DAILY_LOSS_PCT
    if daily_pnl()<=-max_daily_loss:
        state["status"]="daily_loss_guard"; return
    if consecutive_losses()>=MAX_CONSECUTIVE_LOSSES:
        state["status"]="loss_streak_guard"; return

    if a.get("signal") in ("LONG","SHORT"):
        price=await base.get_live_price(SYMBOL,max_age=1.0)
        open_trade(a,price)


async def bot_loop():
    await asyncio.sleep(11)
    while True:
        try:
            await cycle()
        except Exception as e:
            state["status"]="error"
            state["error"]=f"{type(e).__name__}: {e}"
            print("TV CONSENSUS CYCLE",state["error"],flush=True)
        finally:
            heartbeat_state()
        await asyncio.sleep(SCAN_SECONDS)


def install(base_module):
    global base
    base=base_module
    init_persistence()
    heartbeat_state(force=True)
    return state
