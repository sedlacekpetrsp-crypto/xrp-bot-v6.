import os
import json
import asyncio
from datetime import datetime, timezone, timedelta

import httpx
import psycopg
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="V7 Pro Multi Scalper")

SYMBOLS = ["XRPUSDC", "ETHUSDC", "SOLUSDC"]
BINANCE_API = "https://data-api.binance.vision"
TRADING_MODE = "PAPER"
DATABASE_URL = os.getenv("DATABASE_URL")
STARTING_BALANCE = 10000.0

# Risk and execution simulation
RISK_PER_TRADE = 0.0025          # 0.25 % account risk per trade
BASE_RISK_REWARD = 1.30
ATR_MULTIPLIER = 0.90
FEE_RATE = 0.0005               # 0.05 % each side
SLIPPAGE_RATE = 0.0002          # 0.02 % simulated slippage each side
MAX_TRADE_MINUTES = 6
COOLDOWN_AFTER_WIN_MIN = 0
COOLDOWN_AFTER_LOSS_MIN = 1
LOOP_SECONDS = 10
DAILY_LOSS_LIMIT_R = 3.0
MAX_CONSECUTIVE_LOSSES = 3
LOSS_STREAK_COOLDOWN_MIN = 30
MAX_OPEN_POSITIONS = 1          # correlation protection: only one crypto position at once

# Strategy filters
BREAKOUT_LOOKBACK = 12
ORDER_BOOK_LEVELS = 20
TREND_ADX_MIN = 18.0
RANGE_ADX_MAX = 16.0
TREND_EMA_SEPARATION_MIN = 0.0008
MIN_VOLUME_RATIO_TREND = 0.90
MIN_VOLUME_RATIO_BREAKOUT = 1.10
MIN_VOLUME_RATIO_RANGE = 0.75
MIN_BOOK_IMBALANCE_LONG = 0.53
MAX_BOOK_IMBALANCE_SHORT = 0.47
LONG_RSI_MIN = 42
LONG_RSI_MAX = 72
SHORT_RSI_MIN = 28
SHORT_RSI_MAX = 58
RANGE_RSI_LONG_MAX = 38
RANGE_RSI_SHORT_MIN = 62
MIN_ENTRY_SCORE = 5
VWAP_STRETCH_ATR = 1.20

PAPER_BALANCE = STARTING_BALANCE
paper_position = None
trade_history = []
last_entry_candle = {}
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
            cur.execute("ALTER TABLE v7_trades ADD COLUMN IF NOT EXISTS symbol TEXT NOT NULL DEFAULT 'XRPUSDT'")
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
                    if paper_position and "symbol" not in paper_position:
                        paper_position["symbol"] = "XRPUSDT"
                    lec = state.get("last_entry_candle", {})
                    if isinstance(lec, dict):
                        last_entry_candle = lec
                    elif lec is not None:
                        last_entry_candle = {"XRPUSDC": lec}
                    else:
                        last_entry_candle = {}
                    c = state.get("cooldown_until")
                    cooldown_until = datetime.fromisoformat(c) if c else None

                cur.execute("""
                    SELECT symbol, side, setup, entry_price, exit_price, qty,
                           gross_pnl, fees, pnl, reason, score, opened_at, closed_at
                    FROM v7_trades ORDER BY id DESC LIMIT 300
                """)
                trade_history = []
                for r in cur.fetchall():
                    trade_history.append({
                        "symbol": r[0], "side": r[1], "setup": r[2],
                        "entry_price": r[3], "exit_price": r[4], "qty": r[5],
                        "gross_pnl": r[6], "fees": r[7], "pnl": r[8],
                        "reason": r[9], "score": r[10],
                        "opened_at": r[11].isoformat() if r[11] else None,
                        "closed_at": r[12].isoformat() if r[12] else None,
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
                        symbol, side, setup, entry_price, exit_price, qty,
                        gross_pnl, fees, pnl, reason, score, opened_at, closed_at
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    t["symbol"], t["side"], t["setup"], t["entry_price"],
                    t["exit_price"], t["qty"], t["gross_pnl"], t["fees"],
                    t["pnl"], t["reason"], t["score"], t["opened_at"], t["closed_at"],
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


def adx(highs, lows, closes, period=14):
    if len(closes) < period * 2 + 2:
        return None
    tr, plus_dm, minus_dm = [], [], []
    for i in range(1, len(closes)):
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        plus_dm.append(up if up > down and up > 0 else 0.0)
        minus_dm.append(down if down > up and down > 0 else 0.0)
        tr.append(max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1])))
    dxs = []
    for end in range(period, len(tr) + 1):
        tr_sum = sum(tr[end - period:end])
        if tr_sum <= 0:
            continue
        pdi = 100 * sum(plus_dm[end - period:end]) / tr_sum
        mdi = 100 * sum(minus_dm[end - period:end]) / tr_sum
        denom = pdi + mdi
        dxs.append(100 * abs(pdi - mdi) / denom if denom > 0 else 0.0)
    return sum(dxs[-period:]) / min(period, len(dxs)) if dxs else None


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


