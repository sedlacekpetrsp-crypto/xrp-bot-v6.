import os
import json
import asyncio
import time
from datetime import datetime, timezone, timedelta

import httpx
import psycopg
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, Response

# ============================================================
# XRP BOT V8.1 CANDLE — MULTI-COIN — PAPER ONLY
# Stable build: shared HTTP client, cached dashboard data,
# retry/backoff for Binance 429, low request volume.
# ============================================================

app = FastAPI(title="XRP Bot V8.1 Candle")

SYMBOLS = ["XRPUSDT", "BTCUSDT", "ETHUSDT", "SOLUSDT"]
BINANCE_API = "https://data-api.binance.vision"
TRADING_MODE = "PAPER"
DATABASE_URL = os.getenv("DATABASE_URL")
STARTING_BALANCE = 10000.0

RISK_PER_TRADE = 0.005
RISK_REWARD = 1.0
FEE_RATE = 0.0005
SLIPPAGE_RATE = 0.0002
ROUND_TRIP_COST_RATE = 2 * (FEE_RATE + SLIPPAGE_RATE)
MIN_EDGE_COST_MULTIPLE = 1.50
STOP_BUFFER_RATE = 0.0005
MIN_STOP_RATE = 0.0015
MAX_NOTIONAL_SHARE = 1 / len(SYMBOLS)

COOLDOWN_AFTER_WIN_MIN = 1
COOLDOWN_AFTER_LOSS_MIN = 5
MAX_TRADE_MINUTES = 45
POSITION_LOOP_SECONDS = 5
SIGNAL_SCAN_SECONDS = 30

PAPER_BALANCE = STARTING_BALANCE
positions = {}
trade_history = []
last_entry_candle = {}
cooldown_until = {}
last_analysis = {}
price_cache = {}
bot_loop_started = False
bot_task = None
http_client = None
last_cycle_at = None
last_signal_scan_at = None
last_error = None
http_429_count = 0
started_at = datetime.now(timezone.utc)


def utcnow():
    return datetime.now(timezone.utc)


def get_db():
    return psycopg.connect(DATABASE_URL) if DATABASE_URL else None


def init_db():
    if not DATABASE_URL:
        print("DATABASE_URL není nastaveno - data nebudou trvale ukládána.")
        return
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS v81_trades (
                    id SERIAL PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    setup TEXT,
                    entry_price DOUBLE PRECISION NOT NULL,
                    exit_price DOUBLE PRECISION NOT NULL,
                    qty DOUBLE PRECISION NOT NULL,
                    gross_pnl DOUBLE PRECISION NOT NULL,
                    fees DOUBLE PRECISION NOT NULL,
                    pnl DOUBLE PRECISION NOT NULL,
                    reason TEXT,
                    opened_at TIMESTAMPTZ,
                    closed_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS v81_state (
                    id INTEGER PRIMARY KEY,
                    state JSONB NOT NULL
                )
            """)
        conn.commit()


def save_state():
    if not DATABASE_URL:
        return
    state = {
        "paper_balance": PAPER_BALANCE,
        "positions": positions,
        "last_entry_candle": last_entry_candle,
        "cooldown_until": cooldown_until,
    }
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO v81_state (id, state) VALUES (1, %s::jsonb)
                    ON CONFLICT (id) DO UPDATE SET state = EXCLUDED.state
                """, (json.dumps(state),))
            conn.commit()
    except Exception as e:
        print("SAVE STATE ERROR:", e)


