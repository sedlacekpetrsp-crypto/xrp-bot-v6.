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
# XRP BOT V8.1 CANDLE FIXED — MULTI-COIN — PAPER ONLY
# Changes after 279-trade review:
# - 15m EMA trend + anti-chop filter
# - 5m volume confirmation
# - stricter breakout / engulfing / pin bar rules
# - true NET R:R 1:1 after simulated fees + slippage
# - risk sizing from NET stop loss, not gross price distance
# - max 2 concurrent positions
# - longer cooldowns and 120m time exit
# - separate DB tables so the old 279-trade sample is preserved
# ============================================================

app = FastAPI(title="XRP Bot V8.1 Candle Fixed")

SYMBOLS = ["XRPUSDT", "BTCUSDT", "ETHUSDT", "SOLUSDT"]
BINANCE_API = "https://data-api.binance.vision"
TRADING_MODE = "PAPER"
DATABASE_URL = os.getenv("DATABASE_URL")
STARTING_BALANCE = 10000.0

RISK_PER_TRADE = 0.005
NET_RISK_REWARD = 1.0
FEE_RATE = 0.0005
SLIPPAGE_RATE = 0.0002
ROUND_TRIP_COST_RATE = 2 * (FEE_RATE + SLIPPAGE_RATE)

STOP_BUFFER_RATE = 0.0005
MIN_STOP_RATE = 0.0040
MAX_STOP_RATE = 0.0150
MIN_TARGET_MOVE_RATE = 0.0050
MAX_NOTIONAL_SHARE = 0.50
MAX_OPEN_POSITIONS = 2

TREND_INTERVAL = "15m"
TREND_EMA_FAST = 20
TREND_EMA_SLOW = 50
MIN_TREND_STRENGTH = 0.0012

VOLUME_LOOKBACK = 20
MIN_VOLUME_BREAKOUT = 1.35
MIN_VOLUME_ENGULFING = 1.15
MIN_VOLUME_PIN = 1.20

BREAKOUT_LOOKBACK = 20
BREAKOUT_BUFFER_RATE = 0.0005
BREAKOUT_BODY_RATIO = 0.65
MAX_SIGNAL_RANGE_RATE = 0.012

COOLDOWN_AFTER_WIN_MIN = 5
COOLDOWN_AFTER_LOSS_MIN = 20
MAX_TRADE_MINUTES = 120
POSITION_LOOP_SECONDS = 5
SIGNAL_SCAN_SECONDS = 60