def rolling_vwap(highs, lows, closes, volumes, lookback=120):
    n = min(lookback, len(closes))
    if n <= 0:
        return None
    pv = 0.0
    vol = 0.0
    for h, l, c, v in zip(highs[-n:], lows[-n:], closes[-n:], volumes[-n:]):
        typical = (h + l + c) / 3
        pv += typical * v
        vol += v
    return pv / vol if vol > 0 else None


async def get_klines(symbol, interval, limit=250):
    url = f"{BINANCE_API}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


async def get_live_price(symbol):
    url = f"{BINANCE_API}/api/v3/ticker/price?symbol={symbol}"
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(url)
        response.raise_for_status()
        return float(response.json()["price"])


async def get_order_book_imbalance(symbol):
    url = f"{BINANCE_API}/api/v3/depth?symbol={symbol}&limit={ORDER_BOOK_LEVELS}"
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()
    bid_notional = sum(float(p) * float(q) for p, q in data.get("bids", []))
    ask_notional = sum(float(p) * float(q) for p, q in data.get("asks", []))
    total = bid_notional + ask_notional
    return bid_notional / total if total > 0 else 0.5


def daily_risk_status():
    today = datetime.now(timezone.utc).date()
    day_pnl = 0.0
    today_trades = []
    for t in trade_history:
        try:
            closed = datetime.fromisoformat(t["closed_at"])
        except Exception:
            continue
        if closed.date() == today:
            today_trades.append(t)
            day_pnl += float(t["pnl"])
    consecutive_losses = 0
    for t in today_trades:
        if float(t["pnl"]) < 0:
            consecutive_losses += 1
        else:
            break
    risk_per_trade_usdc = max(PAPER_BALANCE, 1.0) * RISK_PER_TRADE
    limit_usdc = risk_per_trade_usdc * DAILY_LOSS_LIMIT_R
    daily_blocked = day_pnl <= -limit_usdc
    return day_pnl, consecutive_losses, daily_blocked, limit_usdc