def load_state():
    global PAPER_BALANCE, positions, last_entry_candle, cooldown_until, trade_history
    if not DATABASE_URL:
        return
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT state FROM v81_state WHERE id = 1")
                row = cur.fetchone()
                if row:
                    state = row[0] or {}
                    PAPER_BALANCE = float(state.get("paper_balance", STARTING_BALANCE))
                    positions = state.get("positions", {}) or {}
                    last_entry_candle = state.get("last_entry_candle", {}) or {}
                    cooldown_until = state.get("cooldown_until", {}) or {}
                cur.execute("""
                    SELECT symbol, side, setup, entry_price, exit_price, qty,
                           gross_pnl, fees, pnl, reason, opened_at, closed_at
                    FROM v81_trades ORDER BY id DESC LIMIT 300
                """)
                rows = cur.fetchall()
                trade_history = [{
                    "symbol": r[0], "side": r[1], "setup": r[2],
                    "entry_price": r[3], "exit_price": r[4], "qty": r[5],
                    "gross_pnl": r[6], "fees": r[7], "pnl": r[8],
                    "reason": r[9],
                    "opened_at": r[10].isoformat() if r[10] else None,
                    "closed_at": r[11].isoformat() if r[11] else None,
                } for r in rows]
    except Exception as e:
        print("LOAD STATE ERROR:", e)


def save_trade(trade):
    if not DATABASE_URL:
        return
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO v81_trades (
                        symbol, side, setup, entry_price, exit_price, qty,
                        gross_pnl, fees, pnl, reason, opened_at, closed_at
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    trade["symbol"], trade["side"], trade["setup"],
                    trade["entry_price"], trade["exit_price"], trade["qty"],
                    trade["gross_pnl"], trade["fees"], trade["pnl"],
                    trade["reason"], trade["opened_at"], trade["closed_at"],
                ))
            conn.commit()
    except Exception as e:
        print("SAVE TRADE ERROR:", e)


async def binance_get(path, params=None):
    global http_429_count, last_error
    if http_client is None:
        raise RuntimeError("HTTP client not initialized")
    url = f"{BINANCE_API}{path}"
    delay = 1.0
    for attempt in range(4):
        try:
            r = await http_client.get(url, params=params)
            if r.status_code == 429:
                http_429_count += 1
                retry_after = r.headers.get("Retry-After")
                try:
                    wait = float(retry_after) if retry_after else delay
                except ValueError:
                    wait = delay
                await asyncio.sleep(min(max(wait, 0.5), 10.0))
                delay *= 2
                continue
            r.raise_for_status()
            return r.json()
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            last_error = f"BINANCE {type(e).__name__}: {e}"
            if attempt == 3:
                raise
            await asyncio.sleep(delay)
            delay *= 2
    raise RuntimeError("Binance rate limit: retries exhausted")


async def get_klines(symbol, interval="5m", limit=80):
    return await binance_get("/api/v3/klines", {
        "symbol": symbol, "interval": interval, "limit": limit
    })


async def get_live_price(symbol, max_age=2.0):
    cached = price_cache.get(symbol)
    now = time.monotonic()
    if cached and now - cached["ts"] <= max_age:
        return cached["price"]
    data = await binance_get("/api/v3/ticker/price", {"symbol": symbol})
    price = float(data["price"])
    price_cache[symbol] = {"price": price, "ts": now, "updated_at": utcnow().isoformat()}
    return price


def candle_parts(k):
    o, h, l, c = float(k[1]), float(k[2]), float(k[3]), float(k[4])
    body = abs(c - o)
    rng = max(h - l, 1e-12)
    upper = h - max(o, c)
    lower = min(o, c) - l
    return o, h, l, c, body, rng, upper, lower


