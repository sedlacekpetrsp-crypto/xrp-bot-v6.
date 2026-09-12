import os
import json
import asyncio
from datetime import datetime, timezone, timedelta

import httpx
import psycopg
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

# ============================================================
# V9 BEST-OF — PAPER ONLY
# Built from the strongest recurring ideas across V5/V6/V7/V8/V8.1:
# 1h market direction + 15m confirmation + 5m BREAKOUT / TREND_PULLBACK
# + volume + confirmation candle + realistic fees/slippage.
# ============================================================

app = FastAPI(title="V9 Best-Of Paper Bot")

SYMBOLS = ["XRPUSDT", "BTCUSDT", "ETHUSDT", "SOLUSDT"]
BINANCE_API = os.getenv("BINANCE_API", "https://data-api.binance.vision")
DATABASE_URL = os.getenv("DATABASE_URL")
TRADING_MODE = "PAPER"
STARTING_BALANCE = float(os.getenv("STARTING_BALANCE", "10000"))

RISK_PER_TRADE = float(os.getenv("RISK_PER_TRADE", "0.003"))
NET_RISK_REWARD = float(os.getenv("NET_RISK_REWARD", "1.60"))
FEE_RATE = float(os.getenv("FEE_RATE", "0.0005"))
SLIPPAGE_RATE = float(os.getenv("SLIPPAGE_RATE", "0.0002"))
MAX_NOTIONAL_SHARE = float(os.getenv("MAX_NOTIONAL_SHARE", "0.35"))
MAX_OPEN_POSITIONS = int(os.getenv("MAX_OPEN_POSITIONS", "2"))

EMA_FAST = 20
EMA_SLOW = 50
EMA_1H_SLOW = 200
BREAKOUT_LOOKBACK = 20
VOLUME_LOOKBACK = 20
MIN_VOLUME_BREAKOUT = float(os.getenv("MIN_VOLUME_BREAKOUT", "1.35"))
MIN_VOLUME_PULLBACK = float(os.getenv("MIN_VOLUME_PULLBACK", "1.05"))
MIN_1H_TREND_STRENGTH = float(os.getenv("MIN_1H_TREND_STRENGTH", "0.0015"))
MIN_15M_TREND_STRENGTH = float(os.getenv("MIN_15M_TREND_STRENGTH", "0.0010"))
BREAKOUT_BUFFER_RATE = float(os.getenv("BREAKOUT_BUFFER_RATE", "0.0006"))
PULLBACK_TOLERANCE_RATE = float(os.getenv("PULLBACK_TOLERANCE_RATE", "0.0025"))
MIN_BODY_RATIO = float(os.getenv("MIN_BODY_RATIO", "0.55"))
MAX_SIGNAL_RANGE_RATE = float(os.getenv("MAX_SIGNAL_RANGE_RATE", "0.012"))

ATR_PERIOD = 14
ATR_STOP_MULT = float(os.getenv("ATR_STOP_MULT", "1.20"))
MIN_STOP_RATE = float(os.getenv("MIN_STOP_RATE", "0.0035"))
MAX_STOP_RATE = float(os.getenv("MAX_STOP_RATE", "0.015"))
BREAKEVEN_TRIGGER_R = float(os.getenv("BREAKEVEN_TRIGGER_R", "0.80"))
MAX_TRADE_MINUTES = int(os.getenv("MAX_TRADE_MINUTES", "120"))
COOLDOWN_AFTER_WIN_MIN = int(os.getenv("COOLDOWN_AFTER_WIN_MIN", "5"))
COOLDOWN_AFTER_LOSS_MIN = int(os.getenv("COOLDOWN_AFTER_LOSS_MIN", "20"))
SIGNAL_SCAN_SECONDS = int(os.getenv("SIGNAL_SCAN_SECONDS", "60"))
POSITION_LOOP_SECONDS = int(os.getenv("POSITION_LOOP_SECONDS", "5"))

TRADE_TABLE = "v9_trades"
STATE_TABLE = "v9_state"

paper_balance = STARTING_BALANCE
positions = {}
trade_history = []
last_entry_candle = {}
cooldown_until = {}
last_analysis = {}
bot_task = None
http_client = None
last_error = None
last_cycle_at = None


def utcnow():
    return datetime.now(timezone.utc)