async def strategy_analysis(symbol):
    k1_task = get_klines(symbol, "1m", 250)
    k5_task = get_klines(symbol, "5m", 250)
    book_task = get_order_book_imbalance(symbol)
    k1, k5, book_imbalance = await asyncio.gather(k1_task, k5_task, book_task)

    c1 = k1[:-1]
    c5 = k5[:-1]
    opens = [float(x[1]) for x in c1]
    highs = [float(x[2]) for x in c1]
    lows = [float(x[3]) for x in c1]
    closes = [float(x[4]) for x in c1]
    volumes = [float(x[5]) for x in c1]
    highs5 = [float(x[2]) for x in c5]
    lows5 = [float(x[3]) for x in c5]
    closes5 = [float(x[4]) for x in c5]

    candle_time = int(c1[-1][0])
    o, h, l, c = opens[-1], highs[-1], lows[-1], closes[-1]
    ema9 = ema(closes, 9)
    ema21 = ema(closes, 21)
    ema20_5m = ema(closes5, 20)
    ema50_5m = ema(closes5, 50)
    rsi_value = rsi(closes, 14)
    atr_value = atr(highs, lows, closes, 14)
    adx5 = adx(highs5, lows5, closes5, 14)
    macd_value, macd_prev = macd_hist(closes)
    vwap_value = rolling_vwap(highs, lows, closes, volumes, 120)

    prev_volumes = volumes[-21:-1]
    avg_volume = sum(prev_volumes) / len(prev_volumes) if prev_volumes else 0
    volume_ratio = volumes[-1] / avg_volume if avg_volume > 0 else 0

    ema_sep = abs(ema20_5m - ema50_5m) / c if c > 0 else 0
    close5 = closes5[-1]
    if adx5 is not None and adx5 >= TREND_ADX_MIN and ema_sep >= TREND_EMA_SEPARATION_MIN:
        if close5 > ema20_5m > ema50_5m:
            regime = "TREND_LONG"
        elif close5 < ema20_5m < ema50_5m:
            regime = "TREND_SHORT"
        else:
            regime = "TRANSITION"
    elif adx5 is not None and adx5 <= RANGE_ADX_MAX:
        regime = "RANGE"
    else:
        regime = "TRANSITION"

    bullish = c > o
    bearish = c < o
    candle_range = max(h - l, 1e-12)
    bull_close_strength = (c - l) / candle_range
    bear_close_strength = (h - c) / candle_range
    macd_up = macd_value is not None and (macd_value > 0 or (macd_prev is not None and macd_value > macd_prev))
    macd_down = macd_value is not None and (macd_value < 0 or (macd_prev is not None and macd_value < macd_prev))

    prior_high = max(highs[-BREAKOUT_LOOKBACK-1:-1])
    prior_low = min(lows[-BREAKOUT_LOOKBACK-1:-1])
    long_breakout = c > prior_high and volume_ratio >= MIN_VOLUME_RATIO_BREAKOUT
    short_breakout = c < prior_low and volume_ratio >= MIN_VOLUME_RATIO_BREAKOUT
    failed_high = h > prior_high and c < prior_high and bear_close_strength >= 0.60
    failed_low = l < prior_low and c > prior_low and bull_close_strength >= 0.60

    near_fast_ema_long = l <= max(ema9, ema21) * 1.0015 and c > ema9
    near_fast_ema_short = h >= min(ema9, ema21) * 0.9985 and c < ema9
    above_vwap = vwap_value is not None and c >= vwap_value
    below_vwap = vwap_value is not None and c <= vwap_value
    vwap_distance = abs(c - vwap_value) if vwap_value is not None else 0.0

    long_score = sum([
        ema9 > ema21,
        c > ema9,
        LONG_RSI_MIN <= rsi_value <= LONG_RSI_MAX,
        macd_up,
        bull_close_strength >= 0.55,
        volume_ratio >= MIN_VOLUME_RATIO_TREND,
        book_imbalance >= MIN_BOOK_IMBALANCE_LONG,
        above_vwap,
    ])
    short_score = sum([
        ema9 < ema21,
        c < ema9,
        SHORT_RSI_MIN <= rsi_value <= SHORT_RSI_MAX,
        macd_down,
        bear_close_strength >= 0.55,
        volume_ratio >= MIN_VOLUME_RATIO_TREND,
        book_imbalance <= MAX_BOOK_IMBALANCE_SHORT,
        below_vwap,
    ])

    signal = "WAIT"
    setup = None
    score = 0

    if regime == "TREND_LONG":
        if long_breakout and long_score >= MIN_ENTRY_SCORE:
            signal, setup, score = "LONG", "BREAKOUT", long_score
        elif near_fast_ema_long and long_score >= MIN_ENTRY_SCORE:
            signal, setup, score = "LONG", "TREND_PULLBACK", long_score
        elif long_score >= MIN_ENTRY_SCORE + 1:
            signal, setup, score = "LONG", "MOMENTUM", long_score
    elif regime == "TREND_SHORT":
        if short_breakout and short_score >= MIN_ENTRY_SCORE:
            signal, setup, score = "SHORT", "BREAKOUT", short_score
        elif near_fast_ema_short and short_score >= MIN_ENTRY_SCORE:
            signal, setup, score = "SHORT", "TREND_PULLBACK", short_score
        elif short_score >= MIN_ENTRY_SCORE + 1:
            signal, setup, score = "SHORT", "MOMENTUM", short_score
    elif regime == "TRANSITION" and long_score == 8:
        signal, setup, score = "LONG", "TRANSITION_8_OF_8", 8
    elif regime == "TRANSITION" and short_score == 8:
        signal, setup, score = "SHORT", "TRANSITION_8_OF_8", 8
    elif regime in ("RANGE", "TRANSITION") and atr_value and vwap_value:
        stretched = vwap_distance >= atr_value * VWAP_STRETCH_ATR
        range_long = failed_low and stretched and c < vwap_value and rsi_value <= RANGE_RSI_LONG_MAX and volume_ratio >= MIN_VOLUME_RATIO_RANGE and book_imbalance >= 0.50
        range_short = failed_high and stretched and c > vwap_value and rsi_value >= RANGE_RSI_SHORT_MIN and volume_ratio >= MIN_VOLUME_RATIO_RANGE and book_imbalance <= 0.50
        if range_long:
            signal, setup, score = "LONG", "FAILED_BREAKOUT", 6
        elif range_short:
            signal, setup, score = "SHORT", "FAILED_BREAKOUT", 6

    reason = (
        f"{symbol} · Regime {regime} · LONG {long_score}/8 · SHORT {short_score}/8 · "
        f"Book {book_imbalance:.2f} · Vol {volume_ratio:.2f}× · "
        + (f"ADX5 {adx5:.1f}" if adx5 is not None else "ADX5 ---")
    )

    return {
        "symbol": symbol, "signal": signal, "setup": setup, "score": score,
        "candle_time": candle_time, "regime": regime,
        "rsi": rsi_value, "macd": macd_value, "atr": atr_value,
        "adx5": adx5, "ema9": ema9, "ema21": ema21,
        "ema20_5m": ema20_5m, "ema50_5m": ema50_5m,
        "vwap": vwap_value, "volume_ratio": volume_ratio,
        "book_imbalance": book_imbalance, "reason": reason,
        "long_score": long_score, "short_score": short_score,
    }