TRADE_TABLE = "v81fix_trades"
STATE_TABLE = "v81fix_state"

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
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {TRADE_TABLE} (
                    id SERIAL PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    setup TEXT,
                    entry_market DOUBLE PRECISION NOT NULL,
                    entry_price DOUBLE PRECISION NOT NULL,
                    exit_market DOUBLE PRECISION NOT NULL,
                    exit_price DOUBLE PRECISION NOT NULL,
                    qty DOUBLE PRECISION NOT NULL,
                    gross_pnl DOUBLE PRECISION NOT NULL,
                    slippage DOUBLE PRECISION NOT NULL,
                    fees DOUBLE PRECISION NOT NULL,
                    pnl DOUBLE PRECISION NOT NULL,
                    reason TEXT,
                    opened_at TIMESTAMPTZ,
                    closed_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {STATE_TABLE} (
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
                cur.execute(f"""
                    INSERT INTO {STATE_TABLE} (id, state) VALUES (1, %s::jsonb)
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
                cur.execute(f"SELECT state FROM {STATE_TABLE} WHERE id = 1")
                row = cur.fetchone()
                if row:
                    state = row[0] or {}
                    PAPER_BALANCE = float(state.get("paper_balance", STARTING_BALANCE))
                    positions = state.get("positions", {}) or {}
                    last_entry_candle = state.get("last_entry_candle", {}) or {}
                    cooldown_until = state.get("cooldown_until", {}) or {}

                cur.execute(f"""
                    SELECT symbol, side, setup, entry_market, entry_price,
                           exit_market, exit_price, qty, gross_pnl, slippage,
                           fees, pnl, reason, opened_at, closed_at
                    FROM {TRADE_TABLE}
                    ORDER BY id DESC LIMIT 500
                """)
                rows = cur.fetchall()
                trade_history = [{
                    "symbol": r[0],
                    "side": r[1],
                    "setup": r[2],
                    "entry_market": r[3],
                    "entry_price": r[4],
                    "exit_market": r[5],
                    "exit_price": r[6],
                    "qty": r[7],
                    "gross_pnl": r[8],
                    "slippage": r[9],
                    "fees": r[10],
                    "pnl": r[11],
                    "reason": r[12],
                    "opened_at": r[13].isoformat() if r[13] else None,
                    "closed_at": r[14].isoformat() if r[14] else None,
                } for r in rows]
    except Exception as e:
        print("LOAD STATE ERROR:", e)


def save_trade(trade):
    if not DATABASE_URL:
        return
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    INSERT INTO {TRADE_TABLE} (
                        symbol, side, setup, entry_market, entry_price,
                        exit_market, exit_price, qty, gross_pnl, slippage,
                        fees, pnl, reason, opened_at, closed_at
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    trade["symbol"], trade["side"], trade["setup"],
                    trade["entry_market"], trade["entry_price"],
                    trade["exit_market"], trade["exit_price"], trade["qty"],
                    trade["gross_pnl"], trade["slippage"], trade["fees"],
                    trade["pnl"], trade["reason"], trade["opened_at"],
                    trade["closed_at"],
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


async def get_klines(symbol, interval="5m", limit=100):
    return await binance_get("/api/v3/klines", {
        "symbol": symbol,
        "interval": interval,
        "limit": limit,
    })


async def get_live_price(symbol, max_age=2.0):
    cached = price_cache.get(symbol)
    now = time.monotonic()
    if cached and now - cached["ts"] <= max_age:
        return cached["price"]
    data = await binance_get("/api/v3/ticker/price", {"symbol": symbol})
    price = float(data["price"])
    price_cache[symbol] = {
        "price": price,
        "ts": now,
        "updated_at": utcnow().isoformat(),
    }
    return price


def ema(values, period):
    if not values:
        return 0.0
    alpha = 2.0 / (period + 1.0)
    value = float(values[0])
    for x in values[1:]:
        value = alpha * float(x) + (1.0 - alpha) * value
    return value


def candle_parts(k):
    o, h, l, c = float(k[1]), float(k[2]), float(k[3]), float(k[4])
    body = abs(c - o)
    rng = max(h - l, 1e-12)
    upper = h - max(o, c)
    lower = min(o, c) - l
    return o, h, l, c, body, rng, upper, lower


def volume_ratio(closed):
    if len(closed) < VOLUME_LOOKBACK + 1:
        return 0.0
    cur_v = float(closed[-1][5])
    prev = [float(x[5]) for x in closed[-(VOLUME_LOOKBACK + 1):-1]]
    avg_v = sum(prev) / len(prev) if prev else 0.0
    return cur_v / avg_v if avg_v > 0 else 0.0


def detect_setup(closed):
    need = max(BREAKOUT_LOOKBACK + 2, VOLUME_LOOKBACK + 2)
    if len(closed) < need:
        return {"signal": "WAIT", "setup": None, "reason": "málo dat"}

    prev, cur = closed[-2], closed[-1]
    p_o, p_h, p_l, p_c, p_body, p_rng, p_up, p_low = candle_parts(prev)
    c_o, c_h, c_l, c_c, c_body, c_rng, c_up, c_low = candle_parts(cur)
    candle_time = int(cur[0])
    body_ratio = c_body / c_rng
    range_rate = c_rng / max(c_c, 1e-12)
    vol_ratio = volume_ratio(closed)

    recent = closed[-(BREAKOUT_LOOKBACK + 1):-1]
    prior_high = max(float(x[2]) for x in recent)
    prior_low = min(float(x[3]) for x in recent)

    breakout_up_level = prior_high * (1 + BREAKOUT_BUFFER_RATE)
    breakout_down_level = prior_low * (1 - BREAKOUT_BUFFER_RATE)

    bullish_breakout = (
        c_c > breakout_up_level
        and c_c > c_o
        and body_ratio >= BREAKOUT_BODY_RATIO
        and c_up <= c_rng * 0.18
        and vol_ratio >= MIN_VOLUME_BREAKOUT
    )
    bearish_breakout = (
        c_c < breakout_down_level
        and c_c < c_o
        and body_ratio >= BREAKOUT_BODY_RATIO
        and c_low <= c_rng * 0.18
        and vol_ratio >= MIN_VOLUME_BREAKOUT
    )

    bullish_engulfing = (
        p_c < p_o and c_c > c_o
        and c_o <= p_c and c_c >= p_o
        and c_body >= p_body * 1.15
        and body_ratio >= 0.50
        and vol_ratio >= MIN_VOLUME_ENGULFING
    )
    bearish_engulfing = (
        p_c > p_o and c_c < c_o
        and c_o >= p_c and c_c <= p_o
        and c_body >= p_body * 1.15
        and body_ratio >= 0.50
        and vol_ratio >= MIN_VOLUME_ENGULFING
    )

    bullish_pin = (
        c_c > c_o
        and c_low >= max(c_body * 2.2, c_rng * 0.50)
        and c_up <= c_rng * 0.15
        and c_c >= c_l + c_rng * 0.72
        and vol_ratio >= MIN_VOLUME_PIN
    )
    bearish_pin = (
        c_c < c_o
        and c_up >= max(c_body * 2.2, c_rng * 0.50)
        and c_low <= c_rng * 0.15
        and c_c <= c_l + c_rng * 0.28
        and vol_ratio >= MIN_VOLUME_PIN
    )

    if range_rate > MAX_SIGNAL_RANGE_RATE:
        signal, setup = "WAIT", None
        reason = "svíčka je příliš velká - nechasing"
    elif bullish_breakout:
        signal, setup = "LONG", "BREAKOUT"
        reason = "breakout + volume potvrzen"
    elif bearish_breakout:
        signal, setup = "SHORT", "BREAKOUT"
        reason = "breakout + volume potvrzen"
    elif bullish_engulfing:
        signal, setup = "LONG", "BULL ENGULFING"
        reason = "engulfing + volume potvrzen"
    elif bearish_engulfing:
        signal, setup = "SHORT", "BEAR ENGULFING"
        reason = "engulfing + volume potvrzen"
    elif bullish_pin:
        signal, setup = "LONG", "BULL PIN BAR"
        reason = "pin bar + volume potvrzen"
    elif bearish_pin:
        signal, setup = "SHORT", "BEAR PIN BAR"
        reason = "pin bar + volume potvrzen"
    else:
        signal, setup = "WAIT", None
        reason = "bez kvalitní svíčkové formace / volume"

    return {
        "signal": signal,
        "setup": setup,
        "reason": reason,
        "candle_time": candle_time,
        "price_closed": c_c,
        "signal_high": c_h,
        "signal_low": c_l,
        "body_ratio": body_ratio,
        "range_rate": range_rate,
        "volume_ratio": vol_ratio,
    }


def trend_filter(trend_closed, side):
    if len(trend_closed) < TREND_EMA_SLOW + 5:
        return False, "málo 15m dat", {}

    closes = [float(x[4]) for x in trend_closed]
    close = closes[-1]
    fast = ema(closes[-80:], TREND_EMA_FAST)
    slow = ema(closes[-100:], TREND_EMA_SLOW)
    strength = abs(fast - slow) / max(close, 1e-12)

    if strength < MIN_TREND_STRENGTH:
        return False, "15m chop / slabý trend", {
            "trend": "CHOP",
            "ema_fast": fast,
            "ema_slow": slow,
            "trend_strength": strength,
        }

    if fast > slow and close > fast:
        trend = "LONG"
    elif fast < slow and close < fast:
        trend = "SHORT"
    else:
        trend = "MIXED"

    ok = trend == side
    return ok, ("trend potvrzen" if ok else "signál proti 15m trendu"), {
        "trend": trend,
        "ema_fast": fast,
        "ema_slow": slow,
        "trend_strength": strength,
    }


async def strategy_analysis(symbol):
    k5, k15 = await asyncio.gather(
        get_klines(symbol, "5m", 100),
        get_klines(symbol, TREND_INTERVAL, 100),
    )
    closed5 = k5[:-1]
    closed15 = k15[:-1]

    result = detect_setup(closed5)
    result["symbol"] = symbol

    side = result.get("signal")
    if side in ("LONG", "SHORT"):
        ok, trend_reason, trend_meta = trend_filter(closed15, side)
        result.update(trend_meta)
        if not ok:
            result["raw_signal"] = side
            result["signal"] = "WAIT"
            result["reason"] = trend_reason
        else:
            result["reason"] = f'{result["reason"]} • {trend_reason}'
    else:
        _, _, trend_meta = trend_filter(closed15, "LONG")
        result.update(trend_meta)

    return result


def cooldown_active(symbol):
    value = cooldown_until.get(symbol)
    if not value:
        return False
    try:
        return utcnow() < datetime.fromisoformat(value)
    except Exception:
        return False


def estimated_net_per_unit(side, entry_exec, exit_market):
    if side == "LONG":
        exit_exec = exit_market * (1 - SLIPPAGE_RATE)
        gross_exec = exit_exec - entry_exec
    else:
        exit_exec = exit_market * (1 + SLIPPAGE_RATE)
        gross_exec = entry_exec - exit_exec
    fees = (entry_exec + exit_exec) * FEE_RATE
    return gross_exec - fees


def target_market_for_net_profit(side, entry_exec, target_net_per_unit):
    f = FEE_RATE
    s = SLIPPAGE_RATE
    if side == "LONG":
        exit_exec = (target_net_per_unit + entry_exec * (1 + f)) / (1 - f)
        return exit_exec / (1 - s)
    exit_exec = (entry_exec * (1 - f) - target_net_per_unit) / (1 + f)
    return exit_exec / (1 + s)


def open_trade(symbol, analysis, market_price):
    global positions, last_entry_candle

    if symbol in positions:
        return False
    if len(positions) >= MAX_OPEN_POSITIONS:
        return False

    side = analysis.get("signal")
    if side not in ("LONG", "SHORT"):
        return False

    signal_low = float(analysis["signal_low"])
    signal_high = float(analysis["signal_high"])

    if side == "LONG":
        entry_market = market_price
        entry_price = entry_market * (1 + SLIPPAGE_RATE)
        structural_stop = signal_low * (1 - STOP_BUFFER_RATE)
        min_stop_market = entry_market * (1 - MIN_STOP_RATE)
        stop_loss = min(structural_stop, min_stop_market)
        gross_stop_rate = (entry_market - stop_loss) / max(entry_market, 1e-12)
    else:
        entry_market = market_price
        entry_price = entry_market * (1 - SLIPPAGE_RATE)
        structural_stop = signal_high * (1 + STOP_BUFFER_RATE)
        min_stop_market = entry_market * (1 + MIN_STOP_RATE)
        stop_loss = max(structural_stop, min_stop_market)
        gross_stop_rate = (stop_loss - entry_market) / max(entry_market, 1e-12)

    if gross_stop_rate <= 0 or gross_stop_rate > MAX_STOP_RATE:
        print("SKIP V8.1 FIX", symbol, "STOP_OUT_OF_RANGE", gross_stop_rate)
        return False

    stop_net_per_unit = estimated_net_per_unit(side, entry_price, stop_loss)
    net_loss_per_unit = -stop_net_per_unit
    if net_loss_per_unit <= 0:
        print("SKIP V8.1 FIX", symbol, "INVALID_NET_RISK", stop_net_per_unit)
        return False

    target_net_per_unit = net_loss_per_unit * NET_RISK_REWARD
    take_profit = target_market_for_net_profit(side, entry_price, target_net_per_unit)

    if side == "LONG":
        target_move_rate = (take_profit - entry_market) / max(entry_market, 1e-12)
    else:
        target_move_rate = (entry_market - take_profit) / max(entry_market, 1e-12)

    if target_move_rate < MIN_TARGET_MOVE_RATE:
        print("SKIP V8.1 FIX", symbol, "TARGET_TOO_SMALL", target_move_rate)
        return False

    risk_usdt = PAPER_BALANCE * RISK_PER_TRADE
    qty_by_risk = risk_usdt / net_loss_per_unit
    max_notional = PAPER_BALANCE * MAX_NOTIONAL_SHARE
    qty_by_notional = max_notional / entry_price
    qty = min(qty_by_risk, qty_by_notional)
    if qty <= 0:
        return False

    actual_net_risk = net_loss_per_unit * qty
    expected_net_reward = target_net_per_unit * qty

    positions[symbol] = {
        "symbol": symbol,
        "side": side,
        "setup": analysis["setup"],
        "entry_market": entry_market,
        "entry_price": entry_price,
        "qty": qty,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "risk_usdt": actual_net_risk,
        "expected_reward_usdt": expected_net_reward,
        "net_rr": expected_net_reward / max(actual_net_risk, 1e-12),
        "opened_at": utcnow().isoformat(),
        "signal_candle": analysis["candle_time"],
        "volume_ratio": analysis.get("volume_ratio"),
        "trend": analysis.get("trend"),
        "trend_strength": analysis.get("trend_strength"),
    }
    last_entry_candle[symbol] = analysis["candle_time"]
    save_state()
    print(
        "OPEN V8.1 FIX", symbol, side, analysis["setup"],
        "entry", entry_price, "SL", stop_loss, "TP", take_profit,
        "netRR", positions[symbol]["net_rr"],
    )
    return True


def close_trade(symbol, market_price, reason):
    global PAPER_BALANCE, trade_history, positions, cooldown_until

    p = positions.get(symbol)
    if not p:
        return

    side = p["side"]
    entry_market = float(p.get("entry_market", p["entry_price"]))
    entry_price = float(p["entry_price"])
    exit_market = float(market_price)
    qty = float(p["qty"])

    if side == "LONG":
        exit_price = exit_market * (1 - SLIPPAGE_RATE)
        ideal_gross = (exit_market - entry_market) * qty
        execution_gross = (exit_price - entry_price) * qty
        slippage_cost = max(ideal_gross - execution_gross, 0.0)
    else:
        exit_price = exit_market * (1 + SLIPPAGE_RATE)
        ideal_gross = (entry_market - exit_market) * qty
        execution_gross = (entry_price - exit_price) * qty
        slippage_cost = max(ideal_gross - execution_gross, 0.0)

    fees = (entry_price * qty + exit_price * qty) * FEE_RATE
    net_pnl = execution_gross - fees
    PAPER_BALANCE += net_pnl

    closed_at = utcnow()
    trade = {
        "symbol": symbol,
        "side": side,
        "setup": p["setup"],
        "entry_market": entry_market,
        "entry_price": entry_price,
        "exit_market": exit_market,
        "exit_price": exit_price,
        "qty": qty,
        "gross_pnl": ideal_gross,
        "slippage": slippage_cost,
        "fees": fees,
        "pnl": net_pnl,
        "reason": reason,
        "opened_at": p["opened_at"],
        "closed_at": closed_at.isoformat(),
    }

    save_trade(trade)
    trade_history.insert(0, trade)
    trade_history = trade_history[:500]

    minutes = COOLDOWN_AFTER_LOSS_MIN if net_pnl < 0 else COOLDOWN_AFTER_WIN_MIN
    cooldown_until[symbol] = (closed_at + timedelta(minutes=minutes)).isoformat()
    positions.pop(symbol, None)
    save_state()
    print("CLOSE V8.1 FIX", symbol, reason, net_pnl)


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
        if len(positions) >= MAX_OPEN_POSITIONS:
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
            "symbol": symbol,
            "signal": "ERROR",
            "setup": None,
            "reason": str(e),
        }
        print("SYMBOL SCAN ERROR", symbol, e)


async def trading_loop():
    global last_cycle_at, last_signal_scan_at, last_error
    next_scan = 0.0
    while True:
        try:
            if positions:
                await asyncio.gather(
                    *(manage_position(s) for s in list(positions.keys())),
                    return_exceptions=True,
                )

            now = time.monotonic()
            if now >= next_scan:
                for symbol in SYMBOLS:
                    await scan_symbol(symbol)
                last_signal_scan_at = utcnow().isoformat()
                next_scan = now + SIGNAL_SCAN_SECONDS

            last_cycle_at = utcnow().isoformat()
        except Exception as e:
            last_error = f"LOOP: {type(e).__name__}: {e}"
            print("V8.1 FIX LOOP ERROR", e)

        await asyncio.sleep(POSITION_LOOP_SECONDS)


def calculate_stats():
    count = len(trade_history)
    wins_list = [t for t in trade_history if float(t["pnl"]) > 0]
    losses_list = [t for t in trade_history if float(t["pnl"]) <= 0]
    total_pnl = sum(float(t["pnl"]) for t in trade_history)
    total_fees = sum(float(t["fees"]) for t in trade_history)
    total_slippage = sum(float(t.get("slippage", 0)) for t in trade_history)
    gp = sum(float(t["pnl"]) for t in wins_list)
    gl = abs(sum(float(t["pnl"]) for t in losses_list))
    avg_win = gp / len(wins_list) if wins_list else 0.0
    avg_loss = gl / len(losses_list) if losses_list else 0.0
    realized_rr = avg_win / avg_loss if avg_loss else 0.0

    return {
        "count": count,
        "wins": len(wins_list),
        "losses": len(losses_list),
        "win_rate": (len(wins_list) / count * 100) if count else 0,
        "total_pnl": total_pnl,
        "total_fees": total_fees,
        "total_slippage": total_slippage,
        "total_costs": total_fees + total_slippage,
        "average_pnl": (total_pnl / count) if count else 0,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "realized_rr": realized_rr,
        "profit_factor": (gp / gl) if gl else (999 if gp else 0),
    }


@app.on_event("startup")
async def startup_event():
    global bot_loop_started, bot_task, http_client, started_at
    started_at = utcnow()
    limits = httpx.Limits(
        max_connections=8,
        max_keepalive_connections=4,
        keepalive_expiry=30.0,
    )
    http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(10.0),
        limits=limits,
        headers={"User-Agent": "xrp-bot-v8.1-fixed/2.0"},
    )
    init_db()
    load_state()
    if not bot_loop_started:
        bot_loop_started = True
        bot_task = asyncio.create_task(trading_loop())
        print("XRP BOT V8.1 CANDLE FIXED STARTED")


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
            "symbol": symbol,
            "signal": "WAIT",
            "setup": None,
            "reason": "čekám na první scan",
        })

        p = positions.get(symbol)
        cached = price_cache.get(symbol)
        price = cached["price"] if cached else a.get("price_closed")

        a["price"] = price
        a["cooldown"] = cooldown_active(symbol)
        a["position"] = p

        upnl = 0.0
        if p and price is not None:
            upnl = estimated_net_per_unit(
                p["side"],
                float(p["entry_price"]),
                float(price),
            ) * float(p["qty"])
            unrealized_total += upnl

        a["unrealized_pnl"] = upnl
        market[symbol] = a

    return {
        "bot": "XRP BOT V8.1 CANDLE FIXED",
        "mode": TRADING_MODE,
        "strategy": "PRICE ACTION + 15m TREND + VOLUME",
        "risk_reward": "NET 1:1 after costs",
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
        "settings": {
            "max_open_positions": MAX_OPEN_POSITIONS,
            "trend_interval": TREND_INTERVAL,
            "min_trend_strength_pct": MIN_TREND_STRENGTH * 100,
            "min_stop_pct": MIN_STOP_RATE * 100,
            "max_stop_pct": MAX_STOP_RATE * 100,
            "min_target_pct": MIN_TARGET_MOVE_RATE * 100,
            "max_trade_minutes": MAX_TRADE_MINUTES,
            "fee_pct_each_side": FEE_RATE * 100,
            "slippage_pct_each_side": SLIPPAGE_RATE * 100,
        },
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "bot": "XRP BOT V8.1 CANDLE FIXED",
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
<title>Bot V8.1 Candle Fixed</title>
<style>
body{margin:0;background:#0b1118;color:#edf3f8;font-family:Arial,sans-serif}
.wrap{max-width:1050px;margin:auto;padding:14px}
.card{background:#151c24;border:1px solid #26313d;border-radius:16px;padding:16px;margin-bottom:12px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px}
.coin{background:#10171f;border-radius:12px;padding:12px}
.row{display:flex;justify-content:space-between;gap:12px;margin:6px 0}
.green{color:#5ce68b}.red{color:#ff6b6b}.yellow{color:#ffd166}.muted{opacity:.65}
.trade{display:grid;grid-template-columns:1fr .7fr 1.2fr 1fr .8fr;gap:8px;padding:9px 0;border-bottom:1px solid #29343e;font-size:13px}
h1{font-size:24px;margin:0 0 8px}h2{font-size:18px}
</style></head>
<body><div class="wrap">
<div class="card"><h1>🕯️ BOT V8.1 CANDLE — FIXED</h1>
<div class="muted">PAPER • Price Action + 15m trend + volume • NET R:R 1:1 • risk 0.5 %</div></div>
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
      ['Fees',f(s.total_fees,2)+' USDT'],
      ['Slippage',f(s.total_slippage,2)+' USDT'],
      ['Real R:R',f(s.realized_rr,2)+':1'],
      ['Profit factor',f(s.profit_factor,2)]
    ].map(x=>`<div class="coin"><div class="muted">${x[0]}</div><b>${x[1]}</b></div>`).join('');

    document.getElementById('coins').innerHTML=Object.values(d.market||{}).map(x=>{
      const p=x.position, sig=x.signal||'WAIT', cls=sig==='LONG'?'green':sig==='SHORT'?'red':'yellow';
      return `<div class="coin"><b>${x.symbol}</b>
      <div class="row"><span>Signál</span><b class="${cls}">${sig}</b></div>
      <div class="row"><span>Cena</span><span>${x.price==null?'—':f(x.price,6)}</span></div>
      <div class="row"><span>Setup</span><span>${x.setup||'—'}</span></div>
      <div class="row"><span>15m trend</span><span>${x.trend||'—'}</span></div>
      <div class="row"><span>Volume</span><span>${x.volume_ratio==null?'—':f(x.volume_ratio,2)+'x'}</span></div>
      <div class="row"><span>Pozice</span><span>${p?p.side:'—'}</span></div>
      <div class="row"><span>uPnL net</span><span>${f(x.unrealized_pnl,2)}</span></div>
      <div class="muted">${x.reason||''}</div></div>`;
    }).join('');

    document.getElementById('trades').innerHTML=(d.trade_history||[]).map(t=>
      `<div class="trade"><span>${t.symbol}</span><span>${t.side}</span><span>${t.setup||'—'}</span><span>${t.reason}</span><span class="${Number(t.pnl)>=0?'green':'red'}">${f(t.pnl,2)}</span></div>`
    ).join('')||'<div class="muted">Nový test zatím bez obchodů.</div>';

    document.getElementById('health').textContent=
      `Poslední cyklus: ${d.last_cycle_at||'—'} • scan: ${d.last_signal_scan_at||'—'} • 429: ${d.http_429_count||0} • chyba: ${d.last_error||'žádná'}`;
  }catch(e){document.getElementById('health').textContent='Dashboard error: '+e}
}
refresh(); setInterval(refresh,10000);
</script></body></html>
"""
