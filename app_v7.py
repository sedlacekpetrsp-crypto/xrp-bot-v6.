import os
import json
import asyncio
from datetime import datetime, timezone, timedelta

import httpx
import psycopg
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="XRP Bot V7 Scalper")

SYMBOL = "XRPUSDT"
BINANCE_API = "https://data-api.binance.vision"
TRADING_MODE = "PAPER"
DATABASE_URL = os.getenv("DATABASE_URL")
STARTING_BALANCE = 10000.0

# =========================
# V7 MONEY MANAGEMENT
# =========================
RISK_PER_TRADE = 0.0025
RISK_REWARD = 1.25
ATR_MULTIPLIER = 0.90
FEE_RATE = 0.0005
SLIPPAGE_RATE = 0.0002
MAX_TRADE_MINUTES = 6
COOLDOWN_AFTER_WIN_MIN = 0
COOLDOWN_AFTER_LOSS_MIN = 1
LOOP_SECONDS = 10

# =========================
# V7 ENTRY FILTERS
# =========================
MIN_VOLUME_RATIO = 0.85
LONG_RSI_MIN = 40
LONG_RSI_MAX = 72
SHORT_RSI_MIN = 28
SHORT_RSI_MAX = 60
MIN_ENTRY_SCORE = 4
BREAKOUT_LOOKBACK = 10

PAPER_BALANCE = STARTING_BALANCE
paper_position = None
trade_history = []
last_entry_candle = None
cooldown_until = None
bot_loop_started = False


def get_db():
    if not DATABASE_URL:
        return None
    return psycopg.connect(DATABASE_URL)


