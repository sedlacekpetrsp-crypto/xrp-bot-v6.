import os
import json
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

import httpx
import psycopg
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(title="XRP Bot V8 Candle Fixed")

SYMBOL = os.getenv("SYMBOL", "XRPUSDT")
BINANCE_API = os.getenv("BINANCE_API", "https://data-api.binance.vision")
TRADING_MODE = "PAPER"
STARTING_BALANCE = float(os.getenv("STARTING_BALANCE", "10000"))
RISK_PER_TRADE = float(os.getenv("RISK_PER_TRADE", "0.003"))
RISK_REWARD = float(os.getenv("RISK_REWARD", "2.0"))  # skutečné NET R:R po nákladech
FEE_RATE = float(os.getenv("FEE_RATE", "0.0005"))
SLIPPAGE_RATE = float(os.getenv("SLIPPAGE_RATE", "0.0002"))
MAX_NOTIONAL_SHARE = float(os.getenv("MAX_NOTIONAL_SHARE", "0.50"))
MIN_SCORE = int(os.getenv("MIN_SCORE", "6"))
MIN_VOLUME_RATIO = float(os.getenv("MIN_VOLUME_RATIO", "1.35"))
MIN_TREND_STRENGTH = float(os.getenv("MIN_TREND_STRENGTH", "0.0015"))
MAX_TRADE_MINUTES = int(os.getenv("MAX_TRADE_MINUTES", "120"))
BREAKEVEN_TRIGGER_R = float(os.getenv("BREAKEVEN_TRIGGER_R", "0.75"))
ENABLED_SETUPS = {"BULLISH_ENGULFING", "BEARISH_ENGULFING"}
COOLDOWN_AFTER_LOSS_MIN = int(os.getenv("COOLDOWN_AFTER_LOSS_MIN", "30"))
MAIN_INTERVAL = os.getenv("MAIN_INTERVAL", "5m")
STRUCTURE_INTERVAL = os.getenv("STRUCTURE_INTERVAL", "15m")
STRUCTURE_TOLERANCE_PCT = float(os.getenv("STRUCTURE_TOLERANCE_PCT", "0.0035"))
MIN_CANDLE_RANGE_PCT = float(os.getenv("MIN_CANDLE_RANGE_PCT", "0.0012"))
DATABASE_URL = os.getenv("DATABASE_URL")

paper_balance = STARTING_BALANCE
paper_position: Optional[Dict[str, Any]] = None
trade_history: List[Dict[str, Any]] = []
last_entry_candle = None
cooldown_until = None
last_signal: Dict[str, Any] = {}
bot_task = None


def get_db():
    return psycopg.connect(DATABASE_URL) if DATABASE_URL else None


def init_db():
    if not DATABASE_URL:
        print("DATABASE_URL není nastaveno - data nebudou trvale ukládána.")
        return
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS candle_v8_trades (
                    id SERIAL PRIMARY KEY,
                    side TEXT NOT NULL,
                    setup TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    entry_price DOUBLE PRECISION NOT NULL,
                    exit_price DOUBLE PRECISION,
                    qty DOUBLE PRECISION NOT NULL,
                    stop_loss DOUBLE PRECISION NOT NULL,
                    take_profit DOUBLE PRECISION NOT NULL,
                    gross_pnl DOUBLE PRECISION,
                    fees DOUBLE PRECISION,
                    net_pnl DOUBLE PRECISION,
                    reason TEXT,
                    entry_time TIMESTAMPTZ NOT NULL,
                    exit_time TIMESTAMPTZ
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS candle_v8_state (
                    id INTEGER PRIMARY KEY,
                    state JSONB NOT NULL
                )
            """)
        conn.commit()


def save_state():
    if not DATABASE_URL:
        return
    state = {
        "paper_balance": paper_balance,
        "paper_position": paper_position,
        "last_entry_candle": last_entry_candle,
        "cooldown_until": cooldown_until.isoformat() if cooldown_until else None,
    }
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO candle_v8_state (id, state)
                VALUES (1, %s::jsonb)
                ON CONFLICT (id) DO UPDATE SET state = EXCLUDED.state
            """, (json.dumps(state),))
        conn.commit()