def open_trade(symbol, side, setup, score, market_price, atr_value, candle_time):
    global paper_position, last_entry_candle
    if paper_position is not None or atr_value is None or atr_value <= 0:
        return
    risk_usdc = PAPER_BALANCE * RISK_PER_TRADE
    setup_atr_mult = 0.80 if setup == "FAILED_BREAKOUT" else ATR_MULTIPLIER
    setup_rr = 1.15 if setup == "FAILED_BREAKOUT" else BASE_RISK_REWARD
    stop_distance = atr_value * setup_atr_mult
    qty = min(risk_usdc / stop_distance, PAPER_BALANCE / market_price)
    if qty <= 0:
        return

    if side == "LONG":
        entry = market_price * (1 + SLIPPAGE_RATE)
        stop_loss = entry - stop_distance
        take_profit = entry + stop_distance * setup_rr
    else:
        entry = market_price * (1 - SLIPPAGE_RATE)
        stop_loss = entry + stop_distance
        take_profit = entry - stop_distance * setup_rr

    paper_position = {
        "symbol": symbol, "side": side, "setup": setup, "score": score,
        "entry_price": entry, "qty": qty,
        "stop_loss": stop_loss, "take_profit": take_profit,
        "risk_distance": stop_distance, "breakeven_moved": False,
        "opened_at": datetime.now(timezone.utc).isoformat(),
    }
    last_entry_candle[symbol] = candle_time
    save_state()
    print("V7 OPEN", symbol, side, setup, score, entry)