def detect_setup(closed):
    if len(closed) < 12:
        return {"signal": "WAIT", "setup": None, "reason": "málo dat"}

    prev, cur = closed[-2], closed[-1]
    p_o, p_h, p_l, p_c, p_body, p_rng, p_up, p_low = candle_parts(prev)
    c_o, c_h, c_l, c_c, c_body, c_rng, c_up, c_low = candle_parts(cur)
    candle_time = int(cur[0])
    body_ratio = c_body / c_rng

    recent = closed[-10:-2]
    prior_high = max(float(x[2]) for x in recent)
    prior_low = min(float(x[3]) for x in recent)

    bullish_breakout = c_c > prior_high and c_c > c_o and body_ratio >= 0.55
    bearish_breakout = c_c < prior_low and c_c < c_o and body_ratio >= 0.55

    bullish_engulfing = (
        p_c < p_o and c_c > c_o
        and c_o <= p_c and c_c >= p_o
        and c_body >= p_body * 1.05
        and body_ratio >= 0.45
    )
    bearish_engulfing = (
        p_c > p_o and c_c < c_o
        and c_o >= p_c and c_c <= p_o
        and c_body >= p_body * 1.05
        and body_ratio >= 0.45
    )

    bullish_pin = (
        c_c > c_o
        and c_low >= max(c_body * 2.0, c_rng * 0.45)
        and c_up <= c_rng * 0.20
        and c_c >= c_l + c_rng * 0.65
    )
    bearish_pin = (
        c_c < c_o
        and c_up >= max(c_body * 2.0, c_rng * 0.45)
        and c_low <= c_rng * 0.20
        and c_c <= c_l + c_rng * 0.35
    )

    if bullish_breakout:
        signal, setup = "LONG", "BREAKOUT"
    elif bearish_breakout:
        signal, setup = "SHORT", "BREAKOUT"
    elif bullish_engulfing:
        signal, setup = "LONG", "BULL ENGULFING"
    elif bearish_engulfing:
        signal, setup = "SHORT", "BEAR ENGULFING"
    elif bullish_pin:
        signal, setup = "LONG", "BULL PIN BAR"
    elif bearish_pin:
        signal, setup = "SHORT", "BEAR PIN BAR"
    else:
        signal, setup = "WAIT", None

    return {
        "signal": signal,
        "setup": setup,
        "reason": "price-action setup potvrzen" if signal != "WAIT" else "bez potvrzené svíčkové formace",
        "candle_time": candle_time,
        "price_closed": c_c,
        "signal_high": c_h,
        "signal_low": c_l,
        "body_ratio": body_ratio,
    }


async def strategy_analysis(symbol):
    klines = await get_klines(symbol, "5m", 80)
    closed = klines[:-1]
    result = detect_setup(closed)
    result["symbol"] = symbol
    return result


def cooldown_active(symbol):
    value = cooldown_until.get(symbol)
    if not value:
        return False
    try:
        return utcnow() < datetime.fromisoformat(value)
    except Exception:
        return False


def open_trade(symbol, analysis, market_price):
    global positions, last_entry_candle
    if symbol in positions:
        return False
    side = analysis.get("signal")
    if side not in ("LONG", "SHORT"):
        return False

    signal_low = float(analysis["signal_low"])
    signal_high = float(analysis["signal_high"])
    min_stop = market_price * MIN_STOP_RATE

    if side == "LONG":
        entry_price = market_price * (1 + SLIPPAGE_RATE)
        structural_stop = signal_low * (1 - STOP_BUFFER_RATE)
        stop_distance = max(entry_price - structural_stop, min_stop)
        stop_loss = entry_price - stop_distance
        take_profit = entry_price + stop_distance * RISK_REWARD
    else:
        entry_price = market_price * (1 - SLIPPAGE_RATE)
        structural_stop = signal_high * (1 + STOP_BUFFER_RATE)
        stop_distance = max(structural_stop - entry_price, min_stop)
        stop_loss = entry_price + stop_distance
        take_profit = entry_price - stop_distance * RISK_REWARD

    if stop_distance <= 0:
        return False

    expected_move_rate = (stop_distance * RISK_REWARD) / max(entry_price, 1e-12)
    if expected_move_rate < ROUND_TRIP_COST_RATE * MIN_EDGE_COST_MULTIPLE:
        print("SKIP V8.1", symbol, "EDGE_TOO_SMALL", expected_move_rate)
        return False

    risk_usdt = PAPER_BALANCE * RISK_PER_TRADE
    qty_by_risk = risk_usdt / stop_distance
    max_notional = PAPER_BALANCE * MAX_NOTIONAL_SHARE
    qty_by_notional = max_notional / entry_price
    qty = min(qty_by_risk, qty_by_notional)
    if qty <= 0:
        return False

    positions[symbol] = {
        "symbol": symbol,
        "side": side,
        "setup": analysis["setup"],
        "entry_price": entry_price,
        "qty": qty,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "risk_usdt": risk_usdt,
        "opened_at": utcnow().isoformat(),
        "signal_candle": analysis["candle_time"],
    }
    last_entry_candle[symbol] = analysis["candle_time"]
    save_state()
    print("OPEN V8.1", symbol, side, analysis["setup"], entry_price)
    return True


