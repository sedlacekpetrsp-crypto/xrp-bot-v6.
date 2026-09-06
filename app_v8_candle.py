import os
import json
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

import httpx
import psycopg
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(title="XRP Bot V8 Candle")

SYMBOL = os.getenv("SYMBOL", "XRPUSDT")
BINANCE_API = os.getenv("BINANCE_API", "https://data-api.binance.vision")
TRADING_MODE = "PAPER"
STARTING_BALANCE = float(os.getenv("STARTING_BALANCE", "10000"))
RISK_PER_TRADE = float(os.getenv("RISK_PER_TRADE", "0.005"))
RISK_REWARD = float(os.getenv("RISK_REWARD", "2.0"))
FEE_RATE = float(os.getenv("FEE_RATE", "0.0005"))
MIN_SCORE = int(os.getenv("MIN_SCORE", "4"))
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
    return {"open_time":int(k[0]),"open":float(k[1]),"high":float(k[2]),"low":float(k[3]),"close":float(k[4])}


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


def detect_signal(main_closed, structure_closed):
    if len(main_closed)<25 or len(structure_closed)<35:
        return {"side":"WAIT","setup":"NONE","score":0,"reasons":["Not enough candles"]}

    c3,c2,c1 = main_closed[-3],main_closed[-2],main_closed[-1]
    support=min(c["low"] for c in structure_closed[-30:])
    resistance=max(c["high"] for c in structure_closed[-30:])
    swing_low=min(c["low"] for c in main_closed[-22:-2])
    swing_high=max(c["high"] for c in main_closed[-22:-2])
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
        return {"side":"WAIT","setup":"NONE","score":0,"support":support,"resistance":resistance,"candle_time":c1["open_time"],"reasons":["No confirmed candle setup"]}

    best=max(candidates,key=lambda x:x["score"])
    best["support"]=support; best["resistance"]=resistance
    if best["score"]<MIN_SCORE:
        best["side"]="WAIT"; best["reasons"].append(f"Score {best['score']} < {MIN_SCORE}")
    return best


def open_position(signal):
    global paper_position,last_entry_candle
    entry=float(signal["entry"]); side=signal["side"]; buffer=entry*0.0002
    if side=="LONG":
        stop=float(signal["pattern_low"])-buffer; unit=entry-stop; tp=entry+RISK_REWARD*unit
    else:
        stop=float(signal["pattern_high"])+buffer; unit=stop-entry; tp=entry-RISK_REWARD*unit
    if unit<=0: return False
    risk_usdt=paper_balance*RISK_PER_TRADE
    qty=min(risk_usdt/unit, paper_balance/entry)
    if qty<=0: return False
    paper_position={"side":side,"setup":signal["setup"],"score":int(signal["score"]),"entry_price":entry,"qty":qty,"stop_loss":stop,"take_profit":tp,"entry_time":datetime.now(timezone.utc).isoformat(),"entry_candle":int(signal["candle_time"]),"reasons":signal.get("reasons",[])}
    last_entry_candle=int(signal["candle_time"]); save_state(); return True


def close_position(exit_price,reason):
    global paper_balance,paper_position,cooldown_until,trade_history
    if not paper_position: return
    p=paper_position; entry=p["entry_price"]; qty=p["qty"]
    gross=(exit_price-entry)*qty if p["side"]=="LONG" else (entry-exit_price)*qty
    fees=(entry*qty+exit_price*qty)*FEE_RATE; net=gross-fees; paper_balance+=net
    t={"side":p["side"],"setup":p["setup"],"score":p["score"],"entry_price":entry,"exit_price":exit_price,"qty":qty,"stop_loss":p["stop_loss"],"take_profit":p["take_profit"],"gross_pnl":gross,"fees":fees,"net_pnl":net,"reason":reason,"entry_time":p["entry_time"],"exit_time":datetime.now(timezone.utc).isoformat()}
    trade_history.insert(0,t); trade_history[:]=trade_history[:100]; save_trade(t)
    if net<0: cooldown_until=datetime.now(timezone.utc)+timedelta(minutes=COOLDOWN_AFTER_LOSS_MIN)
    paper_position=None; save_state()


def manage_position(price):
    if not paper_position: return
    p=paper_position
    if p["side"]=="LONG":
        if price<=p["stop_loss"]: close_position(price,"STOP_LOSS")
        elif price>=p["take_profit"]: close_position(price,"TAKE_PROFIT")
    else:
        if price>=p["stop_loss"]: close_position(price,"STOP_LOSS")
        elif price<=p["take_profit"]: close_position(price,"TAKE_PROFIT")


