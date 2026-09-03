import os
import json
import asyncio
from datetime import datetime, timezone, timedelta

import psycopg
import httpx
from fastapi import FastAPI
from fastapi.responses import HTMLResponse


# ============================================================
# XRP BOT V6 SCALPER
# PAPER ONLY
# ============================================================

app = FastAPI(title="XRP Bot V6 Scalper")

SYMBOL = "XRPUSDT"
BINANCE_API = "https://data-api.binance.vision"
TRADING_MODE = "PAPER"

DATABASE_URL = os.getenv("DATABASE_URL")

STARTING_BALANCE = 10000.0

# ============================================================
# MONEY MANAGEMENT
# ============================================================

RISK_PER_TRADE = 0.0025          # 0.25 % účtu
RISK_REWARD = 1.30               # TP = 1.30 R
ATR_MULTIPLIER = 1.00            # SL = 1 × ATR

# Simulované obchodní náklady
FEE_RATE = 0.0005                # 0.05 % za stranu
SLIPPAGE_RATE = 0.0002           # 0.02 %

# ============================================================
# SCALPING STRATEGIE
# ============================================================

MIN_VOLUME_RATIO = 1.05

RSI_LONG_MIN = 50
RSI_LONG_MAX = 69

RSI_SHORT_MIN = 31
RSI_SHORT_MAX = 50

COOLDOWN_AFTER_WIN_MIN = 1
COOLDOWN_AFTER_LOSS_MIN = 4

MAX_TRADE_MINUTES = 10

LOOP_SECONDS = 10

# ============================================================
# GLOBAL STATE
# ============================================================

PAPER_BALANCE = STARTING_BALANCE
paper_position = None
trade_history = []