def close_trade(market_price, reason):
    global PAPER_BALANCE, paper_position, cooldown_until, trade_history
    if not paper_position:
        return
    p = paper_position
    symbol = p.get("symbol", "XRPUSDT")
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
        "symbol": symbol, "side": side, "setup": p.get("setup"),
        "score": int(p.get("score", 0)), "entry_price": entry,
        "exit_price": exit_price, "qty": qty, "gross_pnl": gross_pnl,
        "fees": fees, "pnl": net_pnl, "reason": reason,
        "opened_at": p["opened_at"], "closed_at": closed_at.isoformat(),
    }
    save_trade(trade)
    trade_history.insert(0, trade)
    trade_history = trade_history[:300]

    _, streak, _, _ = daily_risk_status()
    cooldown_minutes = COOLDOWN_AFTER_LOSS_MIN if net_pnl < 0 else COOLDOWN_AFTER_WIN_MIN
    if net_pnl < 0 and streak >= MAX_CONSECUTIVE_LOSSES:
        cooldown_minutes = max(cooldown_minutes, LOSS_STREAK_COOLDOWN_MIN)
    cooldown_until = closed_at + timedelta(minutes=cooldown_minutes)
    paper_position = None
    save_state()
    print("V7 CLOSE", symbol, reason, net_pnl)


async def manage_position():
    global paper_position
    if not paper_position:
        return
    p = paper_position
    symbol = p.get("symbol", "XRPUSDT")
    price = await get_live_price(symbol)
    side = p["side"]
    entry = float(p["entry_price"])
    stop_loss = float(p["stop_loss"])
    take_profit = float(p["take_profit"])
    risk_distance = float(p.get("risk_distance", abs(entry - stop_loss)))

    if not p.get("breakeven_moved"):
        if side == "LONG" and price >= entry + risk_distance:
            p["stop_loss"] = entry * (1 + 2 * FEE_RATE + SLIPPAGE_RATE)
            p["breakeven_moved"] = True
            save_state()
            stop_loss = float(p["stop_loss"])
        elif side == "SHORT" and price <= entry - risk_distance:
            p["stop_loss"] = entry * (1 - 2 * FEE_RATE - SLIPPAGE_RATE)
            p["breakeven_moved"] = True
            save_state()
            stop_loss = float(p["stop_loss"])

    if side == "LONG":
        if price <= stop_loss:
            close_trade(price, "BREAK EVEN" if p.get("breakeven_moved") else "STOP LOSS")
            return
        if price >= take_profit:
            close_trade(price, "TAKE PROFIT")
            return
    else:
        if price >= stop_loss:
            close_trade(price, "BREAK EVEN" if p.get("breakeven_moved") else "STOP LOSS")
            return
        if price <= take_profit:
            close_trade(price, "TAKE PROFIT")
            return

    opened_at = datetime.fromisoformat(p["opened_at"])
    age_minutes = (datetime.now(timezone.utc) - opened_at).total_seconds() / 60
    if age_minutes >= MAX_TRADE_MINUTES:
        close_trade(price, "TIME EXIT")


async def analyze_all_symbols():
    results = await asyncio.gather(
        *(strategy_analysis(symbol) for symbol in SYMBOLS),
        return_exceptions=True,
    )
    analyses = []
    for symbol, result in zip(SYMBOLS, results):
        if isinstance(result, Exception):
            print("V7 ANALYSIS ERROR", symbol, result)
            analyses.append({
                "symbol": symbol, "signal": "ERROR", "setup": None, "score": 0,
                "reason": str(result), "long_score": 0, "short_score": 0,
                "regime": "ERROR", "rsi": None, "macd": None, "atr": None,
                "adx5": None, "ema9": None, "ema21": None, "ema20_5m": None,
                "ema50_5m": None, "vwap": None, "volume_ratio": None,
                "book_imbalance": None, "candle_time": None,
            })
        else:
            analyses.append(result)
    return analyses