def get_db():
    return psycopg.connect(DATABASE_URL) if DATABASE_URL else None


def init_db():
    if not DATABASE_URL:
        return
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {TRADE_TABLE}(
                    id SERIAL PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    setup TEXT NOT NULL,
                    entry_market DOUBLE PRECISION NOT NULL,
                    entry_price DOUBLE PRECISION NOT NULL,
                    exit_market DOUBLE PRECISION NOT NULL,
                    exit_price DOUBLE PRECISION NOT NULL,
                    qty DOUBLE PRECISION NOT NULL,
                    stop_loss DOUBLE PRECISION NOT NULL,
                    take_profit DOUBLE PRECISION NOT NULL,
                    gross_pnl DOUBLE PRECISION NOT NULL,
                    fees DOUBLE PRECISION NOT NULL,
                    slippage DOUBLE PRECISION NOT NULL,
                    pnl DOUBLE PRECISION NOT NULL,
                    reason TEXT,
                    opened_at TIMESTAMPTZ,
                    closed_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {STATE_TABLE}(
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
        "positions": positions,
        "last_entry_candle": last_entry_candle,
        "cooldown_until": cooldown_until,
    }
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO {STATE_TABLE}(id,state) VALUES(1,%s::jsonb) "
                f"ON CONFLICT(id) DO UPDATE SET state=EXCLUDED.state",
                (json.dumps(state),),
            )
        conn.commit()


def load_state():
    global paper_balance, positions, trade_history, last_entry_candle, cooldown_until
    if not DATABASE_URL:
        return
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT state FROM {STATE_TABLE} WHERE id=1")
            row = cur.fetchone()
            if row:
                s = row[0] or {}
                paper_balance = float(s.get("paper_balance", STARTING_BALANCE))
                positions = s.get("positions", {}) or {}
                last_entry_candle = s.get("last_entry_candle", {}) or {}
                cooldown_until = s.get("cooldown_until", {}) or {}
            cur.execute(f"""
                SELECT symbol,side,setup,entry_market,entry_price,exit_market,exit_price,
                       qty,stop_loss,take_profit,gross_pnl,fees,slippage,pnl,reason,opened_at,closed_at
                FROM {TRADE_TABLE} ORDER BY id DESC LIMIT 500
            """)
            rows = cur.fetchall()
    trade_history = [{
        "symbol":r[0],"side":r[1],"setup":r[2],"entry_market":r[3],"entry_price":r[4],
        "exit_market":r[5],"exit_price":r[6],"qty":r[7],"stop_loss":r[8],"take_profit":r[9],
        "gross_pnl":r[10],"fees":r[11],"slippage":r[12],"pnl":r[13],"reason":r[14],
        "opened_at":r[15].isoformat() if r[15] else None,
        "closed_at":r[16].isoformat() if r[16] else None,
    } for r in rows]


def save_trade(t):
    if not DATABASE_URL:
        return
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                INSERT INTO {TRADE_TABLE}(
                    symbol,side,setup,entry_market,entry_price,exit_market,exit_price,qty,
                    stop_loss,take_profit,gross_pnl,fees,slippage,pnl,reason,opened_at,closed_at
                ) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                t["symbol"],t["side"],t["setup"],t["entry_market"],t["entry_price"],
                t["exit_market"],t["exit_price"],t["qty"],t["stop_loss"],t["take_profit"],
                t["gross_pnl"],t["fees"],t["slippage"],t["pnl"],t["reason"],
                t["opened_at"],t["closed_at"],
            ))
        conn.commit()


def ema(values, period):
    if len(values) < period:
        return None
    alpha = 2.0 / (period + 1.0)
    value = sum(values[:period]) / period
    for x in values[period:]:
        value = alpha * x + (1 - alpha) * value
    return value


def atr(highs, lows, closes, period=14):
    if len(closes) < period + 1:
        return None
    trs = [max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1])) for i in range(1,len(closes))]
    value = sum(trs[:period]) / period
    for x in trs[period:]:
        value = ((period-1)*value + x) / period
    return value


def body_ratio(k):
    o,h,l,c = map(float, (k[1],k[2],k[3],k[4]))
    r = max(h-l, 1e-12)
    return abs(c-o)/r