def close_trade(symbol, market_price, reason):
    global PAPER_BALANCE, trade_history, positions, cooldown_until
    p = positions.get(symbol)
    if not p:
        return
    side = p["side"]
    entry_price = float(p["entry_price"])
    qty = float(p["qty"])

    if side == "LONG":
        exit_price = market_price * (1 - SLIPPAGE_RATE)
        gross_pnl = (exit_price - entry_price) * qty
    else:
        exit_price = market_price * (1 + SLIPPAGE_RATE)
        gross_pnl = (entry_price - exit_price) * qty

    fees = (entry_price * qty + exit_price * qty) * FEE_RATE
    net_pnl = gross_pnl - fees
    PAPER_BALANCE += net_pnl
    closed_at = utcnow()
    trade = {
        "symbol": symbol, "side": side, "setup": p["setup"],
        "entry_price": entry_price, "exit_price": exit_price, "qty": qty,
        "gross_pnl": gross_pnl, "fees": fees, "pnl": net_pnl,
        "reason": reason, "opened_at": p["opened_at"],
        "closed_at": closed_at.isoformat(),
    }
    save_trade(trade)
    trade_history.insert(0, trade)
    trade_history = trade_history[:300]
    minutes = COOLDOWN_AFTER_LOSS_MIN if net_pnl < 0 else COOLDOWN_AFTER_WIN_MIN
    cooldown_until[symbol] = (closed_at + timedelta(minutes=minutes)).isoformat()
    positions.pop(symbol, None)
    save_state()
    print("CLOSE V8.1", symbol, reason, net_pnl)


async def manage_position(symbol):
    p = positions.get(symbol)
    if not p:
        return
    price = await get_live_price(symbol, max_age=1.0)
    side = p["side"]
    stop_loss = float(p["stop_loss"])
    take_profit = float(p["take_profit"])
    opened_at = datetime.fromisoformat(p["opened_at"])
    age_minutes = (utcnow() - opened_at).total_seconds() / 60

    if side == "LONG":
        if price <= stop_loss:
            close_trade(symbol, price, "STOP LOSS")
            return
        if price >= take_profit:
            close_trade(symbol, price, "TAKE PROFIT")
            return
    else:
        if price >= stop_loss:
            close_trade(symbol, price, "STOP LOSS")
            return
        if price <= take_profit:
            close_trade(symbol, price, "TAKE PROFIT")
            return

    if age_minutes >= MAX_TRADE_MINUTES:
        close_trade(symbol, price, "TIME EXIT")


async def scan_symbol(symbol):
    global last_error
    try:
        analysis = await strategy_analysis(symbol)
        last_analysis[symbol] = analysis
        if symbol in positions or cooldown_active(symbol):
            return
        if last_entry_candle.get(symbol) == analysis.get("candle_time"):
            return
        if analysis.get("signal") not in ("LONG", "SHORT"):
            return
        price = await get_live_price(symbol, max_age=2.0)
        open_trade(symbol, analysis, price)
    except Exception as e:
        last_error = f"{symbol}: {type(e).__name__}: {e}"
        last_analysis[symbol] = {
            "symbol": symbol, "signal": "ERROR", "setup": None,
            "reason": str(e)
        }
        print("SYMBOL SCAN ERROR", symbol, e)