last_entry_candle = None
cooldown_until = None

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
        print("DATABASE_URL není nastaveno.")
        return

    with get_db() as conn:
        with conn.cursor() as cur:

            cur.execute("""
                CREATE TABLE IF NOT EXISTS v6_trades (
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
                    opened_at TIMESTAMPTZ,
                    closed_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS v6_state (
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
        "cooldown_until": (
            cooldown_until.isoformat()
            if cooldown_until
            else None
        )
    }

    try:
        with get_db() as conn:
            with conn.cursor() as cur:

                cur.execute("""
                    INSERT INTO v6_state (id, state)
                    VALUES (1, %s::jsonb)
                    ON CONFLICT (id)
                    DO UPDATE SET state = EXCLUDED.state
                """, (json.dumps(state),))

            conn.commit()

    except Exception as e:
        print("SAVE STATE ERROR:", e)


def load_state():
    global PAPER_BALANCE
    global paper_position
    global last_entry_candle
    global cooldown_until
    global trade_history

    if not DATABASE_URL:
        return

    try:
        with get_db() as conn:
            with conn.cursor() as cur:

                cur.execute("""
                    SELECT state
                    FROM v6_state
                    WHERE id = 1
                """)

                row = cur.fetchone()

                if row:
                    state = row[0]

                    PAPER_BALANCE = float(
                        state.get(
                            "paper_balance",
                            STARTING_BALANCE
                        )
                    )

                    paper_position = state.get(
                        "paper_position"
                    )

                    last_entry_candle = state.get(
                        "last_entry_candle"
                    )

                    cooldown = state.get(
                        "cooldown_until"
                    )

                    if cooldown:
                        cooldown_until = (
                            datetime.fromisoformat(
                                cooldown
                            )
                        )

                cur.execute("""
                    SELECT
                        side,
                        setup,
                        entry_price,
                        exit_price,
                        qty,
                        gross_pnl,
                        fees,
                        pnl,
                        reason,
                        opened_at,
                        closed_at
                    FROM v6_trades
                    ORDER BY id DESC
                    LIMIT 200
                """)

                rows = cur.fetchall()

                trade_history = []

                for row in rows:
                    trade_history.append({
                        "side": row[0],
                        "setup": row[1],
                        "entry_price": row[2],
                        "exit_price": row[3],
                        "qty": row[4],
                        "gross_pnl": row[5],
                        "fees": row[6],
                        "pnl": row[7],
                        "reason": row[8],
                        "opened_at": (
                            row[9].isoformat()
                            if row[9]
                            else None
                        ),
                        "closed_at": (
                            row[10].isoformat()
                            if row[10]
                            else None
                        )
                    })

    except Exception as e:
        print("LOAD STATE ERROR:", e)


def save_trade(trade):

    if not DATABASE_URL:
        return

    try:
        with get_db() as conn:
            with conn.cursor() as cur:

                cur.execute("""
                    INSERT INTO v6_trades (
                        side,
                        setup,
                        entry_price,
                        exit_price,
                        qty,
                        gross_pnl,
                        fees,
                        pnl,
                        reason,
                        opened_at,
                        closed_at
                    )
                    VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s
                    )
                """, (
                    trade["side"],
                    trade["setup"],
                    trade["entry_price"],
                    trade["exit_price"],
                    trade["qty"],
                    trade["gross_pnl"],
                    trade["fees"],
                    trade["pnl"],
                    trade["reason"],
                    trade["opened_at"],
                    trade["closed_at"]
                ))

            conn.commit()

    except Exception as e:
        print("SAVE TRADE ERROR:", e)


# ============================================================
# INDICATORS
# ============================================================

def ema(values, period):

    if len(values) < period:
        return None

    multiplier = 2 / (period + 1)

    value = sum(values[:period]) / period

    for price in values[period:]:
        value = (
            price * multiplier
            + value * (1 - multiplier)
        )

    return value


def ema_series(values, period):

    if len(values) < period:
        return []

    multiplier = 2 / (period + 1)

    result = [None] * (period - 1)

    current = sum(values[:period]) / period

    result.append(current)

    for price in values[period:]:

        current = (
            price * multiplier
            + current * (1 - multiplier)
        )

        result.append(current)

    return result


def rsi(values, period=14):

    if len(values) < period + 1:
        return None

    gains = []
    losses = []

    for i in range(
        len(values) - period,
        len(values)
    ):

        change = values[i] - values[i - 1]

        gains.append(
            max(change, 0)
        )

        losses.append(
            max(-change, 0)
        )

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss

    return 100 - (
        100 / (1 + rs)
    )


def atr(highs, lows, closes, period=14):

    if len(closes) < period + 1:
        return None

    true_ranges = []

    start = len(closes) - period

    for i in range(start, len(closes)):

        previous_close = closes[i - 1]

        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - previous_close),
            abs(lows[i] - previous_close)
        )

        true_ranges.append(tr)

    return sum(true_ranges) / period


def macd_histogram(values):

    if len(values) < 40:
        return None

    ema12 = ema_series(values, 12)
    ema26 = ema_series(values, 26)

    macd_values = []

    for i in range(len(values)):

        if (
            i < len(ema12)
            and i < len(ema26)
            and ema12[i] is not None
            and ema26[i] is not None
        ):
            macd_values.append(
                ema12[i] - ema26[i]
            )

    if len(macd_values) < 9:
        return None

    signal = ema(
        macd_values,
        9
    )

    return (
        macd_values[-1]
        - signal
    )


# ============================================================
# BINANCE DATA
# ============================================================

async def get_klines(interval, limit=250):

    url = (
        f"{BINANCE_API}/api/v3/klines"
        f"?symbol={SYMBOL}"
        f"&interval={interval}"
        f"&limit={limit}"
    )

    async with httpx.AsyncClient(
        timeout=10
    ) as client:

        response = await client.get(url)
        response.raise_for_status()

        return response.json()


async def get_live_price():

    url = (
        f"{BINANCE_API}/api/v3/ticker/price"
        f"?symbol={SYMBOL}"
    )

    async with httpx.AsyncClient(
        timeout=10
    ) as client:

        response = await client.get(url)
        response.raise_for_status()

        data = response.json()

        return float(
            data["price"]
        )


# ============================================================
# STRATEGY ANALYSIS
# ============================================================

async def strategy_analysis():

    klines_1m = await get_klines(
        "1m",
        250
    )

    klines_5m = await get_klines(
        "5m",
        250
    )

    # poslední UZAVŘENÁ 1m svíčka
    closed_1m = klines_1m[:-1]

    closes_1m = [
        float(x[4])
        for x in closed_1m
    ]

    opens_1m = [
        float(x[1])
        for x in closed_1m
    ]

    highs_1m = [
        float(x[2])
        for x in closed_1m
    ]

    lows_1m = [
        float(x[3])
        for x in closed_1m
    ]

    volumes_1m = [
        float(x[5])
        for x in closed_1m
    ]

    candle_time = int(
        closed_1m[-1][0]
    )

    # 5m
    closed_5m = klines_5m[:-1]

    closes_5m = [
        float(x[4])
        for x in closed_5m
    ]

    # ---------------------------
    # 1m indicators
    # ---------------------------

    ema9 = ema(
        closes_1m,
        9
    )

    ema21 = ema(
        closes_1m,
        21
    )

    rsi_value = rsi(
        closes_1m,
        14
    )

    atr_value = atr(
        highs_1m,
        lows_1m,
        closes_1m,
        14
    )

    macd_value = macd_histogram(
        closes_1m
    )

    # ---------------------------
    # 5m trend
    # ---------------------------

    ema20_5m = ema(
        closes_5m,
        20
    )

    ema50_5m = ema(
        closes_5m,
        50
    )

    close_5m = closes_5m[-1]

    if (
        close_5m > ema20_5m
        and ema20_5m > ema50_5m
    ):
        trend_5m = "LONG"

    elif (
        close_5m < ema20_5m
        and ema20_5m < ema50_5m
    ):
        trend_5m = "SHORT"

    else:
        trend_5m = "NEUTRAL"

    # ---------------------------
    # VOLUME
    # ---------------------------

    previous_volumes = volumes_1m[-21:-1]

    average_volume = (
        sum(previous_volumes)
        / len(previous_volumes)
    )

    current_volume = volumes_1m[-1]

    volume_ratio = (
        current_volume
        / average_volume
        if average_volume > 0
        else 0
    )

    # ---------------------------
    # Current candle
    # ---------------------------

    current_open = opens_1m[-1]
    current_close = closes_1m[-1]
    current_high = highs_1m[-1]
    current_low = lows_1m[-1]

    previous_close = closes_1m[-2]

    bullish_candle = (
        current_close > current_open
    )

    bearish_candle = (
        current_close < current_open
    )

    # ---------------------------
    # ENTRY SETUPS
    # ---------------------------

    long_momentum = (
        trend_5m == "LONG"
        and ema9 > ema21
        and current_close > ema9
        and bullish_candle
        and RSI_LONG_MIN
        <= rsi_value
        <= RSI_LONG_MAX
        and macd_value > 0
        and volume_ratio
        >= MIN_VOLUME_RATIO
    )

    short_momentum = (
        trend_5m == "SHORT"
        and ema9 < ema21
        and current_close < ema9
        and bearish_candle
        and RSI_SHORT_MIN
        <= rsi_value
        <= RSI_SHORT_MAX
        and macd_value < 0
        and volume_ratio
        >= MIN_VOLUME_RATIO
    )

    # Pullback k EMA9
    long_pullback = (
        trend_5m == "LONG"
        and ema9 > ema21
        and current_low
        <= ema9 * 1.001
        and current_close > ema9
        and bullish_candle
        and 45 <= rsi_value <= 67
        and macd_value > 0
    )

    short_pullback = (
        trend_5m == "SHORT"
        and ema9 < ema21
        and current_high
        >= ema9 * 0.999
        and current_close < ema9
        and bearish_candle
        and 33 <= rsi_value <= 55
        and macd_value < 0
    )

    signal = "WAIT"
    setup = None

    if long_pullback:
        signal = "LONG"
        setup = "PULLBACK"

    elif short_pullback:
        signal = "SHORT"
        setup = "PULLBACK"

    elif long_momentum:
        signal = "LONG"
        setup = "MOMENTUM"

    elif short_momentum:
        signal = "SHORT"
        setup = "MOMENTUM"

    reasons = []

    if trend_5m == "NEUTRAL":
        reasons.append(
            "5m trend NEUTRAL"
        )

    if volume_ratio < MIN_VOLUME_RATIO:
        reasons.append(
            "slabší volume"
        )

    if signal == "WAIT":
        reasons.append(
            "bez vstupního setupu"
        )

    return {
        "signal": signal,
        "setup": setup,
        "candle_time": candle_time,

        "trend_5m": trend_5m,

        "price_closed": current_close,

        "ema9": ema9,
        "ema21": ema21,

        "ema20_5m": ema20_5m,
        "ema50_5m": ema50_5m,

        "rsi": rsi_value,
        "macd": macd_value,
        "atr": atr_value,

        "volume_ratio": volume_ratio,

        "reason": ", ".join(reasons)
        if reasons
        else "Podmínky splněny"
    }


# ============================================================
# OPEN TRADE
# ============================================================

def open_trade(
    side,
    setup,
    market_price,
    atr_value,
    candle_time
):

    global paper_position
    global last_entry_candle

    if paper_position is not None:
        return

    if atr_value is None:
        return

    risk_usdt = (
        PAPER_BALANCE
        * RISK_PER_TRADE
    )

    stop_distance = (
        atr_value
        * ATR_MULTIPLIER
    )

    if stop_distance <= 0:
        return

    qty = (
        risk_usdt
        / stop_distance
    )

    # Bez páky
    max_qty = (
        PAPER_BALANCE
        / market_price
    )

    qty = min(
        qty,
        max_qty
    )

    if qty <= 0:
        return

    if side == "LONG":

        entry_price = (
            market_price
            * (1 + SLIPPAGE_RATE)
        )

        stop_loss = (
            entry_price
            - stop_distance
        )

        take_profit = (
            entry_price
            + stop_distance
            * RISK_REWARD
        )

    else:

        entry_price = (
            market_price
            * (1 - SLIPPAGE_RATE)
        )

        stop_loss = (
            entry_price
            + stop_distance
        )

        take_profit = (
            entry_price
            - stop_distance
            * RISK_REWARD
        )

    paper_position = {
        "side": side,
        "setup": setup,
        "entry_price": entry_price,
        "qty": qty,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "opened_at": (
            datetime.now(
                timezone.utc
            ).isoformat()
        )
    }

    last_entry_candle = candle_time

    save_state()

    print(
        "OPEN",
        side,
        setup,
        entry_price
    )


# ============================================================
# CLOSE TRADE
# ============================================================

def close_trade(
    market_price,
    reason
):

    global PAPER_BALANCE
    global paper_position
    global cooldown_until
    global trade_history

    if not paper_position:
        return

    side = paper_position["side"]

    entry_price = float(
        paper_position["entry_price"]
    )

    qty = float(
        paper_position["qty"]
    )

    if side == "LONG":

        exit_price = (
            market_price
            * (1 - SLIPPAGE_RATE)
        )

        gross_pnl = (
            exit_price
            - entry_price
        ) * qty

    else:

        exit_price = (
            market_price
            * (1 + SLIPPAGE_RATE)
        )

        gross_pnl = (
            entry_price
            - exit_price
        ) * qty

    entry_fee = (
        entry_price
        * qty
        * FEE_RATE
    )

    exit_fee = (
        exit_price
        * qty
        * FEE_RATE
    )

    fees = (
        entry_fee
        + exit_fee
    )

    net_pnl = (
        gross_pnl
        - fees
    )

    PAPER_BALANCE += net_pnl

    opened_at = (
        paper_position[
            "opened_at"
        ]
    )

    closed_at = (
        datetime.now(
            timezone.utc
        )
    )

    trade = {
        "side": side,
        "setup": paper_position[
            "setup"
        ],
        "entry_price": entry_price,
        "exit_price": exit_price,
        "qty": qty,
        "gross_pnl": gross_pnl,
        "fees": fees,
        "pnl": net_pnl,
        "reason": reason,
        "opened_at": opened_at,
        "closed_at": (
            closed_at.isoformat()
        )
    }

    save_trade(trade)

    trade_history.insert(
        0,
        trade
    )

    if len(trade_history) > 200:
        trade_history = (
            trade_history[:200]
        )

    if net_pnl < 0:

        cooldown_until = (
            closed_at
            + timedelta(
                minutes=
                COOLDOWN_AFTER_LOSS_MIN
            )
        )

    else:

        cooldown_until = (
            closed_at
            + timedelta(
                minutes=
                COOLDOWN_AFTER_WIN_MIN
            )
        )

    paper_position = None

    save_state()

    print(
        "CLOSE",
        reason,
        net_pnl
    )


# ============================================================
# POSITION MANAGEMENT
# ============================================================

async def manage_position():

    if not paper_position:
        return

    price = await get_live_price()

    side = paper_position["side"]

    stop_loss = float(
        paper_position["stop_loss"]
    )

    take_profit = float(
        paper_position["take_profit"]
    )

    opened_at = datetime.fromisoformat(
        paper_position["opened_at"]
    )

    now = datetime.now(
        timezone.utc
    )

    age = (
        now - opened_at
    ).total_seconds() / 60

    if side == "LONG":

        if price <= stop_loss:
            close_trade(
                price,
                "STOP LOSS"
            )
            return

        if price >= take_profit:
            close_trade(
                price,
                "TAKE PROFIT"
            )
            return

    else:

        if price >= stop_loss:
            close_trade(
                price,
                "STOP LOSS"
            )
            return

        if price <= take_profit:
            close_trade(
                price,
                "TAKE PROFIT"
            )
            return

    if age >= MAX_TRADE_MINUTES:

        close_trade(
            price,
            "TIME EXIT"
        )


# ============================================================
# BOT CYCLE
# ============================================================

async def trading_cycle():

    global last_entry_candle

    try:

        await manage_position()

        analysis = (
            await strategy_analysis()
        )

        if paper_position is not None:
            return

        now = datetime.now(
            timezone.utc
        )

        if (
            cooldown_until
            and now < cooldown_until
        ):
            return

        candle_time = analysis[
            "candle_time"
        ]

        # maximálně jeden nový vstup
        # na jednu uzavřenou 1m svíčku
        if (
            last_entry_candle
            == candle_time
        ):
            return

        signal = analysis[
            "signal"
        ]

        if signal not in (
            "LONG",
            "SHORT"
        ):
            return

        live_price = (
            await get_live_price()
        )

        open_trade(
            side=signal,
            setup=analysis[
                "setup"
            ],
            market_price=live_price,
            atr_value=analysis[
                "atr"
            ],
            candle_time=candle_time
        )

    except Exception as e:
        print(
            "TRADING CYCLE ERROR:",
            e
        )


async def bot_loop():

    while True:

        await trading_cycle()

        await asyncio.sleep(
            LOOP_SECONDS
        )


# ============================================================
# STARTUP
# ============================================================

@app.on_event("startup")
async def startup_event():

    global bot_loop_started

    init_db()
    load_state()

    if not bot_loop_started:

        bot_loop_started = True

        asyncio.create_task(
            bot_loop()
        )

        print(
            "XRP BOT V6 SCALPER STARTED"
        )


# ============================================================
# STATISTICS
# ============================================================

def calculate_stats():

    trades = trade_history

    count = len(trades)

    wins = len([
        t for t in trades
        if t["pnl"] > 0
    ])

    losses = len([
        t for t in trades
        if t["pnl"] <= 0
    ])

    win_rate = (
        wins / count * 100
        if count > 0
        else 0
    )

    total_pnl = sum(
        float(t["pnl"])
        for t in trades
    )

    total_fees = sum(
        float(t["fees"])
        for t in trades
    )

    average_pnl = (
        total_pnl / count
        if count
        else 0
    )

    # Max drawdown z realizovaných obchodů
    equity = STARTING_BALANCE
    peak = equity
    max_drawdown = 0

    for trade in reversed(trades):

        equity += float(
            trade["pnl"]
        )

        if equity > peak:
            peak = equity

        drawdown = (
            peak - equity
        )

        if peak > 0:

            drawdown_pct = (
                drawdown
                / peak
                * 100
            )

            max_drawdown = max(
                max_drawdown,
                drawdown_pct
            )

    return {
        "count": count,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "total_pnl": total_pnl,
        "total_fees": total_fees,
        "average_pnl": average_pnl,
        "max_drawdown": max_drawdown
    }


# ============================================================
# API
# ============================================================

@app.get("/analyze")
async def analyze():

    analysis = (
        await strategy_analysis()
    )

    live_price = (
        await get_live_price()
    )

    stats = (
        calculate_stats()
    )

    now = datetime.now(
        timezone.utc
    )

    cooldown_text = "NE"

    if (
        cooldown_until
        and now < cooldown_until
    ):

        seconds = (
            cooldown_until
            - now
        ).total_seconds()

        cooldown_text = (
            f"{seconds / 60:.1f} min"
        )

    position = None

    unrealized_pnl = 0

    if paper_position:

        position = dict(
            paper_position
        )

        side = position[
            "side"
        ]

        entry = float(
            position[
                "entry_price"
            ]
        )

        qty = float(
            position[
                "qty"
            ]
        )

        if side == "LONG":

            unrealized_pnl = (
                live_price
                - entry
            ) * qty

        else:

            unrealized_pnl = (
                entry
                - live_price
            ) * qty

    equity = (
        PAPER_BALANCE
        + unrealized_pnl
    )

    return {
        "bot": "XRP BOT V6 SCALPER",
        "mode": TRADING_MODE,

        "price": live_price,

        "signal": analysis[
            "signal"
        ],

        "setup": analysis[
            "setup"
        ],

        "trend_5m": analysis[
            "trend_5m"
        ],

        "rsi": analysis[
            "rsi"
        ],

        "macd": analysis[
            "macd"
        ],

        "atr": analysis[
            "atr"
        ],

        "ema9_1m": analysis[
            "ema9"
        ],

        "ema21_1m": analysis[
            "ema21"
        ],

        "ema20_5m": analysis[
            "ema20_5m"
        ],

        "ema50_5m": analysis[
            "ema50_5m"
        ],

        "volume_ratio": analysis[
            "volume_ratio"
        ],

        "reason": analysis[
            "reason"
        ],

        "cooldown": cooldown_text,

        "paper_balance": PAPER_BALANCE,

        "equity": equity,

        "unrealized_pnl":
            unrealized_pnl,

        "position": position,

        "stats": stats,

        "trade_history":
            trade_history[:30]
    }


@app.get("/health")
async def health():

    return {
        "status": "ok",
        "bot": "XRP BOT V6 SCALPER",
        "mode": TRADING_MODE
    }


# ============================================================
# DASHBOARD
# ============================================================

@app.get(
    "/",
    response_class=HTMLResponse
)
async def dashboard():

    return """