def load_state():
    global paper_balance, paper_position, last_entry_candle, cooldown_until, trade_history
    if not DATABASE_URL:
        return
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT state FROM candle_v8_state WHERE id=1")
            row = cur.fetchone()
            if row:
                s = row[0] or {}
                paper_balance = float(s.get("paper_balance", STARTING_BALANCE))
                paper_position = s.get("paper_position")
                last_entry_candle = s.get("last_entry_candle")
                cd = s.get("cooldown_until")
                cooldown_until = datetime.fromisoformat(cd) if cd else None
            cur.execute("""
                SELECT side,setup,score,entry_price,exit_price,qty,stop_loss,take_profit,
                       gross_pnl,fees,net_pnl,reason,entry_time,exit_time
                FROM candle_v8_trades ORDER BY id DESC LIMIT 100
            """)
            rows = cur.fetchall()
    trade_history = [{
        "side":r[0],"setup":r[1],"score":r[2],"entry_price":r[3],"exit_price":r[4],
        "qty":r[5],"stop_loss":r[6],"take_profit":r[7],"gross_pnl":r[8],
        "fees":r[9],"net_pnl":r[10],"reason":r[11],
        "entry_time":r[12].isoformat() if r[12] else None,
        "exit_time":r[13].isoformat() if r[13] else None
    } for r in rows]


def save_trade(t):
    if not DATABASE_URL:
        return
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO candle_v8_trades(
                    side,setup,score,entry_price,exit_price,qty,stop_loss,take_profit,
                    gross_pnl,fees,net_pnl,reason,entry_time,exit_time
                ) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                t["side"],t["setup"],t["score"],t["entry_price"],t["exit_price"],t["qty"],
                t["stop_loss"],t["take_profit"],t["gross_pnl"],t["fees"],t["net_pnl"],
                t["reason"],datetime.fromisoformat(t["entry_time"]),datetime.fromisoformat(t["exit_time"])
            ))
        conn.commit()


async def get_klines(client, interval, limit=120):
    r = await client.get(f"{BINANCE_API}/api/v3/klines", params={"symbol":SYMBOL,"interval":interval,"limit":limit}, timeout=15)
    r.raise_for_status()
    return r.json()


async def get_live_price(client):
    r = await client.get(f"{BINANCE_API}/api/v3/ticker/price", params={"symbol":SYMBOL}, timeout=15)
    r.raise_for_status()
    return float(r.json()["price"])


def candle(k):
    return {"open_time":int(k[0]),"open":float(k[1]),"high":float(k[2]),"low":float(k[3]),"close":float(k[4]),"volume":float(k[5])}


def body(c): return abs(c["close"]-c["open"])
def rng(c): return max(c["high"]-c["low"],1e-12)
def upper_wick(c): return c["high"]-max(c["open"],c["close"])
def lower_wick(c): return min(c["open"],c["close"])-c["low"]
def bullish(c): return c["close"]>c["open"]
def bearish(c): return c["close"]<c["open"]


def meaningful(c):
    return c["close"]>0 and rng(c)/c["close"] >= MIN_CANDLE_RANGE_PCT


def bull_engulf(prev,cur):
    return bearish(prev) and bullish(cur) and cur["open"]<=prev["close"] and cur["close"]>=prev["open"] and body(cur)>body(prev) and meaningful(cur)


def bear_engulf(prev,cur):
    return bullish(prev) and bearish(cur) and cur["open"]>=prev["close"] and cur["close"]<=prev["open"] and body(cur)>body(prev) and meaningful(cur)


def bull_pin(c):
    b=max(body(c),1e-12)
    return meaningful(c) and lower_wick(c)>=2.2*b and upper_wick(c)<=0.8*b and c["close"]>=c["low"]+0.65*rng(c)


def bear_pin(c):
    b=max(body(c),1e-12)
    return meaningful(c) and upper_wick(c)>=2.2*b and lower_wick(c)<=0.8*b and c["close"]<=c["low"]+0.35*rng(c)


def inside_bar(mother,inside):
    return inside["high"]<mother["high"] and inside["low"]>mother["low"]


def near_level(price,level):
    return level>0 and abs(price-level)/level <= STRUCTURE_TOLERANCE_PCT