async def trading_loop():
    global last_cycle_at, last_signal_scan_at, last_error
    next_scan = 0.0
    while True:
        try:
            if positions:
                await asyncio.gather(*(manage_position(s) for s in list(positions.keys())), return_exceptions=True)
            now = time.monotonic()
            if now >= next_scan:
                await asyncio.gather(*(scan_symbol(s) for s in SYMBOLS))
                last_signal_scan_at = utcnow().isoformat()
                next_scan = now + SIGNAL_SCAN_SECONDS
            last_cycle_at = utcnow().isoformat()
        except Exception as e:
            last_error = f"LOOP: {type(e).__name__}: {e}"
            print("V8.1 LOOP ERROR", e)
        await asyncio.sleep(POSITION_LOOP_SECONDS)


def calculate_stats():
    count = len(trade_history)
    wins = sum(1 for t in trade_history if float(t["pnl"]) > 0)
    losses = count - wins
    total_pnl = sum(float(t["pnl"]) for t in trade_history)
    total_fees = sum(float(t["fees"]) for t in trade_history)
    gp = sum(float(t["pnl"]) for t in trade_history if float(t["pnl"]) > 0)
    gl = abs(sum(float(t["pnl"]) for t in trade_history if float(t["pnl"]) < 0))
    return {
        "count": count,
        "wins": wins,
        "losses": losses,
        "win_rate": (wins / count * 100) if count else 0,
        "total_pnl": total_pnl,
        "total_fees": total_fees,
        "average_pnl": (total_pnl / count) if count else 0,
        "profit_factor": (gp / gl) if gl else (999 if gp else 0),
    }


@app.on_event("startup")
async def startup_event():
    global bot_loop_started, bot_task, http_client, started_at
    started_at = utcnow()
    limits = httpx.Limits(max_connections=8, max_keepalive_connections=4, keepalive_expiry=30.0)
    http_client = httpx.AsyncClient(timeout=httpx.Timeout(10.0), limits=limits, headers={"User-Agent": "xrp-bot-v8.1/1.1"})
    init_db()
    load_state()
    if not bot_loop_started:
        bot_loop_started = True
        bot_task = asyncio.create_task(trading_loop())
        print("XRP BOT V8.1 CANDLE STABLE STARTED")


@app.on_event("shutdown")
async def shutdown_event():
    global bot_task, http_client
    if bot_task:
        bot_task.cancel()
    if http_client:
        await http_client.aclose()
        http_client = None


@app.get("/analyze")
async def analyze():
    market = {}
    unrealized_total = 0.0
    for symbol in SYMBOLS:
        a = dict(last_analysis.get(symbol) or {
            "symbol": symbol, "signal": "WAIT", "setup": None, "reason": "čekám na první scan"
        })
        p = positions.get(symbol)
        cached = price_cache.get(symbol)
        price = cached["price"] if cached else a.get("price_closed")
        a["price"] = price
        a["cooldown"] = cooldown_active(symbol)
        a["position"] = p
        upnl = 0.0
        if p and price is not None:
            entry = float(p["entry_price"])
            qty = float(p["qty"])
            upnl = (price - entry) * qty if p["side"] == "LONG" else (entry - price) * qty
            unrealized_total += upnl
        a["unrealized_pnl"] = upnl
        market[symbol] = a
    return {
        "bot": "XRP BOT V8.1 CANDLE",
        "mode": TRADING_MODE,
        "strategy": "PRICE ACTION ONLY",
        "risk_reward": "1:1",
        "risk_per_trade_pct": RISK_PER_TRADE * 100,
        "symbols": SYMBOLS,
        "paper_balance": PAPER_BALANCE,
        "equity": PAPER_BALANCE + unrealized_total,
        "unrealized_pnl": unrealized_total,
        "open_positions": positions,
        "market": market,
        "stats": calculate_stats(),
        "trade_history": trade_history[:50],
        "last_cycle_at": last_cycle_at,
        "last_signal_scan_at": last_signal_scan_at,
        "last_error": last_error,
        "http_429_count": http_429_count,
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "bot": "XRP BOT V8.1 CANDLE",
        "mode": TRADING_MODE,
        "loop_started": bot_loop_started,
        "last_cycle_at": last_cycle_at,
        "last_signal_scan_at": last_signal_scan_at,
        "open_positions": len(positions),
        "http_429_count": http_429_count,
        "last_error": last_error,
        "uptime_seconds": int((utcnow() - started_at).total_seconds()),
    }