<!DOCTYPE html>

<html lang="cs">

<head>

<meta charset="UTF-8">

<meta
name="viewport"
content="width=device-width, initial-scale=1.0"
>

<title>XRP Bot V6 Scalper</title>

<style>

body {
    background: #0b1118;
    color: white;
    font-family: Arial, sans-serif;
    margin: 0;
    padding: 16px;
}

.container {
    max-width: 800px;
    margin: auto;
}

.card {
    background: #151c24;
    border-radius: 22px;
    padding: 22px;
    margin-bottom: 18px;
}

h1 {
    font-size: 26px;
}

h2 {
    font-size: 21px;
}

.row {
    display: flex;
    justify-content: space-between;
    margin: 11px 0;
    gap: 15px;
}

.value {
    text-align: right;
}

.green {
    color: #5ee08a;
}

.red {
    color: #ff6b6b;
}

.yellow {
    color: #ffd166;
}

.small {
    font-size: 14px;
    opacity: 0.75;
}

.trade {
    padding: 12px 0;
    border-bottom:
        1px solid #29313b;
}

</style>

</head>


<body>

<div class="container">

<div class="card">

<h1>⚡ XRP BOT V6 SCALPER</h1>

<div class="row">
<span>Režim</span>
<span class="value">PAPER</span>
</div>