def ema(values, period):
    if len(values) < period:
        return None
    alpha = 2.0 / (period + 1.0)
    value = sum(values[:period]) / period
    for x in values[period:]:
        value = alpha * x + (1.0 - alpha) * value
    return value


def detect_signal(main_closed, structure_closed):
    if len(main_closed)<25 or len(structure_closed)<35:
        return {"side":"WAIT","setup":"NONE","score":0,"reasons":["Not enough candles"]}

    c3,c2,c1 = main_closed[-3],main_closed[-2],main_closed[-1]
    support=min(c["low"] for c in structure_closed[-30:])
    resistance=max(c["high"] for c in structure_closed[-30:])
    swing_low=min(c["low"] for c in main_closed[-22:-2])
    swing_high=max(c["high"] for c in main_closed[-22:-2])
    avg_volume=sum(c["volume"] for c in main_closed[-22:-2])/20
    volume_ratio=c1["volume"]/avg_volume if avg_volume>0 else 0.0
    structure_closes=[c["close"] for c in structure_closed]
    ema20=ema(structure_closes,20); ema50=ema(structure_closes,50)
    trend_strength=abs(ema20-ema50)/c1["close"] if ema20 and ema50 else 0.0
    trend="LONG" if ema20 and ema50 and ema20>ema50 else "SHORT" if ema20 and ema50 and ema20<ema50 else "MIXED"
    candidates=[]

    if bull_engulf(c3,c2) and c1["close"]>c2["high"]:
        score=3; reasons=["Bullish engulfing","Confirmation above pattern high"]
        if near_level(c2["low"],support) or near_level(c2["low"],swing_low): score+=2; reasons.append("Support/swing rejection")
        if body(c2)/rng(c2)>=0.60: score+=1; reasons.append("Strong body")
        candidates.append({"side":"LONG","setup":"BULLISH_ENGULFING","score":score,"pattern_low":min(c2["low"],c1["low"]),"pattern_high":max(c2["high"],c1["high"]),"entry":c1["close"],"candle_time":c1["open_time"],"reasons":reasons})

    if bear_engulf(c3,c2) and c1["close"]<c2["low"]:
        score=3; reasons=["Bearish engulfing","Confirmation below pattern low"]
        if near_level(c2["high"],resistance) or near_level(c2["high"],swing_high): score+=2; reasons.append("Resistance/swing rejection")
        if body(c2)/rng(c2)>=0.60: score+=1; reasons.append("Strong body")
        candidates.append({"side":"SHORT","setup":"BEARISH_ENGULFING","score":score,"pattern_low":min(c2["low"],c1["low"]),"pattern_high":max(c2["high"],c1["high"]),"entry":c1["close"],"candle_time":c1["open_time"],"reasons":reasons})

    if bull_pin(c2) and c1["close"]>c2["high"]:
        score=3; reasons=["Bullish pin bar","Confirmation above pin high"]
        if near_level(c2["low"],support) or near_level(c2["low"],swing_low): score+=2; reasons.append("Pin at support/swing low")
        candidates.append({"side":"LONG","setup":"BULLISH_PINBAR","score":score,"pattern_low":min(c2["low"],c1["low"]),"pattern_high":max(c2["high"],c1["high"]),"entry":c1["close"],"candle_time":c1["open_time"],"reasons":reasons})

    if bear_pin(c2) and c1["close"]<c2["low"]:
        score=3; reasons=["Bearish pin bar","Confirmation below pin low"]
        if near_level(c2["high"],resistance) or near_level(c2["high"],swing_high): score+=2; reasons.append("Pin at resistance/swing high")
        candidates.append({"side":"SHORT","setup":"BEARISH_PINBAR","score":score,"pattern_low":min(c2["low"],c1["low"]),"pattern_high":max(c2["high"],c1["high"]),"entry":c1["close"],"candle_time":c1["open_time"],"reasons":reasons})

    if inside_bar(c3,c2):
        if c1["close"]>c3["high"] and bullish(c1):
            score=3; reasons=["Inside bar","Bullish breakout"]
            if near_level(c3["low"],support) or near_level(c3["low"],swing_low): score+=2; reasons.append("Support nearby")
            if body(c1)/rng(c1)>=0.60: score+=1; reasons.append("Strong breakout candle")
            candidates.append({"side":"LONG","setup":"INSIDE_BAR_BREAKOUT_LONG","score":score,"pattern_low":min(c3["low"],c2["low"]),"pattern_high":c1["high"],"entry":c1["close"],"candle_time":c1["open_time"],"reasons":reasons})
        elif c1["close"]<c3["low"] and bearish(c1):
            score=3; reasons=["Inside bar","Bearish breakout"]
            if near_level(c3["high"],resistance) or near_level(c3["high"],swing_high): score+=2; reasons.append("Resistance nearby")
            if body(c1)/rng(c1)>=0.60: score+=1; reasons.append("Strong breakout candle")
            candidates.append({"side":"SHORT","setup":"INSIDE_BAR_BREAKOUT_SHORT","score":score,"pattern_low":c1["low"],"pattern_high":max(c3["high"],c2["high"]),"entry":c1["close"],"candle_time":c1["open_time"],"reasons":reasons})

    if not candidates:
        return {"side":"WAIT","setup":"NONE","score":0,"support":support,"resistance":resistance,"candle_time":c1["open_time"],"volume_ratio":volume_ratio,"trend":trend,"trend_strength":trend_strength,"reasons":["No confirmed candle setup"]}

    best=max(candidates,key=lambda x:x["score"])
    best["support"]=support; best["resistance"]=resistance
    best["volume_ratio"]=volume_ratio; best["trend"]=trend; best["trend_strength"]=trend_strength
    if best["setup"] not in ENABLED_SETUPS:
        best["side"]="WAIT"; best["reasons"].append("Setup disabled after results review")
    elif volume_ratio < MIN_VOLUME_RATIO:
        best["side"]="WAIT"; best["reasons"].append(f"Volume {volume_ratio:.2f}x < {MIN_VOLUME_RATIO:.2f}x")
    elif trend_strength < MIN_TREND_STRENGTH:
        best["side"]="WAIT"; best["reasons"].append("15m trend too weak / chop")
    elif best["side"] != trend:
        best["side"]="WAIT"; best["reasons"].append(f"Signal against 15m {trend} trend")
    if best["score"]<MIN_SCORE:
        best["side"]="WAIT"; best["reasons"].append(f"Score {best['score']} < {MIN_SCORE}")
    return best