@app.head("/")
@app.head("/analyze")
@app.head("/health")
async def uptime_head():
    return Response(status_code=200)


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
<!doctype html>
<html lang="cs">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Bot V8.1 Candle</title>
<style>
body{margin:0;background:#0b1118;color:#edf3f8;font-family:Arial,sans-serif}
.wrap{max-width:1050px;margin:auto;padding:14px}
.card{background:#151c24;border:1px solid #26313d;border-radius:16px;padding:16px;margin-bottom:12px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px}
.coin{background:#10171f;border-radius:12px;padding:12px}
.row{display:flex;justify-content:space-between;gap:12px;margin:6px 0}
.green{color:#5ce68b}.red{color:#ff6b6b}.yellow{color:#ffd166}.muted{opacity:.65}
.trade{display:grid;grid-template-columns:1.1fr .8fr 1fr 1fr;gap:8px;padding:9px 0;border-bottom:1px solid #29343e;font-size:13px}
h1{font-size:24px;margin:0 0 8px}h2{font-size:18px}
</style></head>
<body><div class="wrap">
<div class="card"><h1>🕯️ BOT V8.1 CANDLE</h1><div class="muted">PAPER • Price Action • R:R 1:1 • risk 0.5 %</div></div>
<div class="card"><div id="stats" class="grid"></div></div>
<div class="card"><h2>📡 Trhy / pozice</h2><div id="coins" class="grid"></div></div>
<div class="card"><h2>🧾 Posledních 50 obchodů</h2><div id="trades"></div></div>
<div class="card muted" id="health">Načítám…</div>
</div>
<script>
const f=(n,d=2)=>Number(n||0).toFixed(d);
async function refresh(){
  try{
    const r=await fetch('/analyze',{cache:'no-store'}); const d=await r.json();
    const s=d.stats||{};
    document.getElementById('stats').innerHTML=[
      ['Balance',f(d.paper_balance,2)+' USDT'],
      ['Equity',f(d.equity,2)+' USDT'],
      ['Obchody',s.count||0],
      ['Win rate',f(s.win_rate,1)+' %'],
      ['PnL',f(s.total_pnl,2)+' USDT'],
      ['Fees',f(s.total_fees,2)+' USDT']
    ].map(x=>`<div class="coin"><div class="muted">${x[0]}</div><b>${x[1]}</b></div>`).join('');
    document.getElementById('coins').innerHTML=Object.values(d.market||{}).map(x=>{
      const p=x.position, sig=x.signal||'WAIT', cls=sig==='LONG'?'green':sig==='SHORT'?'red':'yellow';
      return `<div class="coin"><b>${x.symbol}</b><div class="row"><span>Signál</span><b class="${cls}">${sig}</b></div>
      <div class="row"><span>Cena</span><span>${x.price==null?'—':f(x.price,6)}</span></div>
      <div class="row"><span>Setup</span><span>${x.setup||'—'}</span></div>
      <div class="row"><span>Pozice</span><span>${p?p.side:'—'}</span></div>
      <div class="row"><span>uPnL</span><span>${f(x.unrealized_pnl,2)}</span></div></div>`;
    }).join('');
    document.getElementById('trades').innerHTML=(d.trade_history||[]).map(t=>
      `<div class="trade"><span>${t.symbol}</span><span>${t.side}</span><span>${t.reason}</span><span class="${Number(t.pnl)>=0?'green':'red'}">${f(t.pnl,2)}</span></div>`
    ).join('')||'<div class="muted">Zatím bez obchodů.</div>';
    document.getElementById('health').textContent=`Poslední cyklus: ${d.last_cycle_at||'—'} • scan: ${d.last_signal_scan_at||'—'} • 429: ${d.http_429_count||0} • chyba: ${d.last_error||'žádná'}`;
  }catch(e){document.getElementById('health').textContent='Dashboard error: '+e}
}
refresh(); setInterval(refresh,10000);
</script></body></html>
"""