<div class="row">
<span>XRP cena</span>
<span
class="value"
id="price"
>---</span>
</div>

<div class="row">
<span>Signál</span>
<span
class="value"
id="signal"
>---</span>
</div>

<div class="row">
<span>Setup</span>
<span
class="value"
id="setup"
>---</span>
</div>

<div class="row">
<span>5m trend</span>
<span
class="value"
id="trend"
>---</span>
</div>

<div class="row">
<span>Cooldown</span>
<span
class="value"
id="cooldown"
>---</span>
</div>

</div>


<div class="card">

<h2>🧠 Strategie V6</h2>

<div class="row">
<span>RSI 1m</span>
<span
id="rsi"
class="value"
>---</span>
</div>

<div class="row">
<span>MACD histogram</span>
<span
id="macd"
class="value"
>---</span>
</div>

<div class="row">
<span>ATR 1m</span>
<span
id="atr"
class="value"
>---</span>
</div>

<div class="row">
<span>EMA 9 (1m)</span>
<span
id="ema9"
class="value"
>---</span>
</div>

<div class="row">
<span>EMA 21 (1m)</span>
<span
id="ema21"
class="value"
>---</span>
</div>

<div class="row">
<span>EMA 20 (5m)</span>
<span
id="ema20"
class="value"
>---</span>
</div>