def estimated_net_per_unit(side, entry_exec, exit_market):
    exit_exec=exit_market*(1-SLIPPAGE_RATE if side=="LONG" else 1+SLIPPAGE_RATE)
    gross=(exit_exec-entry_exec) if side=="LONG" else (entry_exec-exit_exec)
    return gross-(entry_exec+exit_exec)*FEE_RATE


def target_market_for_net_profit(side, entry_exec, target_net_per_unit):
    f=FEE_RATE; s=SLIPPAGE_RATE
    if side=="LONG":
        exit_exec=(target_net_per_unit+entry_exec*(1+f))/(1-f)
        return exit_exec/(1-s)
    exit_exec=(entry_exec*(1-f)-target_net_per_unit)/(1+f)
    return exit_exec/(1+s)


def open_position(signal):
    global paper_position,last_entry_candle
    market_entry=float(signal["entry"]); side=signal["side"]; buffer=market_entry*0.0002
    entry=market_entry*(1+SLIPPAGE_RATE if side=="LONG" else 1-SLIPPAGE_RATE)
    if side=="LONG":
        stop=float(signal["pattern_low"])-buffer
    else:
        stop=float(signal["pattern_high"])+buffer
    net_loss_per_unit=-estimated_net_per_unit(side,entry,stop)
    if net_loss_per_unit<=0: return False
    tp=target_market_for_net_profit(side,entry,net_loss_per_unit*RISK_REWARD)
    risk_usdt=paper_balance*RISK_PER_TRADE
    qty=min(risk_usdt/net_loss_per_unit, paper_balance*MAX_NOTIONAL_SHARE/entry)
    if qty<=0: return False
    paper_position={"side":side,"setup":signal["setup"],"score":int(signal["score"]),"entry_price":entry,"qty":qty,"stop_loss":stop,"take_profit":tp,"risk_usdt":qty*net_loss_per_unit,"breakeven_moved":False,"entry_time":datetime.now(timezone.utc).isoformat(),"entry_candle":int(signal["candle_time"]),"reasons":signal.get("reasons",[])}
    last_entry_candle=int(signal["candle_time"]); save_state(); return True


