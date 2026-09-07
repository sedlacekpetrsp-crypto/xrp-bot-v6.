import os
import json
import asyncio
from datetime import datetime, timezone, timedelta

import httpx
import psycopg
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, Response

# ============================================================
# XRP BOT V8.1 CANDLE — MULTI-COIN — PAPER ONLY
# Price Action ONLY | R:R 1:1 | risk/trade 0.5 %
# ============================================================

app = FastAPI(title="XRP Bot V8.1 Candle")

SYMBOLS = ["XRPUSDT", "BTCUSDT", "ETHUSDT", "SOLUSDT"]
BINANCE_API = "https://data-api.binance.vision"
TRADING_MODE = "PAPER"

DATABASE_URL = os.getenv("DATABASE_URL")
STARTING_BALANCE = 10000.0

RISK_PER_TRADE = 0.005       # 0.5 % účtu
RISK_REWARD = 1.0            # TP = 1R
FEE_RATE = 0.0005            # 0.05 % za stranu
SLIPPAGE_RATE = 0.0002       # 0.02 % za stranu
STOP_BUFFER_RATE = 0.0005    # 0.05 % za high/low signální svíčky
MIN_STOP_RATE = 0.0015       # minimální SL vzdálenost 0.15 %
MAX_NOTIONAL_SHARE = 1 / len(SYMBOLS)  # 4 souběžné pozice bez celkové páky

COOLDOWN_AFTER_WIN_MIN = 1
COOLDOWN_AFTER_LOSS_MIN = 5
MAX_TRADE_MINUTES = 45
LOOP_SECONDS = 10

PAPER_BALANCE = STARTING_BALANCE
positions = {}               # symbol -> position
trade_history = []
last_entry_candle = {}       # symbol -> candle open time ms
cooldown_until = {}          # symbol -> ISO datetime
last_analysis = {}
bot_loop_started = False


# ============================================================
# DATABASE
# ============================================================

def get_db():
    if not DATABASE_URL:
        return None
    return psycopg.connect(DATABASE_URL)


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
                    INSERT INTO v81_state (id, state)
                    VALUES (1, %s::jsonb)
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
                    FROM v81_trades
                    ORDER BY id DESC
                    LIMIT 300
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
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    trade["symbol"], trade["side"], trade["setup"],
                    trade["entry_price"], trade["exit_price"], trade["qty"],
                    trade["gross_pnl"], trade["fees"], trade["pnl"],
                    trade["reason"], trade["opened_at"], trade["closed_at"],
                ))
            conn.commit()
    except Exception as e:
        print("SAVE TRADE ERROR:", e)


# ============================================================
# BINANCE DATA
# ============================================================

async def get_klines(symbol, interval="5m", limit=80):
    url = f"{BINANCE_API}/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()


async def get_live_price(symbol):
    url = f"{BINANCE_API}/api/v3/ticker/price"
    params = {"symbol": symbol}
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return float(response.json()["price"])


# ============================================================
# PRICE ACTION / CANDLE STRATEGY ONLY
# ============================================================

def candle_parts(k):
    o, h, l, c = float(k[1]), float(k[2]), float(k[3]), float(k[4])
    body = abs(c - o)
    rng = max(h - l, 1e-12)
    upper = h - max(o, c)
    lower = min(o, c) - l
    return o, h, l, c, body, rng, upper, lower