<div class="row">
<span>EMA 50 (5m)</span>
<span
id="ema50"
class="value"
>---</span>
</div>

<div class="row">
<span>Volume</span>
<span
id="volume"
class="value"
>---</span>
</div>

<p id="reason">
---
</p>

</div>


<div class="card">

<h2>📋 Otevřený PAPER obchod</h2>

<div id="position">
Zatím žádný otevřený obchod
</div>

</div>


<div class="card">

<h2>💰 Účet</h2>

<div class="row">
<span>Realizovaný balance</span>
<span
id="balance"
class="value"
>---</span>
</div>

<div class="row">
<span>Equity</span>
<span
id="equity"
class="value"
>---</span>
</div>

<div class="row">
<span>Otevřený P&L</span>
<span
id="unrealized"
class="value"
>---</span>
</div>

</div>


<div class="card">

<h2>📊 Statistiky</h2>

<div class="row">
<span>Obchody</span>
<span
id="count"
class="value"
>---</span>
</div>

<div class="row">
<span>WIN</span>
<span
id="wins"
class="value"
>---</span>
</div>

<div class="row">
<span>LOSS</span>
<span
id="losses"
class="value"
>---</span>
</div>

<div class="row">
<span>Win rate</span>
<span
id="winrate"
class="value"
>---</span>
</div>