def close_position(exit_price,reason):
    global paper_balance,paper_position,cooldown_until,trade_history
    if not paper_position: return
    p=paper_position; entry=p["entry_price"]; qty=p["qty"]
    exit_exec=exit_price*(1-SLIPPAGE_RATE if p["side"]=="LONG" else 1+SLIPPAGE_RATE)
    gross=(exit_exec-entry)*qty if p["side"]=="LONG" else (entry-exit_exec)*qty
    fees=(entry*qty+exit_exec*qty)*FEE_RATE; net=gross-fees; paper_balance+=net
    t={"side":p["side"],"setup":p["setup"],"score":p["score"],"entry_price":entry,"exit_price":exit_exec,"qty":qty,"stop_loss":p["stop_loss"],"take_profit":p["take_profit"],"gross_pnl":gross,"fees":fees,"net_pnl":net,"reason":reason,"entry_time":p["entry_time"],"exit_time":datetime.now(timezone.utc).isoformat()}
    trade_history.insert(0,t); trade_history[:]=trade_history[:100]; save_trade(t)
    if net<0: cooldown_until=datetime.now(timezone.utc)+timedelta(minutes=COOLDOWN_AFTER_LOSS_MIN)
    paper_position=None; save_state()


def manage_position(price):
    if not paper_position: return
    p=paper_position
    opened=datetime.fromisoformat(p["entry_time"])
    age_minutes=(datetime.now(timezone.utc)-opened).total_seconds()/60
    current_net=estimated_net_per_unit(p["side"],p["entry_price"],price)*p["qty"]
    risk=float(p.get("risk_usdt",paper_balance*RISK_PER_TRADE))
    if not p.get("breakeven_moved") and current_net>=risk*BREAKEVEN_TRIGGER_R:
        p["stop_loss"]=target_market_for_net_profit(p["side"],p["entry_price"],0.0)
        p["breakeven_moved"]=True; save_state()
    if p["side"]=="LONG":
        if price<=p["stop_loss"]: close_position(price,"BREAK_EVEN" if p.get("breakeven_moved") else "STOP_LOSS")
        elif price>=p["take_profit"]: close_position(price,"TAKE_PROFIT")
    else:
        if price>=p["stop_loss"]: close_position(price,"BREAK_EVEN" if p.get("breakeven_moved") else "STOP_LOSS")
        elif price<=p["take_profit"]: close_position(price,"TAKE_PROFIT")
    if paper_position and age_minutes>=MAX_TRADE_MINUTES:
        close_position(price,"TIME_EXIT")


def unrealized(price):
    if not paper_position: return 0.0
    p=paper_position
    return estimated_net_per_unit(p["side"],p["entry_price"],price)*p["qty"]


async def analyze_once():
    global last_signal
    async with httpx.AsyncClient() as client:
        main_raw,struct_raw,price=await asyncio.gather(get_klines(client,MAIN_INTERVAL),get_klines(client,STRUCTURE_INTERVAL),get_live_price(client))
    main=[candle(k) for k in main_raw][:-1]; struct=[candle(k) for k in struct_raw][:-1]
    had=paper_position is not None; manage_position(price)
    signal=detect_signal(main,struct); last_signal=signal
    cd=bool(cooldown_until and datetime.now(timezone.utc)<cooldown_until); opened=False
    if not had and paper_position is None and not cd and signal.get("side") in ("LONG","SHORT") and signal.get("score",0)>=MIN_SCORE and signal.get("candle_time")!=last_entry_candle:
        opened=open_position(signal)
    upnl=unrealized(price)
    return {"bot":"XRP Bot V8 Candle Fixed","mode":TRADING_MODE,"symbol":SYMBOL,"price":price,"balance":paper_balance,"equity":paper_balance+upnl,"unrealized_pnl":upnl,"position":paper_position,"signal":signal,"opened_this_cycle":opened,"cooldown_until":cooldown_until.isoformat() if cooldown_until else None,"fee_rate":FEE_RATE,"slippage_rate":SLIPPAGE_RATE,"risk_per_trade":RISK_PER_TRADE,"risk_reward":RISK_REWARD,"min_score":MIN_SCORE,"enabled_setups":sorted(ENABLED_SETUPS),"history":trade_history[:30],"time":datetime.now(timezone.utc).isoformat()}