def detect_setup(closed):
    """
    Uses only completed 5m candles.
    Priority:
      1) 8-candle breakout with strong body
      2) engulfing
      3) pin bar rejection
    No EMA / RSI / MACD / ATR / volume filters.
    """
    if len(closed) < 12:
        return {"signal": "WAIT", "setup": None, "reason": "málo dat"}

    prev = closed[-2]
    cur = closed[-1]
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
    )
    bearish_engulfing = (
        p_c > p_o and c_c < c_o
        and c_o >= p_c and c_c <= p_o
        and c_body >= p_body * 1.05
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
    closed = klines[:-1]  # pouze uzavřené svíčky
    result = detect_setup(closed)
    result["symbol"] = symbol
    return result


# ============================================================
# RISK / POSITIONS
# ============================================================

def cooldown_active(symbol):
    value = cooldown_until.get(symbol)
    if not value:
        return False
    try:
        return datetime.now(timezone.utc) < datetime.fromisoformat(value)
    except Exception:
        return False


def open_trade(symbol, analysis, market_price):
    global positions, last_entry_candle

    if symbol in positions:
        return False

    side = analysis["signal"]
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

    risk_usdt = PAPER_BALANCE * RISK_PER_TRADE
    qty_by_risk = risk_usdt / stop_distance

    # Multi-coin bez souhrnné páky: každý ze 4 symbolů max 25 % účtu.
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
        "opened_at": datetime.now(timezone.utc).isoformat(),
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

    closed_at = datetime.now(timezone.utc)
    trade = {
        "symbol": symbol,
        "side": side,
        "setup": p["setup"],
        "entry_price": entry_price,
        "exit_price": exit_price,
        "qty": qty,
        "gross_pnl": gross_pnl,
        "fees": fees,
        "pnl": net_pnl,
        "reason": reason,
        "opened_at": p["opened_at"],
        "closed_at": closed_at.isoformat(),
    }

    save_trade(trade)
    trade_history.insert(0, trade)
    trade_history = trade_history[:300]

    minutes = COOLDOWN_AFTER_LOSS_MIN if net_pnl < 0 else COOLDOWN_AFTER_WIN_MIN
    cooldown_until[symbol] = (closed_at + timedelta(minutes=minutes)).isoformat()

    del positions[symbol]
    save_state()
    print("CLOSE V8.1", symbol, reason, net_pnl)


async def manage_position(symbol):
    p = positions.get(symbol)
    if not p:
        return

    price = await get_live_price(symbol)
    side = p["side"]
    stop_loss = float(p["stop_loss"])
    take_profit = float(p["take_profit"])

    opened_at = datetime.fromisoformat(p["opened_at"])
    age_minutes = (datetime.now(timezone.utc) - opened_at).total_seconds() / 60

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


# ============================================================
# BOT CYCLE — ALL SYMBOLS IN PARALLEL
# ============================================================

async def process_symbol(symbol):
    try:
        await manage_position(symbol)
        analysis = await strategy_analysis(symbol)
        last_analysis[symbol] = analysis

        if symbol in positions:
            return
        if cooldown_active(symbol):
            return
        if last_entry_candle.get(symbol) == analysis["candle_time"]:
            return
        if analysis["signal"] not in ("LONG", "SHORT"):
            return

        live_price = await get_live_price(symbol)
        open_trade(symbol, analysis, live_price)
    except Exception as e:
        print("SYMBOL CYCLE ERROR", symbol, e)


async def trading_cycle():
    await asyncio.gather(*(process_symbol(s) for s in SYMBOLS))


async def bot_loop():
    while True:
        await trading_cycle()
        await asyncio.sleep(LOOP_SECONDS)


@app.on_event("startup")
async def startup_event():
    global bot_loop_started
    init_db()
    load_state()
    if not bot_loop_started:
        bot_loop_started = True
        asyncio.create_task(bot_loop())
        print("XRP BOT V8.1 CANDLE STARTED")


# ============================================================
# STATISTICS / API
# ============================================================

def calculate_stats():
    trades = trade_history
    count = len(trades)
    wins = sum(1 for t in trades if float(t["pnl"]) > 0)
    losses = count - wins
    total_pnl = sum(float(t["pnl"]) for t in trades)
    total_fees = sum(float(t["fees"]) for t in trades)
    return {
        "count": count,
        "wins": wins,
        "losses": losses,
        "win_rate": (wins / count * 100) if count else 0,
        "total_pnl": total_pnl,
        "total_fees": total_fees,
        "average_pnl": (total_pnl / count) if count else 0,
    }


@app.get("/analyze")
async def analyze():
    analyses = await asyncio.gather(*(strategy_analysis(s) for s in SYMBOLS), return_exceptions=True)
    market = {}
    unrealized_total = 0.0

    for symbol, a in zip(SYMBOLS, analyses):
        if isinstance(a, Exception):
            market[symbol] = {"symbol": symbol, "signal": "ERROR", "reason": str(a)}
            continue

        last_analysis[symbol] = a
        price = await get_live_price(symbol)
        row = dict(a)
        row["price"] = price
        row["cooldown"] = cooldown_active(symbol)
        row["position"] = positions.get(symbol)

        p = positions.get(symbol)
        if p:
            entry = float(p["entry_price"])
            qty = float(p["qty"])
            upnl = (price - entry) * qty if p["side"] == "LONG" else (entry - price) * qty
            row["unrealized_pnl"] = upnl
            unrealized_total += upnl
        else:
            row["unrealized_pnl"] = 0.0

        market[symbol] = row

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
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "bot": "XRP BOT V8.1 CANDLE",
        "mode": TRADING_MODE,
        "strategy": "PRICE ACTION ONLY",
        "risk_reward": RISK_REWARD,
        "risk_per_trade": RISK_PER_TRADE,
        "symbols": SYMBOLS,
        "open_positions": len(positions),
    }


# UptimeRobot uses HEAD requests. Explicit routes prevent false 405 DOWN alerts.
@app.head("/")
@app.head("/analyze")
@app.head("/health")
async def uptime_head():
    return Response(status_code=200)