<div class="row">
<span>Čistý P&L</span>
<span
id="pnl"
class="value"
>---</span>
</div>

<div class="row">
<span>Poplatky</span>
<span
id="fees"
class="value"
>---</span>
</div>

<div class="row">
<span>Průměr / obchod</span>
<span
id="avg"
class="value"
>---</span>
</div>

<div class="row">
<span>Max drawdown</span>
<span
id="drawdown"
class="value"
>---</span>
</div>

</div>


<div class="card">

<h2>📜 Poslední obchody</h2>

<div id="history">
Zatím žádné obchody
</div>

</div>

</div>


<script>

function number(value, decimals = 4) {

    if (
        value === null
        || value === undefined
    ) {
        return "---";
    }

    return Number(value)
        .toFixed(decimals);
}


async function updateDashboard() {

    try {

        const response =
            await fetch("/analyze");

        const data =
            await response.json();


        document.getElementById(
            "price"
        ).innerText =
            number(data.price, 5)
            + " USDT";


        document.getElementById(
            "signal"
        ).innerText =
            data.signal;


        document.getElementById(
            "setup"
        ).innerText =
            data.setup ?? "---";


        document.getElementById(
            "trend"
        ).innerText =
            data.trend_5m;


        document.getElementById(
            "cooldown"
        ).innerText =
            data.cooldown;


        document.getElementById(
            "rsi"
        ).innerText =
            number(data.rsi, 2);


        document.getElementById(
            "macd"
        ).innerText =
            number(data.macd, 6);


        document.getElementById(
            "atr"
        ).innerText =
            number(data.atr, 6);


        document.getElementById(
            "ema9"
        ).innerText =
            number(
                data.ema9_1m,
                6
            );


        document.getElementById(
            "ema21"
        ).innerText =
            number(
                data.ema21_1m,
                6
            );


        document.getElementById(
            "ema20"
        ).innerText =
            number(
                data.ema20_5m,
                6
            );


        document.getElementById(
            "ema50"
        ).innerText =
            number(
                data.ema50_5m,
                6
            );


        document.getElementById(
            "volume"
        ).innerText =
            number(
                data.volume_ratio,
                2
            ) + "×";


        document.getElementById(
            "reason"
        ).innerText =
            "Čeká kvůli: "
            + data.reason;


        document.getElementById(
            "balance"
        ).innerText =
            number(
                data.paper_balance,
                2
            ) + " USDT";


        document.getElementById(
            "equity"
        ).innerText =
            number(
                data.equity,
                2
            ) + " USDT";


        document.getElementById(
            "unrealized"
        ).innerText =
            number(
                data.unrealized_pnl,
                2
            ) + " USDT";


        const stats = data.stats;

        document.getElementById(
            "count"
        ).innerText =
            stats.count;


        document.getElementById(
            "wins"
        ).innerText =
            stats.wins;


        document.getElementById(
            "losses"
        ).innerText =
            stats.losses;


        document.getElementById(
            "winrate"
        ).innerText =
            number(
                stats.win_rate,
                1
            ) + "%";


        document.getElementById(
            "pnl"
        ).innerText =
            number(
                stats.total_pnl,
                2
            ) + " USDT";


        document.getElementById(
            "fees"
        ).innerText =
            number(
                stats.total_fees,
                2
            ) + " USDT";


        document.getElementById(
            "avg"
        ).innerText =
            number(
                stats.average_pnl,
                2
            ) + " USDT";


        document.getElementById(
            "drawdown"
        ).innerText =
            number(
                stats.max_drawdown,
                2
            ) + "%";


        // POSITION
        const positionBox =
            document.getElementById(
                "position"
            );

        if (data.position) {

            const p =
                data.position;

            positionBox.innerHTML = `

                <div class="row">
                    <span>Směr</span>
                    <span>${p.side}</span>
                </div>

                <div class="row">
                    <span>Setup</span>
                    <span>${p.setup}</span>
                </div>

                <div class="row">
                    <span>Entry</span>
                    <span>${number(
                        p.entry_price,
                        5
                    )}</span>
                </div>

                <div class="row">
                    <span>Stop Loss</span>
                    <span>${number(
                        p.stop_loss,
                        5
                    )}</span>
                </div>

                <div class="row">
                    <span>Take Profit</span>
                    <span>${number(
                        p.take_profit,
                        5
                    )}</span>
                </div>

                <div class="row">
                    <span>P&L</span>
                    <span>
                    ${number(
                        data.unrealized_pnl,
                        2
                    )} USDT
                    </span>
                </div>
            `;

        } else {

            positionBox.innerText =
                "Zatím žádný otevřený obchod";
        }


        // HISTORY
        const history =
            document.getElementById(
                "history"
            );

        if (
            !data.trade_history
            || data.trade_history.length === 0
        ) {

            history.innerText =
                "Zatím žádné obchody";

        } else {

            history.innerHTML =
                data.trade_history
                .map(t => `

                <div class="trade">

                    <b>
                    ${t.side}
                    –
                    ${t.setup ?? ""}
                    </b>

                    <br>

                    Entry:
                    ${number(
                        t.entry_price,
                        5
                    )}

                    →

                    Exit:
                    ${number(
                        t.exit_price,
                        5
                    )}

                    <br>

                    Výsledek:
                    <b>
                    ${number(
                        t.pnl,
                        2
                    )} USDT
                    </b>

                    <br>

                    <span class="small">
                    ${t.reason}
                    </span>

                </div>

            `).join("");
        }

    }

    catch(error) {

        console.log(
            error
        );
    }
}


updateDashboard();

setInterval(
    updateDashboard,
    5000
);

</script>

</body>
</html>
"""