def unrealized(price):
    if not paper_position: return 0.0
    p=paper_position; gross=(price-p["entry_price"])*p["qty"] if p["side"]=="LONG" else (p["entry_price"]-price)*p["qty"]
    return gross-(p["entry_price"]*p["qty"]+price*p["qty"])*FEE_RATE


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
    return {"bot":"XRP Bot V8 Candle","mode":TRADING_MODE,"symbol":SYMBOL,"price":price,"balance":paper_balance,"equity":paper_balance+upnl,"unrealized_pnl":upnl,"position":paper_position,"signal":signal,"opened_this_cycle":opened,"cooldown_until":cooldown_until.isoformat() if cooldown_until else None,"fee_rate":FEE_RATE,"risk_per_trade":RISK_PER_TRADE,"risk_reward":RISK_REWARD,"min_score":MIN_SCORE,"history":trade_history[:30],"time":datetime.now(timezone.utc).isoformat()}


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
    return {"status":"ok","bot":"XRP BOT V8 CANDLE","mode":TRADING_MODE,"symbol":SYMBOL,"strategy":"CANDLE / PRICE ACTION ONLY"}


@app.get("/analyze")
async def analyze():
    try: return JSONResponse(await analyze_once())
    except Exception as e: return JSONResponse({"ok":False,"error":str(e)},status_code=500)


@app.get("/",response_class=HTMLResponse)
async def dashboard():
    return '''<!doctype html><html lang="cs"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>XRP V8 Candle</title><style>body{font-family:Arial;background:#111827;color:#f3f4f6;margin:0;padding:18px}.wrap{max-width:1000px;margin:auto}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px}.card{background:#1f2937;border-radius:14px;padding:14px;margin-bottom:12px}.big{font-size:25px;font-weight:700}.muted{color:#9ca3af}.long{color:#34d399}.short{color:#fb7185}.wait{color:#fbbf24}table{width:100%;border-collapse:collapse;font-size:13px}th,td{padding:8px;border-bottom:1px solid #374151;text-align:left}</style></head><body><div class="wrap"><h1>XRP Bot V8 Candle</h1><div class="muted">Price Action ONLY · PAPER</div><div class="grid" style="margin:16px 0"><div class="card"><div class="muted">Cena</div><div id="price" class="big">-</div></div><div class="card"><div class="muted">Signál</div><div id="signal" class="big">-</div></div><div class="card"><div class="muted">Setup / Score</div><div id="setup" class="big">-</div></div><div class="card"><div class="muted">Balance</div><div id="balance" class="big">-</div></div><div class="card"><div class="muted">Equity</div><div id="equity" class="big">-</div></div><div class="card"><div class="muted">Unrealized</div><div id="upnl" class="big">-</div></div></div><div class="card"><h3>Aktuální pozice</h3><pre id="position">-</pre></div><div class="card"><h3>Rozhodnutí</h3><div id="reasons">-</div></div><div class="card"><h3>Historie</h3><div style="overflow:auto"><table><thead><tr><th>Side</th><th>Setup</th><th>Score</th><th>Entry</th><th>Exit</th><th>Net P&L</th><th>Fees</th><th>Důvod</th></tr></thead><tbody id="history"></tbody></table></div></div></div><script>function n(v,d=4){return v==null?'-':Number(v).toFixed(d)}async function refresh(){try{const r=await fetch('/analyze');const d=await r.json();price.textContent=n(d.price,5);balance.textContent=n(d.balance,2)+' USDT';equity.textContent=n(d.equity,2)+' USDT';upnl.textContent=n(d.unrealized_pnl,2)+' USDT';const s=d.signal?.side||'WAIT';signal.textContent=s;signal.className='big '+(s==='LONG'?'long':s==='SHORT'?'short':'wait');setup.textContent=(d.signal?.setup||'NONE')+' / '+(d.signal?.score??0);position.textContent=d.position?JSON.stringify(d.position,null,2):'Žádná otevřená pozice';reasons.innerHTML=(d.signal?.reasons||[]).map(x=>'<div>• '+x+'</div>').join('')||'-';history.innerHTML='';(d.history||[]).forEach(t=>{const tr=document.createElement('tr');tr.innerHTML=`<td>${t.side}</td><td>${t.setup}</td><td>${t.score}</td><td>${n(t.entry_price,5)}</td><td>${n(t.exit_price,5)}</td><td>${n(t.net_pnl,2)}</td><td>${n(t.fees,2)}</td><td>${t.reason||''}</td>`;history.appendChild(tr)})}catch(e){console.error(e)}}refresh();setInterval(refresh,15000)</script></body></html>'''


if __name__=="__main__":
    import uvicorn
    uvicorn.run("app_v8_candle:app",host="0.0.0.0",port=int(os.getenv("PORT","10000")))