# ============================================================
# DASHBOARD
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
<!DOCTYPE html>
<html lang="cs">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Bot V8.1 Candle</title>
<style>
body{background:#0b1118;color:#fff;font-family:Arial,sans-serif;margin:0;padding:14px}
.wrap{max-width:980px;margin:auto}
.card{background:#151c24;border:1px solid #26313d;border-radius:18px;padding:18px;margin-bottom:14px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
.coin{background:#10171f;border-radius:14px;padding:14px}
.row{display:flex;justify-content:space-between;gap:12px;margin:7px 0}
.green{color:#58df86}.red{color:#ff6868}.yellow{color:#ffd166}.muted{opacity:.7}
.trade{padding:10px 0;border-bottom:1px solid #2a3440}
h1{margin:2px 0 12px;font-size:25px}h2{font-size:19px}
</style>
</head>
<body><div class="wrap">
<div class="card">
<h1>🕯️ BOT V8.1 CANDLE</h1>
<div class="row"><span>Strategie</span><b>PRICE ACTION ONLY</b></div>
<div class="row"><span>Risk : Reward</span><b>1 : 1</b></div>
<div class="row"><span>Risk / obchod</span><b>0.5 %</b></div>
<div class="row"><span>Režim</span><b>PAPER</b></div>
</div>
<div class="card"><h2>📡 Trhy a otevřené pozice</h2><div id="coins" class="grid"></div></div>
<div class="card">
<h2>💰 Účet</h2>
<div class="row"><span>Balance</span><b id="balance">---</b></div>
<div class="row"><span>Equity</span><b id="equity">---</b></div>
<div class="row"><span>Otevřený P&L</span><b id="upnl">---</b></div>
</div>
<div class="card">
<h2>📊 Statistiky</h2>
<div class="row"><span>Obchody</span><b id="count">---</b></div>
<div class="row"><span>WIN / LOSS</span><b id="wl">---</b></div>
<div class="row"><span>Win rate</span><b id="wr">---</b></div>
<div class="row"><span>Čistý P&L</span><b id="pnl">---</b></div>
<div class="row"><span>Poplatky</span><b id="fees">---</b></div>
</div>
<div class="card"><h2>📜 Posledních 50 obchodů</h2><div id="history">---</div></div>
</div>
<script>
const fmt=(v,d=4)=>Number.isFinite(Number(v))?Number(v).toFixed(d):"---";
const cls=v=>Number(v)>0?"green":Number(v)<0?"red":"yellow";
async function refresh(){
  try{
    const r=await fetch("/analyze",{cache:"no-store"}); const d=await r.json();
    document.getElementById("balance").innerText=fmt(d.paper_balance,2)+" USDT";
    document.getElementById("equity").innerText=fmt(d.equity,2)+" USDT";
    const u=document.getElementById("upnl");u.innerText=fmt(d.unrealized_pnl,2)+" USDT";u.className=cls(d.unrealized_pnl);
    const s=d.stats||{};
    document.getElementById("count").innerText=s.count||0;
    document.getElementById("wl").innerText=(s.wins||0)+" / "+(s.losses||0);
    document.getElementById("wr").innerText=fmt(s.win_rate,1)+" %";
    const p=document.getElementById("pnl");p.innerText=fmt(s.total_pnl,2)+" USDT";p.className=cls(s.total_pnl);
    document.getElementById("fees").innerText=fmt(s.total_fees,2)+" USDT";

    document.getElementById("coins").innerHTML=(d.symbols||[]).map(sym=>{
      const m=d.market[sym]||{}; const pos=m.position;
      const sigClass=m.signal==="LONG"?"green":m.signal==="SHORT"?"red":"yellow";
      return `<div class="coin">
        <div class="row"><b>${sym.replace("USDT","")}</b><b>${fmt(m.price,5)}</b></div>
        <div class="row"><span>Signál</span><b class="${sigClass}">${m.signal||"---"}</b></div>
        <div class="row"><span>Setup</span><span>${m.setup||"---"}</span></div>
        <div class="muted">${m.reason||""}</div>
        ${pos?`<hr><div class="row"><span>Pozice</span><b>${pos.side}</b></div>
        <div class="row"><span>Entry</span><span>${fmt(pos.entry_price,5)}</span></div>
        <div class="row"><span>SL</span><span>${fmt(pos.stop_loss,5)}</span></div>
        <div class="row"><span>TP</span><span>${fmt(pos.take_profit,5)}</span></div>
        <div class="row"><span>P&L</span><b class="${cls(m.unrealized_pnl)}">${fmt(m.unrealized_pnl,2)} USDT</b></div>`:""}
      </div>`;
    }).join("");

    const h=(d.trade_history||[]).slice(0,50);
    document.getElementById("history").innerHTML=h.length?h.map(t=>`<div class="trade">
      <div class="row"><span><b>${t.symbol}</b> · ${t.side} · ${t.setup||"---"}</span>
      <b class="${cls(t.pnl)}">${fmt(t.pnl,2)} USDT</b></div>
      <div class="muted">${t.reason} · ${fmt(t.entry_price,5)} → ${fmt(t.exit_price,5)}</div>
    </div>`).join(""):"Zatím žádné uzavřené obchody";
  }catch(e){console.error(e)}
}
refresh(); setInterval(refresh,5000);
</script></body></html>
"""