def bullish(k): return float(k[4]) > float(k[1])
def bearish(k): return float(k[4]) < float(k[1])


def volume_ratio(closed):
    if len(closed) < VOLUME_LOOKBACK + 1:
        return 0.0
    cur = float(closed[-1][5])
    prev = [float(x[5]) for x in closed[-(VOLUME_LOOKBACK+1):-1]]
    av = sum(prev)/len(prev) if prev else 0
    return cur/av if av else 0.0


async def api_get(path, params):
    global last_error
    r = await http_client.get(BINANCE_API + path, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


async def klines(symbol, interval, limit=250):
    return await api_get("/api/v3/klines", {"symbol":symbol,"interval":interval,"limit":limit})


async def live_price(symbol):
    d = await api_get("/api/v3/ticker/price", {"symbol":symbol})
    return float(d["price"])


def trend_state(closed, fast=EMA_FAST, slow=EMA_SLOW, extra_slow=None, min_strength=0.0):
    closes = [float(x[4]) for x in closed]
    if len(closes) < max(slow, extra_slow or slow) + 2:
        return "NEUTRAL", 0.0, None, None
    ef = ema(closes, fast)
    es = ema(closes, slow)
    ex = ema(closes, extra_slow) if extra_slow else None
    price = closes[-1]
    strength = abs(ef-es)/price if price else 0.0
    if strength < min_strength:
        return "NEUTRAL", strength, ef, es
    if extra_slow:
        if price > ef > es > ex:
            return "LONG", strength, ef, es
        if price < ef < es < ex:
            return "SHORT", strength, ef, es
    else:
        if price > ef > es:
            return "LONG", strength, ef, es
        if price < ef < es:
            return "SHORT", strength, ef, es
    return "NEUTRAL", strength, ef, es


def detect_setup(k5, trend_1h, trend_15m):
    closed = k5[:-1]
    if len(closed) < BREAKOUT_LOOKBACK + 30:
        return {"signal":"WAIT","setup":None,"reason":"málo dat"}
    cur = closed[-1]
    prev = closed[-2]
    o,h,l,c = map(float, (cur[1],cur[2],cur[3],cur[4]))
    rng = max(h-l,1e-12)
    br = body_ratio(cur)
    vr = volume_ratio(closed)
    range_rate = rng/max(c,1e-12)
    candle_time = int(cur[0])

    closes = [float(x[4]) for x in closed]
    e20 = ema(closes,20)
    e50 = ema(closes,50)
    recent = closed[-(BREAKOUT_LOOKBACK+1):-1]
    prior_high = max(float(x[2]) for x in recent)
    prior_low = min(float(x[3]) for x in recent)

    common_long = trend_1h == "LONG" and trend_15m == "LONG" and e20 and e50 and e20 > e50
    common_short = trend_1h == "SHORT" and trend_15m == "SHORT" and e20 and e50 and e20 < e50

    breakout_long = common_long and c > prior_high*(1+BREAKOUT_BUFFER_RATE) and bullish(cur) and br >= MIN_BODY_RATIO and vr >= MIN_VOLUME_BREAKOUT
    breakout_short = common_short and c < prior_low*(1-BREAKOUT_BUFFER_RATE) and bearish(cur) and br >= MIN_BODY_RATIO and vr >= MIN_VOLUME_BREAKOUT

    # Pullback requires a touch/retest of EMA20, then close back in trend direction.
    pullback_long = common_long and l <= e20*(1+PULLBACK_TOLERANCE_RATE) and c > e20 and bullish(cur) and c > float(prev[4]) and vr >= MIN_VOLUME_PULLBACK
    pullback_short = common_short and h >= e20*(1-PULLBACK_TOLERANCE_RATE) and c < e20 and bearish(cur) and c < float(prev[4]) and vr >= MIN_VOLUME_PULLBACK

    if range_rate > MAX_SIGNAL_RANGE_RATE:
        sig, setup, reason = "WAIT", None, "signální svíčka příliš velká"
    elif breakout_long:
        sig, setup, reason = "LONG", "BREAKOUT", "1h+15m trend, breakout, volume, silná svíčka"
    elif breakout_short:
        sig, setup, reason = "SHORT", "BREAKOUT", "1h+15m trend, breakout, volume, silná svíčka"
    elif pullback_long:
        sig, setup, reason = "LONG", "TREND_PULLBACK", "1h+15m trend, EMA20 retest, volume, potvrzení"
    elif pullback_short:
        sig, setup, reason = "SHORT", "TREND_PULLBACK", "1h+15m trend, EMA20 retest, volume, potvrzení"
    else:
        sig, setup, reason = "WAIT", None, "bez potvrzeného best-of setupu"

    return {
        "signal":sig,"setup":setup,"reason":reason,"candle_time":candle_time,
        "closed_price":c,"high":h,"low":l,"ema20_5m":e20,"ema50_5m":e50,
        "volume_ratio":vr,"body_ratio":br,"range_rate":range_rate,
    }


def in_cooldown(symbol):
    raw = cooldown_until.get(symbol)
    if not raw:
        return False
    try:
        return utcnow() < datetime.fromisoformat(raw)
    except Exception:
        return False


def execute_entry_price(market, side):
    return market*(1+SLIPPAGE_RATE) if side == "LONG" else market*(1-SLIPPAGE_RATE)


def execute_exit_price(market, side):
    return market*(1-SLIPPAGE_RATE) if side == "LONG" else market*(1+SLIPPAGE_RATE)


def open_position(symbol, analysis, market, atr_value):
    global positions
    side = analysis["signal"]
    entry = execute_entry_price(market, side)
    stop_distance = max(atr_value*ATR_STOP_MULT, entry*MIN_STOP_RATE)
    stop_distance = min(stop_distance, entry*MAX_STOP_RATE)
    stop = entry-stop_distance if side == "LONG" else entry+stop_distance

    # Target is sized from expected NET loss including round-trip fees/slippage.
    risk_budget = paper_balance*RISK_PER_TRADE
    max_qty = (paper_balance*MAX_NOTIONAL_SHARE)/entry
    approx_cost_per_qty = entry*(2*FEE_RATE + 2*SLIPPAGE_RATE)
    loss_per_qty = stop_distance + approx_cost_per_qty
    qty = min(risk_budget/max(loss_per_qty,1e-12), max_qty)
    if qty <= 0:
        return False

    target_net_per_qty = loss_per_qty*NET_RISK_REWARD
    raw_target_distance = target_net_per_qty + entry*(2*FEE_RATE + 2*SLIPPAGE_RATE)
    tp = entry+raw_target_distance if side == "LONG" else entry-raw_target_distance
    positions[symbol] = {
        "symbol":symbol,"side":side,"setup":analysis["setup"],"entry_market":market,"entry_price":entry,
        "qty":qty,"stop_loss":stop,"take_profit":tp,"initial_stop":stop,"initial_risk_distance":stop_distance,
        "opened_at":utcnow().isoformat(),"entry_candle":analysis["candle_time"],"breakeven":False,
    }
    last_entry_candle[symbol] = analysis["candle_time"]
    save_state()
    return True


def close_position(symbol, market, reason):
    global paper_balance
    p = positions.get(symbol)
    if not p:
        return
    side = p["side"]
    exit_price = execute_exit_price(market, side)
    qty = float(p["qty"])
    entry = float(p["entry_price"])
    gross = (exit_price-entry)*qty if side == "LONG" else (entry-exit_price)*qty
    fees = (entry+exit_price)*qty*FEE_RATE
    slippage = abs(entry-float(p["entry_market"]))*qty + abs(exit_price-market)*qty
    pnl = gross-fees
    paper_balance += pnl
    now = utcnow()
    t = {
        "symbol":symbol,"side":side,"setup":p["setup"],"entry_market":p["entry_market"],"entry_price":entry,
        "exit_market":market,"exit_price":exit_price,"qty":qty,"stop_loss":p["initial_stop"],"take_profit":p["take_profit"],
        "gross_pnl":gross,"fees":fees,"slippage":slippage,"pnl":pnl,"reason":reason,
        "opened_at":p["opened_at"],"closed_at":now.isoformat(),
    }
    trade_history.insert(0,t)
    save_trade(t)
    cooldown_until[symbol] = (now + timedelta(minutes=COOLDOWN_AFTER_WIN_MIN if pnl>0 else COOLDOWN_AFTER_LOSS_MIN)).isoformat()
    positions.pop(symbol,None)
    save_state()


async def analyze_symbol(symbol):
    global last_analysis
    k5,k15,k1h = await asyncio.gather(
        klines(symbol,"5m",250), klines(symbol,"15m",250), klines(symbol,"1h",250)
    )
    c5,c15,c1h = k5[:-1],k15[:-1],k1h[:-1]
    t1,str1,_,_ = trend_state(c1h,50,100,EMA_1H_SLOW,MIN_1H_TREND_STRENGTH)
    t15,str15,_,_ = trend_state(c15,EMA_FAST,EMA_SLOW,None,MIN_15M_TREND_STRENGTH)
    a = detect_setup(k5,t1,t15)
    highs=[float(x[2]) for x in c5]; lows=[float(x[3]) for x in c5]; closes=[float(x[4]) for x in c5]
    av=atr(highs,lows,closes,ATR_PERIOD)
    market=float(k5[-1][4])
    a.update({"symbol":symbol,"market_price":market,"trend_1h":t1,"trend_15m":t15,"trend_strength_1h":str1,"trend_strength_15m":str15,"atr":av})
    last_analysis[symbol]=a
    return a


async def manage_positions():
    for symbol in list(positions):
        try:
            market = await live_price(symbol)
            p = positions.get(symbol)
            if not p:
                continue
            side=p["side"]; entry=float(p["entry_price"]); stop=float(p["stop_loss"]); tp=float(p["take_profit"]); rd=float(p["initial_risk_distance"])
            favorable = (market-entry) if side=="LONG" else (entry-market)
            if not p.get("breakeven") and rd>0 and favorable >= rd*BREAKEVEN_TRIGGER_R:
                p["stop_loss"] = entry
                p["breakeven"] = True
                save_state()
                stop=entry
            hit_stop = market<=stop if side=="LONG" else market>=stop
            hit_tp = market>=tp if side=="LONG" else market<=tp
            opened=datetime.fromisoformat(p["opened_at"])
            timed = utcnow()-opened >= timedelta(minutes=MAX_TRADE_MINUTES)
            if hit_stop:
                close_position(symbol,market,"BREAKEVEN" if p.get("breakeven") else "STOP LOSS")
            elif hit_tp:
                close_position(symbol,market,"TAKE PROFIT")
            elif timed:
                close_position(symbol,market,"TIME EXIT")
        except Exception as e:
            print("MANAGE",symbol,e)


async def scan_entries():
    if len(positions) >= MAX_OPEN_POSITIONS:
        return
    for symbol in SYMBOLS:
        if symbol in positions or in_cooldown(symbol) or len(positions)>=MAX_OPEN_POSITIONS:
            continue
        try:
            a=await analyze_symbol(symbol)
            if a["signal"] not in ("LONG","SHORT") or not a.get("atr"):
                continue
            if last_entry_candle.get(symbol)==a["candle_time"]:
                continue
            open_position(symbol,a,a["market_price"],a["atr"])
        except Exception as e:
            print("SCAN",symbol,e)


async def bot_loop():
    global last_cycle_at,last_error
    next_scan = utcnow()
    while True:
        try:
            await manage_positions()
            if utcnow() >= next_scan:
                await scan_entries()
                next_scan = utcnow()+timedelta(seconds=SIGNAL_SCAN_SECONDS)
            last_cycle_at=utcnow().isoformat(); last_error=None
        except asyncio.CancelledError:
            break
        except Exception as e:
            last_error=str(e)
        await asyncio.sleep(POSITION_LOOP_SECONDS)


@app.on_event("startup")
async def startup():
    global http_client,bot_task
    init_db()
    try:
        load_state()
    except Exception as e:
        print("DB START",e)
    http_client=httpx.AsyncClient(timeout=15)
    bot_task=asyncio.create_task(bot_loop())


@app.on_event("shutdown")
async def shutdown():
    global http_client
    if bot_task:
        bot_task.cancel()
    if http_client:
        await http_client.aclose()


def stats():
    n=len(trade_history); wins=sum(1 for t in trade_history if float(t.get("pnl",0))>0)
    pnl=sum(float(t.get("pnl",0)) for t in trade_history)
    return {"count":n,"wins":wins,"win_rate":(100*wins/n if n else 0.0),"pnl":pnl}


@app.get("/health")
async def health():
    return {"ok":True,"ui_version":"open-positions-v1","bot":"V9 BEST-OF","mode":TRADING_MODE,"running":bot_task is not None and not bot_task.done(),"last_cycle_at":last_cycle_at,"last_error":last_error}


@app.get("/analyze")
async def analyze():
    data={}
    for s in SYMBOLS:
        try:data[s]=await analyze_symbol(s)
        except Exception as e:data[s]={"symbol":s,"signal":"ERROR","reason":str(e)}
    unrealized=0.0
    for s,p in positions.items():
        try:
            m=float(data.get(s,{}).get("market_price") or await live_price(s)); e=float(p["entry_price"]); q=float(p["qty"])
            unrealized += (m-e)*q if p["side"]=="LONG" else (e-m)*q
        except Exception: pass
    st=stats()
    return {"bot":"V9 BEST-OF","paper_balance":paper_balance,"equity":paper_balance+unrealized,"open_positions":positions,"symbols":data,"stats":st,"trade_history":trade_history[:50],"risk_per_trade_pct":RISK_PER_TRADE*100,"net_rr":NET_RISK_REWARD}


@app.get("/",response_class=HTMLResponse)
async def dashboard():
    return HTMLResponse("""<!doctype html><html lang='cs'><head><meta name='viewport' content='width=device-width,initial-scale=1'><style>
body{margin:0;background:#0b1220;color:#eef3fb;font-family:Arial,sans-serif}.wrap{max-width:980px;margin:auto;padding:18px}.card{background:#111c2f;border:1px solid #24344e;border-radius:18px;padding:18px;margin-bottom:14px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}.big{font-size:32px;font-weight:800}.muted{color:#9baac0}.green{color:#38d996}.red{color:#ff6b6b}.yellow{color:#ffc857}.row{display:flex;justify-content:space-between;gap:12px;padding:6px 0}table{width:100%;border-collapse:collapse;font-size:13px}td,th{padding:8px;border-bottom:1px solid #24344e;text-align:left}.scroll{overflow:auto}

.position-head{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;align-items:center}.position-pair{font-size:23px;font-weight:800}.badge{font-size:13px;padding:6px 10px;border-radius:8px;background:#1c3048;display:inline-block;margin-left:8px}.position-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:18px 0}.position-value{font-size:19px;font-weight:700;overflow-wrap:anywhere}.position-label{display:block;font-size:12px;color:#9baac0;margin-bottom:5px}.position-note{font-size:13px;color:#9baac0;line-height:1.5}.position-result{font-size:25px;font-weight:800}.section-title{font-size:22px;margin:4px 0 14px}.position-meta{border-top:1px solid #24344e;padding-top:12px;line-height:1.7;font-size:13px}.position-status{font-size:13px;color:#9baac0;margin-top:8px}
</style></head><body><div class='wrap'><div class='card'><div class='big'>V9 BEST-OF</div><div class='muted'>PAPER · 1h + 15m trend · 5m breakout/pullback · volume · NET costs</div></div><div id='root'>Načítám…</div></div><script>
const f=(x,n=2)=>Number(x||0).toFixed(n);const cls=x=>Number(x)>=0?'green':'red';

const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const priceText=x=>x!==null&&x!==undefined&&Number.isFinite(Number(x))?Number(x).toLocaleString('cs-CZ',{minimumFractionDigits:2,maximumFractionDigits:5}):'—';
const timeText=x=>x&&!isNaN(new Date(x))?new Date(x).toLocaleString('cs-CZ'):'—';
function positionsHtml(d){
 const ps=Object.values(d.open_positions||{});
 if(!ps.length)return "<div class='card'><h2 class='section-title'>Otevřené pozice · 0</h2><div class='muted'>Bot nyní nemá otevřený obchod. Čeká na splnění vstupních podmínek.</div></div>";
 return "<h2 class='section-title'>Otevřené pozice · "+ps.length+"</h2>"+ps.map(p=>{
  const raw=d.symbols?.[p.symbol]?.market_price;
  const current=raw!==null&&raw!==undefined&&Number.isFinite(Number(raw))?Number(raw):null;
  const gross=current===null?null:(p.side==='LONG'?current-Number(p.entry_price):Number(p.entry_price)-current)*Number(p.qty);
  const fields=[['Vstupní cena',priceText(p.entry_price)+' USDT'],['Aktuální cena',current===null?'Nedostupná':priceText(current)+' USDT'],['Stop-loss',priceText(p.stop_loss)+' USDT'],['Cílová cena',priceText(p.take_profit)+' USDT'],['Množství',priceText(p.qty)],['Strategie',p.setup==='TREND_PULLBACK'?'Návrat ceny v trendu':p.setup==='BREAKOUT'?'Průraz':p.setup]];
  return `<article class='card'><div class='position-head'><div><span class='position-pair'>${esc(p.symbol.replace(/USDT$/,' / USDT'))}</span><span class='badge ${p.side==='LONG'?'green':'red'}'>${esc(p.side)}</span></div><span class='muted'>OTEVŘENO</span></div><div class='position-grid'>${fields.map(([k,v])=>`<div><span class='position-label'>${esc(k)}</span><span class='position-value'>${esc(v)}</span></div>`).join('')}</div><span class='position-label'>Průběžný výsledek před poplatky</span><div class='position-result ${gross===null?'muted':cls(gross)}'>${gross===null?'Nedostupný':(gross>0?'+':'')+f(gross)+' USDT'}</div><p class='position-note'>Výsledek se mění s cenou. Do historie se obchod zapíše až při uzavření.</p><div class='position-meta'><div>Otevřeno: ${esc(timeText(p.opened_at))}</div>${p.breakeven?"<div class='yellow'>Stop-loss posunutý na vstupní cenu; poplatky mohou znamenat ztrátu.</div>":''}</div></article>`;
 }).join('');
}

async function go(){try{const d=await (await fetch('/analyze',{cache:'no-store'})).json();let h=positionsHtml(d)+`<div class='grid'><div class='card'><div class='muted'>Balance</div><div class='big'>${f(d.paper_balance)} USDT</div></div><div class='card'><div class='muted'>Equity</div><div class='big ${cls(d.equity-d.paper_balance)}'>${f(d.equity)} USDT</div></div><div class='card'><div class='muted'>Uzavřené obchody</div><div class='big'>${d.stats.count}</div></div><div class='card'><div class='muted'>Win rate</div><div class='big'>${f(d.stats.win_rate,1)} %</div></div><div class='card'><div class='muted'>P/L</div><div class='big ${cls(d.stats.pnl)}'>${f(d.stats.pnl)} USDT</div></div><div class='card'><div class='muted'>Risk / NET R:R</div><div class='big'>${f(d.risk_per_trade_pct,2)}% · 1:${f(d.net_rr,2)}</div></div></div>`;
h+=`<div class='grid'>`+Object.values(d.symbols||{}).map(x=>{const s=x.signal||'WAIT';return `<div class='card'><b>${x.symbol}</b><div class='position-status'>Signál pro nový vstup</div><div class='big ${s==='LONG'?'green':s==='SHORT'?'red':'yellow'}'>${s}</div><div class='row'><span>Setup</span><b>${x.setup||'—'}</b></div><div class='row'><span>1h trend</span><b>${x.trend_1h||'—'}</b></div><div class='row'><span>15m trend</span><b>${x.trend_15m||'—'}</b></div><div class='row'><span>Volume</span><b>${f(x.volume_ratio,2)}×</b></div><small class='muted'>${x.reason||''}</small></div>`}).join('')+`</div>`;
h+=`<div class='card'><h3>Uzavřené obchody</h3>${(d.trade_history||[]).length?'':`<p class='muted'>${Object.keys(d.open_positions||{}).length?'Obchod stále probíhá. Zde se objeví až po uzavření.':'Zatím žádný uzavřený obchod.'}</p>`}<div class='scroll'><table><tr><th>Pár</th><th>Směr</th><th>Setup</th><th>P/L</th><th>Důvod</th></tr>`+(d.trade_history||[]).map(t=>`<tr><td>${t.symbol}</td><td class='${t.side==='LONG'?'green':'red'}'>${t.side}</td><td>${t.setup}</td><td class='${cls(t.pnl)}'>${f(t.pnl)}</td><td>${t.reason}</td></tr>`).join('')+`</table></div></div>`;root.innerHTML=h}catch(e){root.innerHTML='<div class=card>Chyba načtení</div>'}}go();setInterval(go,15000);
</script></body></html>""")