def init_db():
    if not DATABASE_URL:
        print("DATABASE_URL není nastaveno - data V7 nebudou trvale ukládána.")
        return
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS v7_trades (
                    id SERIAL PRIMARY KEY,
                    side TEXT NOT NULL,
                    setup TEXT,
                    entry_price DOUBLE PRECISION NOT NULL,
                    exit_price DOUBLE PRECISION NOT NULL,
                    qty DOUBLE PRECISION NOT NULL,
                    gross_pnl DOUBLE PRECISION NOT NULL,
                    fees DOUBLE PRECISION NOT NULL,
                    pnl DOUBLE PRECISION NOT NULL,
                    reason TEXT,
                    score INTEGER,
                    opened_at TIMESTAMPTZ,
                    closed_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS v7_state (
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
        "paper_position": paper_position,
        "last_entry_candle": last_entry_candle,
        "cooldown_until": cooldown_until.isoformat() if cooldown_until else None,
    }
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO v7_state (id, state)
                    VALUES (1, %s::jsonb)
                    ON CONFLICT (id) DO UPDATE SET state = EXCLUDED.state
                """, (json.dumps(state),))
            conn.commit()
    except Exception as e:
        print("SAVE STATE ERROR:", e)


def load_state():
    global PAPER_BALANCE, paper_position, last_entry_candle, cooldown_until, trade_history
    if not DATABASE_URL:
        return
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT state FROM v7_state WHERE id = 1")
                row = cur.fetchone()
                if row:
                    state = row[0]
                    PAPER_BALANCE = float(state.get("paper_balance", STARTING_BALANCE))
                    paper_position = state.get("paper_position")
                    last_entry_candle = state.get("last_entry_candle")
                    c = state.get("cooldown_until")
                    cooldown_until = datetime.fromisoformat(c) if c else None

                cur.execute("""
                    SELECT side, setup, entry_price, exit_price, qty,
                           gross_pnl, fees, pnl, reason, score, opened_at, closed_at
                    FROM v7_trades ORDER BY id DESC LIMIT 200
                """)
                trade_history = []
                for r in cur.fetchall():
                    trade_history.append({
                        "side": r[0], "setup": r[1], "entry_price": r[2],
                        "exit_price": r[3], "qty": r[4], "gross_pnl": r[5],
                        "fees": r[6], "pnl": r[7], "reason": r[8], "score": r[9],
                        "opened_at": r[10].isoformat() if r[10] else None,
                        "closed_at": r[11].isoformat() if r[11] else None,
                    })
    except Exception as e:
        print("LOAD STATE ERROR:", e)


def save_trade(t):
    if not DATABASE_URL:
        return
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO v7_trades (
                        side, setup, entry_price, exit_price, qty,
                        gross_pnl, fees, pnl, reason, score, opened_at, closed_at
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    t["side"], t["setup"], t["entry_price"], t["exit_price"], t["qty"],
                    t["gross_pnl"], t["fees"], t["pnl"], t["reason"], t["score"],
                    t["opened_at"], t["closed_at"],
                ))
            conn.commit()
    except Exception as e:
        print("SAVE TRADE ERROR:", e)


def ema(values, period):
    if len(values) < period:
        return None
    k = 2 / (period + 1)
    value = sum(values[:period]) / period
    for p in values[period:]:
        value = p * k + value * (1 - k)
    return value


def ema_series(values, period):
    if len(values) < period:
        return []
    k = 2 / (period + 1)
    out = [None] * (period - 1)
    value = sum(values[:period]) / period
    out.append(value)
    for p in values[period:]:
        value = p * k + value * (1 - k)
        out.append(value)
    return out


def rsi(values, period=14):
    if len(values) < period + 1:
        return None
    gains, losses = [], []
    for i in range(len(values) - period, len(values)):
        ch = values[i] - values[i - 1]
        gains.append(max(ch, 0))
        losses.append(max(-ch, 0))
    ag = sum(gains) / period
    al = sum(losses) / period
    if al == 0:
        return 100.0
    rs = ag / al
    return 100 - 100 / (1 + rs)


def atr(highs, lows, closes, period=14):
    if len(closes) < period + 1:
        return None
    trs = []
    for i in range(len(closes) - period, len(closes)):
        pc = closes[i - 1]
        trs.append(max(highs[i] - lows[i], abs(highs[i] - pc), abs(lows[i] - pc)))
    return sum(trs) / period


def macd_hist(values):
    if len(values) < 40:
        return None, None
    e12 = ema_series(values, 12)
    e26 = ema_series(values, 26)
    macd = []
    for i in range(len(values)):
        if i < len(e12) and i < len(e26) and e12[i] is not None and e26[i] is not None:
            macd.append(e12[i] - e26[i])
    if len(macd) < 10:
        return None, None
    signal_now = ema(macd, 9)
    hist_now = macd[-1] - signal_now
    signal_prev = ema(macd[:-1], 9)
    hist_prev = macd[-2] - signal_prev if signal_prev is not None else None
    return hist_now, hist_prev


async def get_klines(interval, limit=250):
    url = f"{BINANCE_API}/api/v3/klines?symbol={SYMBOL}&interval={interval}&limit={limit}"
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


async def get_live_price():
    url = f"{BINANCE_API}/api/v3/ticker/price?symbol={SYMBOL}"
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(url)
        response.raise_for_status()
        return float(response.json()["price"])


async def strategy_analysis():
    k1 = await get_klines("1m", 250)
    k5 = await get_klines("5m", 250)
    c1 = k1[:-1]
    c5 = k5[:-1]

    opens = [float(x[1]) for x in c1]
    highs = [float(x[2]) for x in c1]
    lows = [float(x[3]) for x in c1]
    closes = [float(x[4]) for x in c1]
    volumes = [float(x[5]) for x in c1]
    closes5 = [float(x[4]) for x in c5]

    candle_time = int(c1[-1][0])
    o, h, l, c = opens[-1], highs[-1], lows[-1], closes[-1]

    ema9 = ema(closes, 9)
    ema21 = ema(closes, 21)
    ema20_5m = ema(closes5, 20)
    ema50_5m = ema(closes5, 50)
    rsi_value = rsi(closes, 14)
    atr_value = atr(highs, lows, closes, 14)
    macd_value, macd_prev = macd_hist(closes)

    close5 = closes5[-1]
    if ema20_5m > ema50_5m and close5 >= ema20_5m * 0.997:
        trend_5m = "LONG"
    elif ema20_5m < ema50_5m and close5 <= ema20_5m * 1.003:
        trend_5m = "SHORT"
    else:
        trend_5m = "NEUTRAL"

    prev_volumes = volumes[-21:-1]
    avg_volume = sum(prev_volumes) / len(prev_volumes) if prev_volumes else 0
    volume_ratio = volumes[-1] / avg_volume if avg_volume > 0 else 0

    bullish = c > o
    bearish = c < o
    macd_up = macd_value is not None and (macd_value > 0 or (macd_prev is not None and macd_value > macd_prev))
    macd_down = macd_value is not None and (macd_value < 0 or (macd_prev is not None and macd_value < macd_prev))

    long_score = sum([
        ema9 > ema21,
        c > ema9,
        LONG_RSI_MIN <= rsi_value <= LONG_RSI_MAX,
        macd_up,
        bullish,
        volume_ratio >= MIN_VOLUME_RATIO,
    ])
    short_score = sum([
        ema9 < ema21,
        c < ema9,
        SHORT_RSI_MIN <= rsi_value <= SHORT_RSI_MAX,
        macd_down,
        bearish,
        volume_ratio >= MIN_VOLUME_RATIO,
    ])

    prior_high = max(highs[-BREAKOUT_LOOKBACK-1:-1])
    prior_low = min(lows[-BREAKOUT_LOOKBACK-1:-1])
    long_breakout = c > prior_high and volume_ratio >= 1.05
    short_breakout = c < prior_low and volume_ratio >= 1.05
    long_pullback = l <= ema9 * 1.0015 and c > ema9 and bullish
    short_pullback = h >= ema9 * 0.9985 and c < ema9 and bearish

    signal = "WAIT"
    setup = None
    score = 0

    if trend_5m == "LONG" and long_score >= MIN_ENTRY_SCORE:
        signal = "LONG"
        score = long_score
        setup = "BREAKOUT" if long_breakout else ("PULLBACK" if long_pullback else "MOMENTUM")
    elif trend_5m == "SHORT" and short_score >= MIN_ENTRY_SCORE:
        signal = "SHORT"
        score = short_score
        setup = "BREAKOUT" if short_breakout else ("PULLBACK" if short_pullback else "MOMENTUM")

    reason = f"LONG score {long_score}/6 · SHORT score {short_score}/6"
    if trend_5m == "NEUTRAL":
        reason += " · 5m trend NEUTRAL"
    elif signal == "WAIT":
        reason += f" · chybí score {MIN_ENTRY_SCORE}/6"

    return {
        "signal": signal,
        "setup": setup,
        "score": score,
        "candle_time": candle_time,
        "trend_5m": trend_5m,
        "rsi": rsi_value,
        "macd": macd_value,
        "atr": atr_value,
        "ema9": ema9,
        "ema21": ema21,
        "ema20_5m": ema20_5m,
        "ema50_5m": ema50_5m,
        "volume_ratio": volume_ratio,
        "reason": reason,
        "long_score": long_score,
        "short_score": short_score,
    }


def open_trade(side, setup, score, market_price, atr_value, candle_time):
    global paper_position, last_entry_candle
    if paper_position is not None or atr_value is None or atr_value <= 0:
        return

    risk_usdt = PAPER_BALANCE * RISK_PER_TRADE
    stop_distance = atr_value * ATR_MULTIPLIER
    qty = risk_usdt / stop_distance
    qty = min(qty, PAPER_BALANCE / market_price)
    if qty <= 0:
        return

    if side == "LONG":
        entry = market_price * (1 + SLIPPAGE_RATE)
        stop_loss = entry - stop_distance
        take_profit = entry + stop_distance * RISK_REWARD
    else:
        entry = market_price * (1 - SLIPPAGE_RATE)
        stop_loss = entry + stop_distance
        take_profit = entry - stop_distance * RISK_REWARD

    paper_position = {
        "side": side,
        "setup": setup,
        "score": score,
        "entry_price": entry,
        "qty": qty,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "risk_distance": stop_distance,
        "breakeven_moved": False,
        "opened_at": datetime.now(timezone.utc).isoformat(),
    }
    last_entry_candle = candle_time
    save_state()
    print("V7 OPEN", side, setup, score, entry)


def close_trade(market_price, reason):
    global PAPER_BALANCE, paper_position, cooldown_until, trade_history
    if not paper_position:
        return

    p = paper_position
    side = p["side"]
    entry = float(p["entry_price"])
    qty = float(p["qty"])

    if side == "LONG":
        exit_price = market_price * (1 - SLIPPAGE_RATE)
        gross_pnl = (exit_price - entry) * qty
    else:
        exit_price = market_price * (1 + SLIPPAGE_RATE)
        gross_pnl = (entry - exit_price) * qty

    fees = (entry * qty + exit_price * qty) * FEE_RATE
    net_pnl = gross_pnl - fees
    PAPER_BALANCE += net_pnl

    closed_at = datetime.now(timezone.utc)
    trade = {
        "side": side,
        "setup": p.get("setup"),
        "score": int(p.get("score", 0)),
        "entry_price": entry,
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
    trade_history = trade_history[:200]

    cooldown_until = closed_at + timedelta(
        minutes=COOLDOWN_AFTER_LOSS_MIN if net_pnl < 0 else COOLDOWN_AFTER_WIN_MIN
    )
    paper_position = None
    save_state()
    print("V7 CLOSE", reason, net_pnl)


async def manage_position():
    global paper_position
    if not paper_position:
        return

    price = await get_live_price()
    p = paper_position
    side = p["side"]
    entry = float(p["entry_price"])
    stop_loss = float(p["stop_loss"])
    take_profit = float(p["take_profit"])
    risk_distance = float(p.get("risk_distance", abs(entry - stop_loss)))

    if not p.get("breakeven_moved"):
        if side == "LONG" and price >= entry + 0.8 * risk_distance:
            p["stop_loss"] = entry * (1 + 2 * FEE_RATE + SLIPPAGE_RATE)
            p["breakeven_moved"] = True
            save_state()
            stop_loss = float(p["stop_loss"])
        elif side == "SHORT" and price <= entry - 0.8 * risk_distance:
            p["stop_loss"] = entry * (1 - 2 * FEE_RATE - SLIPPAGE_RATE)
            p["breakeven_moved"] = True
            save_state()
            stop_loss = float(p["stop_loss"])

    if side == "LONG":
        if price <= stop_loss:
            close_trade(price, "STOP LOSS / BE")
            return
        if price >= take_profit:
            close_trade(price, "TAKE PROFIT")
            return
    else:
        if price >= stop_loss:
            close_trade(price, "STOP LOSS / BE")
            return
        if price <= take_profit:
            close_trade(price, "TAKE PROFIT")
            return

    opened_at = datetime.fromisoformat(p["opened_at"])
    age_minutes = (datetime.now(timezone.utc) - opened_at).total_seconds() / 60
    if age_minutes >= MAX_TRADE_MINUTES:
        close_trade(price, "TIME EXIT")


async def trading_cycle():
    try:
        await manage_position()
        analysis = await strategy_analysis()

        if paper_position is not None:
            return

        now = datetime.now(timezone.utc)
        if cooldown_until and now < cooldown_until:
            return

        if last_entry_candle == analysis["candle_time"]:
            return

        if analysis["signal"] not in ("LONG", "SHORT"):
            return

        live_price = await get_live_price()
        open_trade(
            analysis["signal"],
            analysis["setup"],
            analysis["score"],
            live_price,
            analysis["atr"],
            analysis["candle_time"],
        )
    except Exception as e:
        print("V7 TRADING CYCLE ERROR:", e)


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
        print("XRP BOT V7 SCALPER STARTED")


def calculate_stats():
    count = len(trade_history)
    wins = sum(1 for t in trade_history if float(t["pnl"]) > 0)
    losses = count - wins
    total_pnl = sum(float(t["pnl"]) for t in trade_history)
    total_fees = sum(float(t["fees"]) for t in trade_history)
    win_rate = wins / count * 100 if count else 0
    average_pnl = total_pnl / count if count else 0

    equity = STARTING_BALANCE
    peak = equity
    max_drawdown = 0.0
    for t in reversed(trade_history):
        equity += float(t["pnl"])
        peak = max(peak, equity)
        if peak > 0:
            max_drawdown = max(max_drawdown, (peak - equity) / peak * 100)

    return {
        "count": count,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "total_pnl": total_pnl,
        "total_fees": total_fees,
        "average_pnl": average_pnl,
        "max_drawdown": max_drawdown,
    }


@app.get("/analyze")
async def analyze():
    analysis = await strategy_analysis()
    live_price = await get_live_price()
    stats = calculate_stats()

    now = datetime.now(timezone.utc)
    cooldown_text = "NE"
    if cooldown_until and now < cooldown_until:
        cooldown_text = f"{(cooldown_until - now).total_seconds() / 60:.1f} min"

    position = dict(paper_position) if paper_position else None
    unrealized_pnl = 0.0
    if position:
        entry = float(position["entry_price"])
        qty = float(position["qty"])
        unrealized_pnl = (
            (live_price - entry) * qty
            if position["side"] == "LONG"
            else (entry - live_price) * qty
        )

    return {
        "bot": "XRP BOT V7 SCALPER",
        "mode": TRADING_MODE,
        "price": live_price,
        "signal": analysis["signal"],
        "setup": analysis["setup"],
        "score": analysis["score"],
        "long_score": analysis["long_score"],
        "short_score": analysis["short_score"],
        "trend_5m": analysis["trend_5m"],
        "rsi": analysis["rsi"],
        "macd": analysis["macd"],
        "atr": analysis["atr"],
        "ema9_1m": analysis["ema9"],
        "ema21_1m": analysis["ema21"],
        "ema20_5m": analysis["ema20_5m"],
        "ema50_5m": analysis["ema50_5m"],
        "volume_ratio": analysis["volume_ratio"],
        "reason": analysis["reason"],
        "cooldown": cooldown_text,
        "paper_balance": PAPER_BALANCE,
        "equity": PAPER_BALANCE + unrealized_pnl,
        "unrealized_pnl": unrealized_pnl,
        "position": position,
        "stats": stats,
        "trade_history": trade_history[:30],
    }


@app.get("/health")
async def health():
    return {"status": "ok", "bot": "XRP BOT V7 SCALPER", "mode": TRADING_MODE}


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
<!DOCTYPE html>
<html lang="cs">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>XRP Bot V7</title>
<style>
body{background:#0b1118;color:white;font-family:Arial,sans-serif;margin:0;padding:16px}
.container{max-width:800px;margin:auto}.card{background:#151c24;border-radius:22px;padding:22px;margin-bottom:18px}
.row{display:flex;justify-content:space-between;gap:15px;margin:11px 0}.green{color:#5ee08a}.red{color:#ff6b6b}.yellow{color:#ffd166}.small{font-size:14px;opacity:.75}.trade{padding:12px 0;border-bottom:1px solid #29313b}
</style>
</head>
<body><div class="container">
<div class="card"><h1>⚡ XRP BOT V7 SCALPER</h1><div class="row"><span>Režim</span><span>PAPER</span></div><div class="row"><span>XRP cena</span><span id="price">---</span></div><div class="row"><span>Signál</span><span id="signal">---</span></div><div class="row"><span>Setup</span><span id="setup">---</span></div><div class="row"><span>5m trend</span><span id="trend">---</span></div><div class="row"><span>Cooldown</span><span id="cooldown">---</span></div></div>
<div class="card"><h2>🧠 Strategie V7</h2><div class="row"><span>LONG score</span><span id="ls">---</span></div><div class="row"><span>SHORT score</span><span id="ss">---</span></div><div class="row"><span>RSI 1m</span><span id="rsi">---</span></div><div class="row"><span>MACD</span><span id="macd">---</span></div><div class="row"><span>ATR 1m</span><span id="atr">---</span></div><div class="row"><span>EMA 9 / 21</span><span id="ema">---</span></div><div class="row"><span>EMA 20 / 50 (5m)</span><span id="ema5">---</span></div><div class="row"><span>Volume ratio</span><span id="vol">---</span></div><p id="reason">---</p></div>
<div class="card"><h2>📋 Otevřený PAPER obchod</h2><div id="position">Zatím žádný otevřený obchod</div></div>
<div class="card"><h2>💰 Účet</h2><div class="row"><span>Balance</span><span id="bal">---</span></div><div class="row"><span>Equity</span><span id="eq">---</span></div><div class="row"><span>Otevřený P&L</span><span id="upnl">---</span></div></div>
<div class="card"><h2>📊 Statistiky</h2><div class="row"><span>Obchody</span><span id="count">---</span></div><div class="row"><span>Win rate</span><span id="wr">---</span></div><div class="row"><span>Čistý P&L</span><span id="pnl">---</span></div><div class="row"><span>Max drawdown</span><span id="dd">---</span></div></div>
<div class="card"><h2>📜 Poslední obchody</h2><div id="history">Zatím žádné uzavřené obchody</div></div>
</div>
<script>
const n=(v,d=4)=>Number.isFinite(Number(v))?Number(v).toFixed(d):'---';
const cls=v=>Number(v)>0?'green':Number(v)<0?'red':'yellow';
async function refresh(){try{const d=await (await fetch('/analyze',{cache:'no-store'})).json();
document.getElementById('price').innerText=n(d.price,5);const se=document.getElementById('signal');se.innerText=d.signal??'---';se.className=cls(d.signal==='LONG'?1:d.signal==='SHORT'?-1:0);document.getElementById('setup').innerText=d.setup??'---';document.getElementById('trend').innerText=d.trend_5m??'---';document.getElementById('cooldown').innerText=d.cooldown??'---';document.getElementById('ls').innerText=(d.long_score??0)+'/6';document.getElementById('ss').innerText=(d.short_score??0)+'/6';document.getElementById('rsi').innerText=n(d.rsi,2);document.getElementById('macd').innerText=n(d.macd,6);document.getElementById('atr').innerText=n(d.atr,6);document.getElementById('ema').innerText=n(d.ema9_1m,5)+' / '+n(d.ema21_1m,5);document.getElementById('ema5').innerText=n(d.ema20_5m,5)+' / '+n(d.ema50_5m,5);document.getElementById('vol').innerText=n(d.volume_ratio,2)+'×';document.getElementById('reason').innerText=d.reason??'---';document.getElementById('bal').innerText=n(d.paper_balance,2)+' USDT';document.getElementById('eq').innerText=n(d.equity,2)+' USDT';const u=document.getElementById('upnl');u.innerText=n(d.unrealized_pnl,2)+' USDT';u.className=cls(d.unrealized_pnl);
if(d.position){const p=d.position;document.getElementById('position').innerHTML=`<div class="row"><span>Směr</span><span>${p.side}</span></div><div class="row"><span>Setup</span><span>${p.setup}</span></div><div class="row"><span>Score</span><span>${p.score}/6</span></div><div class="row"><span>Entry</span><span>${n(p.entry_price,5)}</span></div><div class="row"><span>SL</span><span>${n(p.stop_loss,5)}</span></div><div class="row"><span>TP</span><span>${n(p.take_profit,5)}</span></div>`}else document.getElementById('position').innerText='Zatím žádný otevřený obchod';
const s=d.stats??{};document.getElementById('count').innerText=s.count??0;document.getElementById('wr').innerText=n(s.win_rate,1)+' %';const pe=document.getElementById('pnl');pe.innerText=n(s.total_pnl,2)+' USDT';pe.className=cls(s.total_pnl);document.getElementById('dd').innerText=n(s.max_drawdown,2)+' %';const h=d.trade_history??[];document.getElementById('history').innerHTML=h.length?h.map(t=>`<div class="trade"><div class="row"><span>${t.side} · ${t.setup} · ${t.score}/6</span><span class="${cls(t.pnl)}">${n(t.pnl,2)} USDT</span></div><div class="small">${t.reason} · ${n(t.entry_price,5)} → ${n(t.exit_price,5)}</div></div>`).join(''):'Zatím žádné uzavřené obchody';
}catch(e){document.getElementById('reason').innerText='Chyba načítání: '+e}}
refresh();setInterval(refresh,5000);
</script></body></html>
"""