async def bot_loop():
    while True:
        try: await analyze_once()
        except Exception as e: print("BOT LOOP ERROR",repr(e))
        await asyncio.sleep(15)


@app.on_event("startup")
async def startup():
    global bot_task
    try: init_db(); load_state()
    except Exception as e: print("DB STARTUP ERROR",repr(e))
    bot_task=asyncio.create_task(bot_loop())


@app.on_event("shutdown")
async def shutdown():
    if bot_task:
        bot_task.cancel()
        try: await bot_task
        except asyncio.CancelledError: pass


@app.get("/health")
async def health():
    return {"status":"ok","bot":"XRP BOT V8 CANDLE FIXED","mode":TRADING_MODE,"symbol":SYMBOL,"strategy":"ENGULFING + 15m TREND + VOLUME","risk_reward":"NET 1:2"}


@app.get("/analyze")
async def analyze():
    try: return JSONResponse(await analyze_once())
    except Exception as e: return JSONResponse({"ok":False,"error":str(e)},status_code=500)


@app.get("/",response_class=HTMLResponse)
async def dashboard():
    return '''<!doctype html>
<html lang="cs">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>XRP V8 Candle Fixed</title>
<style>
:root{--bg:#07111f;--panel:#0f1b2d;--panel2:#132238;--line:#243650;--text:#f4f7fb;--muted:#8ea1b8;--green:#21d19f;--red:#ff647c;--amber:#f8c55c;--blue:#6ea8fe;--shadow:0 12px 35px rgba(0,0,0,.24)}
*{box-sizing:border-box}body{margin:0;background:linear-gradient(180deg,#07111f 0%,#091525 100%);color:var(--text);font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif}.wrap{max-width:980px;margin:auto;padding:18px 14px 34px}.top{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;margin:4px 2px 18px}.title{font-size:24px;font-weight:800;letter-spacing:-.4px}.subtitle{font-size:12px;color:var(--muted);margin-top:4px}.badge{padding:7px 10px;border:1px solid var(--line);background:#0d1929;border-radius:999px;font-size:11px;color:#b8c6d8;white-space:nowrap}.hero{background:linear-gradient(145deg,#13243a,#0e1a2c);border:1px solid #20344f;border-radius:22px;padding:18px;box-shadow:var(--shadow);margin-bottom:14px}.heroRow{display:flex;justify-content:space-between;align-items:center;gap:12px}.signal{font-size:30px;font-weight:900;letter-spacing:.3px}.setup{font-size:13px;color:#b9c6d6;margin-top:3px}.pnl{text-align:right}.pnlLabel{font-size:11px;color:var(--muted)}.pnlValue{font-size:26px;font-weight:900;margin-top:2px}.long{color:var(--green)}.short{color:var(--red)}.wait{color:var(--amber)}.pos{color:var(--green)}.neg{color:var(--red)}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:14px}.metric{background:var(--panel);border:1px solid #1d3048;border-radius:16px;padding:13px 12px}.metric .k{font-size:11px;color:var(--muted);margin-bottom:5px}.metric .v{font-size:18px;font-weight:800;white-space:nowrap}.card{background:var(--panel);border:1px solid #1d3048;border-radius:18px;padding:16px;margin-bottom:14px;box-shadow:0 7px 22px rgba(0,0,0,.14)}.card h3{margin:0 0 14px;font-size:16px}.positionGrid{display:grid;grid-template-columns:repeat(2,1fr);gap:9px}.item{background:#0b1727;border:1px solid #1c2c43;border-radius:13px;padding:11px}.item .k{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.6px}.item .v{font-size:16px;font-weight:800;margin-top:4px}.riskbar{height:8px;background:#1a2b42;border-radius:10px;overflow:hidden;margin:14px 0 6px}.riskfill{height:100%;width:50%;background:linear-gradient(90deg,var(--red),var(--amber),var(--green));border-radius:10px}.barlabels{display:flex;justify-content:space-between;font-size:10px;color:var(--muted)}.reasons{display:grid;gap:8px}.reason{background:#0b1727;border:1px solid #1b2c42;border-radius:12px;padding:10px 11px;font-size:13px}.reason:before{content:'✓';color:var(--green);font-weight:900;margin-right:8px}.empty{color:var(--muted);font-size:13px;padding:4px 0}.history{display:grid;gap:9px}.trade{background:#0b1727;border:1px solid #1c2c43;border-radius:14px;padding:11px 12px}.tradeTop{display:flex;justify-content:space-between;gap:10px}.tradeSide{font-weight:900;font-size:13px}.tradeSetup{font-size:11px;color:var(--muted);margin-top:2px}.tradePnl{font-size:16px;font-weight:900}.tradeMeta{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:10px;font-size:10px;color:var(--muted)}.tradeMeta b{display:block;color:#dbe5f2;font-size:12px;margin-top:2px}.footer{font-size:10px;color:#61758d;text-align:center;padding:6px}.dot{display:inline-block;width:7px;height:7px;background:var(--green);border-radius:50%;margin-right:6px;box-shadow:0 0 0 4px rgba(33,209,159,.1)}@media(max-width:620px){.wrap{padding:13px 10px 28px}.title{font-size:21px}.grid{grid-template-columns:repeat(2,1fr)}.metric .v{font-size:16px}.hero{padding:16px}.signal{font-size:27px}.pnlValue{font-size:22px}.positionGrid{grid-template-columns:repeat(2,1fr)}}
</style>
</head>
<body>
<div class="wrap">
  <div class="top"><div><div class="title">XRP Bot V8 Candle Fixed</div><div class="subtitle"><span class="dot"></span>ENGULFING + 15m trend + volume · PAPER · auto refresh 15 s</div></div><div class="badge" id="clock">--:--</div></div>

  <section class="hero">
    <div class="heroRow"><div><div id="heroSignal" class="signal wait">WAIT</div><div id="heroSetup" class="setup">Čekám na potvrzenou svíčkovou formaci</div></div><div class="pnl"><div class="pnlLabel">NEREALIZOVANÝ P&L</div><div id="heroPnl" class="pnlValue">0.00 USDT</div></div></div>
  </section>

  <div class="grid">
    <div class="metric"><div class="k">XRP CENA</div><div id="price" class="v">-</div></div>
    <div class="metric"><div class="k">BALANCE</div><div id="balance" class="v">-</div></div>
    <div class="metric"><div class="k">EQUITY</div><div id="equity" class="v">-</div></div>
    <div class="metric"><div class="k">SCORE</div><div id="score" class="v">-</div></div>
    <div class="metric"><div class="k">RISK / TRADE</div><div id="risk" class="v">-</div></div>
    <div class="metric"><div class="k">RISK : REWARD</div><div id="rr" class="v">-</div></div>
  </div>

  <section class="card"><h3>Aktuální pozice</h3><div id="positionBox" class="empty">Žádná otevřená pozice</div></section>
  <section class="card"><h3>Proč bot rozhodl</h3><div id="reasons" class="reasons"><div class="empty">Načítám…</div></div></section>
  <section class="card"><h3>Poslední obchody</h3><div id="history" class="history"><div class="empty">Zatím žádné uzavřené obchody</div></div></section>
  <div class="footer">V8 Candle Fixed · pouze engulfing · NET R:R po nákladech</div>
</div>
<script>
const fmt=(v,d=4)=>v==null?'-':Number(v).toFixed(d);
const cls=v=>Number(v)>0?'pos':Number(v)<0?'neg':'';
const esc=s=>String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
function setupName(s){return String(s||'NONE').replaceAll('_',' ')}
function progress(p,price){if(!p)return 50;const lo=Math.min(p.stop_loss,p.take_profit),hi=Math.max(p.stop_loss,p.take_profit);if(hi<=lo)return 50;return Math.max(0,Math.min(100,(price-lo)/(hi-lo)*100))}
function renderPosition(p,price){const box=document.getElementById('positionBox');if(!p){box.className='empty';box.innerHTML='Žádná otevřená pozice';return}const sideClass=p.side==='LONG'?'long':'short';const pr=progress(p,price);box.className='';box.innerHTML=`<div class="positionGrid"><div class="item"><div class="k">Směr</div><div class="v ${sideClass}">${esc(p.side)}</div></div><div class="item"><div class="k">Setup</div><div class="v">${esc(setupName(p.setup))}</div></div><div class="item"><div class="k">Vstup</div><div class="v">${fmt(p.entry_price,5)}</div></div><div class="item"><div class="k">Aktuální cena</div><div class="v">${fmt(price,5)}</div></div><div class="item"><div class="k">Stop loss</div><div class="v short">${fmt(p.stop_loss,5)}</div></div><div class="item"><div class="k">Take profit</div><div class="v long">${fmt(p.take_profit,5)}</div></div><div class="item"><div class="k">Množství</div><div class="v">${fmt(p.qty,0)} XRP</div></div><div class="item"><div class="k">Score</div><div class="v">${p.score??'-'}</div></div></div><div class="riskbar"><div class="riskfill" style="width:${pr}%"></div></div><div class="barlabels"><span>SL ${fmt(p.stop_loss,4)}</span><span>CENA ${fmt(price,4)}</span><span>TP ${fmt(p.take_profit,4)}</span></div>`}
function renderHistory(arr){const h=document.getElementById('history');if(!arr?.length){h.innerHTML='<div class="empty">Zatím žádné uzavřené obchody</div>';return}h.innerHTML=arr.slice(0,12).map(t=>`<div class="trade"><div class="tradeTop"><div><div class="tradeSide ${t.side==='LONG'?'long':'short'}">${esc(t.side)}</div><div class="tradeSetup">${esc(setupName(t.setup))} · score ${t.score??'-'}</div></div><div class="tradePnl ${cls(t.net_pnl)}">${Number(t.net_pnl)>=0?'+':''}${fmt(t.net_pnl,2)} USDT</div></div><div class="tradeMeta"><span>ENTRY<b>${fmt(t.entry_price,5)}</b></span><span>EXIT<b>${fmt(t.exit_price,5)}</b></span><span>FEE<b>${fmt(t.fees,2)}</b></span></div></div>`).join('')}
async function refresh(){try{const r=await fetch('/analyze',{cache:'no-store'});const d=await r.json();const s=d.position?.side||d.signal?.side||'WAIT';const setup=d.position?.setup||d.signal?.setup||'NONE';heroSignal.textContent=s;heroSignal.className='signal '+(s==='LONG'?'long':s==='SHORT'?'short':'wait');heroSetup.textContent=s==='WAIT'?'Čekám na potvrzenou svíčkovou formaci':setupName(setup);heroPnl.textContent=(Number(d.unrealized_pnl)>=0?'+':'')+fmt(d.unrealized_pnl,2)+' USDT';heroPnl.className='pnlValue '+cls(d.unrealized_pnl);price.textContent=fmt(d.price,5);balance.textContent=fmt(d.balance,2)+' USDT';equity.textContent=fmt(d.equity,2)+' USDT';score.textContent=(d.position?.score??d.signal?.score??0)+' / '+(d.min_score??'-')+' min';risk.textContent=fmt((d.risk_per_trade||0)*100,2)+' %';rr.textContent='1 : '+fmt(d.risk_reward,1);renderPosition(d.position,d.price);const rs=d.position?.reasons||d.signal?.reasons||[];reasons.innerHTML=rs.length?rs.map(x=>`<div class="reason">${esc(x)}</div>`).join(''):'<div class="empty">Bez nového potvrzeného setupu</div>';renderHistory(d.history||[]);clock.textContent=new Date().toLocaleTimeString('cs-CZ',{hour:'2-digit',minute:'2-digit'});}catch(e){console.error(e);heroSetup.textContent='Chyba načtení dat';}}
refresh();setInterval(refresh,15000);
</script>
</body></html>'''


if __name__=="__main__":
    import uvicorn
    uvicorn.run("app_v8_candle:app",host="0.0.0.0",port=int(os.getenv("PORT","10000")))