def choose_best_signal(analyses):
    candidates = []
    for a in analyses:
        if a.get("signal") not in ("LONG", "SHORT"):
            continue
        symbol = a["symbol"]
        if last_entry_candle.get(symbol) == a.get("candle_time"):
            continue
        # Higher score first, then stronger ADX, then stronger volume.
        rank = (
            int(a.get("score") or 0),
            float(a.get("adx5") or 0),
            float(a.get("volume_ratio") or 0),
        )
        candidates.append((rank, a))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


async def trading_cycle():
    try:
        await manage_position()
        if paper_position is not None:
            return

        now = datetime.now(timezone.utc)
        if cooldown_until and now < cooldown_until:
            return

        _, streak, daily_blocked, _ = daily_risk_status()
        if daily_blocked or streak >= MAX_CONSECUTIVE_LOSSES:
            return

        analyses = await analyze_all_symbols()
        best = choose_best_signal(analyses)
        if not best:
            return

        live_price = await get_live_price(best["symbol"])
        open_trade(
            best["symbol"], best["signal"], best["setup"], best["score"],
            live_price, best["atr"], best["candle_time"],
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
        print("V7 PRO MULTI SCALPER STARTED", SYMBOLS)


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

    by_symbol = {}
    for symbol in SYMBOLS:
        rows = [t for t in trade_history if t.get("symbol") == symbol]
        n = len(rows)
        sw = sum(1 for t in rows if float(t["pnl"]) > 0)
        by_symbol[symbol] = {
            "count": n,
            "wins": sw,
            "win_rate": sw / n * 100 if n else 0,
            "pnl": sum(float(t["pnl"]) for t in rows),
            "fees": sum(float(t["fees"]) for t in rows),
        }

    day_pnl, streak, daily_blocked, daily_limit = daily_risk_status()
    return {
        "count": count, "wins": wins, "losses": losses, "win_rate": win_rate,
        "total_pnl": total_pnl, "total_fees": total_fees,
        "average_pnl": average_pnl, "max_drawdown": max_drawdown,
        "day_pnl": day_pnl, "loss_streak": streak,
        "daily_blocked": daily_blocked, "daily_limit": daily_limit,
        "by_symbol": by_symbol,
    }


@app.get("/analyze")
async def analyze():
    analyses = await analyze_all_symbols()
    prices_results = await asyncio.gather(
        *(get_live_price(symbol) for symbol in SYMBOLS),
        return_exceptions=True,
    )
    prices = {
        symbol: (None if isinstance(price, Exception) else price)
        for symbol, price in zip(SYMBOLS, prices_results)
    }

    stats = calculate_stats()
    now = datetime.now(timezone.utc)
    cooldown_text = "NE"
    if cooldown_until and now < cooldown_until:
        cooldown_text = f"{(cooldown_until - now).total_seconds() / 60:.1f} min"

    position = dict(paper_position) if paper_position else None
    unrealized_pnl = 0.0
    if position:
        symbol = position.get("symbol", "XRPUSDT")
        live_price = prices.get(symbol)
        if live_price is None:
            try:
                live_price = await get_live_price(symbol)
            except Exception:
                live_price = None
        if live_price is not None:
            entry = float(position["entry_price"])
            qty = float(position["qty"])
            unrealized_pnl = (
                (live_price - entry) * qty
                if position["side"] == "LONG"
                else (entry - live_price) * qty
            )

    best = choose_best_signal(analyses)
    return {
        "bot": "V7 PRO MULTI SCALPER", "mode": TRADING_MODE,
        "symbols": SYMBOLS, "prices": prices, "analyses": analyses,
        "best_signal": best,
        "cooldown": cooldown_text, "paper_balance": PAPER_BALANCE,
        "equity": PAPER_BALANCE + unrealized_pnl,
        "unrealized_pnl": unrealized_pnl,
        "position": position, "stats": stats,
        "trade_history": trade_history[:40],
    }


@app.get("/health")
async def health():
    return {
        "status": "ok", "bot": "V7 PRO MULTI SCALPER",
        "mode": TRADING_MODE, "symbols": SYMBOLS,
    }


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
<!DOCTYPE html>
<html lang="cs">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>V7 Pro Multi Scalper</title>
<style>
body{background:#0b1118;color:white;font-family:Arial,sans-serif;margin:0;padding:16px}
.container{max-width:900px;margin:auto}.card{background:#151c24;border-radius:22px;padding:22px;margin-bottom:18px}
.row{display:flex;justify-content:space-between;gap:15px;margin:11px 0}.green{color:#5ee08a}.red{color:#ff6b6b}.yellow{color:#ffd166}
.small{font-size:14px;opacity:.75}.trade{padding:12px 0;border-bottom:1px solid #29313b}.market{border-top:1px solid #29313b;padding-top:10px;margin-top:10px}
.symbol{font-weight:700;font-size:20px}.muted{opacity:.72}
</style>
</head>
<body><div class="container">
<div class="card"><h1>⚡ V7 PRO MULTI SCALPER</h1>
<div class="row"><span>Režim</span><span>PAPER</span></div>
<div class="row"><span>Trhy</span><span>XRP/USDC · ETH/USDC · SOL/USDC</span></div>
<div class="row"><span>Cooldown</span><span id="cooldown">---</span></div>
<div class="row"><span>Nejlepší signál</span><span id="best">---</span></div>
</div>

<div class="card"><h2>🧠 Trhy a signály</h2><div id="markets">Načítám...</div></div>

<div class="card"><h2>📋 Otevřený PAPER obchod</h2><div id="position">Zatím žádný otevřený obchod</div></div>

<div class="card"><h2>💰 Účet</h2>
<div class="row"><span>Balance</span><span id="bal">---</span></div>
<div class="row"><span>Equity</span><span id="eq">---</span></div>
<div class="row"><span>Otevřený P&L</span><span id="upnl">---</span></div>
</div>

<div class="card"><h2>📊 Celkové statistiky</h2>
<div class="row"><span>Obchody</span><span id="count">---</span></div>
<div class="row"><span>Win rate</span><span id="wr">---</span></div>
<div class="row"><span>Čistý P&L</span><span id="pnl">---</span></div>
<div class="row"><span>Poplatky</span><span id="fees">---</span></div>
<div class="row"><span>Dnešní P&L</span><span id="daypnl">---</span></div>
<div class="row"><span>Série ztrát</span><span id="streak">---</span></div>
<div class="row"><span>Max drawdown</span><span id="dd">---</span></div>
</div>

<div class="card"><h2>🏁 Výsledky podle trhu</h2><div id="bysymbol">---</div></div>
<div class="card"><h2>📜 Poslední obchody</h2><div id="history">Zatím žádné uzavřené obchody</div></div>
</div>

<script>
const n=(v,d=4)=>Number.isFinite(Number(v))?Number(v).toFixed(d):'---';
const cls=v=>Number(v)>0?'green':Number(v)<0?'red':'yellow';
const pretty=s=>String(s||'').replace('USDC','/USDC').replace('USDT','/USDT');

async function refresh(){
try{
 const d=await (await fetch('/analyze',{cache:'no-store'})).json();
 document.getElementById('cooldown').innerText=d.cooldown??'---';
 const b=d.best_signal;
 document.getElementById('best').innerText=b?`${pretty(b.symbol)} · ${b.signal} · ${b.setup} · ${b.score}/8`:'WAIT';

 const prices=d.prices||{};
 const aa=d.analyses||[];
 document.getElementById('markets').innerHTML=aa.map(a=>{
   const sig=a.signal||'WAIT'; const c=sig==='LONG'?'green':sig==='SHORT'?'red':'yellow';
   return `<div class="market"><div class="row"><span class="symbol">${pretty(a.symbol)}</span><span>${n(prices[a.symbol],a.symbol.startsWith('XRP')?5:2)} USDC</span></div>
   <div class="row"><span>Signál</span><span class="${c}">${sig}</span></div>
   <div class="row"><span>Setup</span><span>${a.setup??'---'}</span></div>
   <div class="row"><span>Regime</span><span>${a.regime??'---'}</span></div>
   <div class="row"><span>LONG / SHORT score</span><span>${a.long_score??0}/8 · ${a.short_score??0}/8</span></div>
   <div class="row"><span>RSI · ADX5</span><span>${n(a.rsi,1)} · ${n(a.adx5,1)}</span></div>
   <div class="row"><span>Volume · Book bids</span><span>${n(a.volume_ratio,2)}× · ${n((a.book_imbalance??0)*100,1)}%</span></div>
   <div class="small">${a.reason??''}</div></div>`;
 }).join('');

 document.getElementById('bal').innerText=n(d.paper_balance,2)+' USDC';
 document.getElementById('eq').innerText=n(d.equity,2)+' USDC';
 const u=document.getElementById('upnl');u.innerText=n(d.unrealized_pnl,2)+' USDC';u.className=cls(d.unrealized_pnl);

 if(d.position){const p=d.position;document.getElementById('position').innerHTML=`
 <div class="row"><span>Trh</span><span>${pretty(p.symbol)}</span></div>
 <div class="row"><span>Směr</span><span>${p.side}</span></div>
 <div class="row"><span>Setup</span><span>${p.setup}</span></div>
 <div class="row"><span>Score</span><span>${p.score}/8</span></div>
 <div class="row"><span>Entry</span><span>${n(p.entry_price,6)}</span></div>
 <div class="row"><span>SL</span><span>${n(p.stop_loss,6)}</span></div>
 <div class="row"><span>TP</span><span>${n(p.take_profit,6)}</span></div>`}
 else document.getElementById('position').innerText='Zatím žádný otevřený obchod';

 const s=d.stats||{};
 document.getElementById('count').innerText=s.count??0;
 document.getElementById('wr').innerText=n(s.win_rate,1)+' %';
 const pe=document.getElementById('pnl');pe.innerText=n(s.total_pnl,2)+' USDC';pe.className=cls(s.total_pnl);
 document.getElementById('fees').innerText=n(s.total_fees,2)+' USDC';
 const dp=document.getElementById('daypnl');dp.innerText=n(s.day_pnl,2)+' USDC';dp.className=cls(s.day_pnl);
 document.getElementById('streak').innerText=s.loss_streak??0;
 document.getElementById('dd').innerText=n(s.max_drawdown,2)+' %';

 const bs=s.by_symbol||{};
 document.getElementById('bysymbol').innerHTML=(d.symbols||[]).map(sym=>{const x=bs[sym]||{};return `<div class="trade"><div class="row"><span>${pretty(sym)}</span><span class="${cls(x.pnl)}">${n(x.pnl,2)} USDC</span></div><div class="small">Obchody ${x.count??0} · Win rate ${n(x.win_rate,1)} % · Poplatky ${n(x.fees,2)} USDC</div></div>`}).join('');

 const h=d.trade_history||[];
 document.getElementById('history').innerHTML=h.length?h.map(t=>`<div class="trade"><div class="row"><span>${pretty(t.symbol)} · ${t.side} · ${t.setup} · ${t.score}/8</span><span class="${cls(t.pnl)}">${n(t.pnl,2)} USDC</span></div><div class="small">${t.reason} · ${n(t.entry_price,6)} → ${n(t.exit_price,6)} · fee ${n(t.fees,2)}</div></div>`).join(''):'Zatím žádné uzavřené obchody';
}catch(e){document.getElementById('best').innerText='Chyba načítání: '+e}
}
refresh();setInterval(refresh,5000);
</script>
</body></html>
"""
