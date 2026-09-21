"""
XRP Lead-Lag Scalper — PAPER ONLY.

Idea:
- BTC + ETH are treated as short-horizon leaders.
- XRP is traded only when both leaders move in the same direction,
  XRP has not yet caught up, and XRP order-book microstructure confirms.
- Exit on lag convergence, leader fade, book flip, hard SL/TP, or time limit.
No live orders are sent.
"""
from __future__ import annotations

import asyncio
import json
import math
import os
import time
from datetime import datetime, timezone, timedelta

import psycopg
from psycopg.types.json import Jsonb

BUILD = "lead-lag-v2-bookflip-confirm-20260921"
MODE = "PAPER"

TRADE_SYMBOL = "XRPUSDC"
BTC_SYMBOL = "BTCUSDT"
ETH_SYMBOL = "ETHUSDT"

START_BALANCE = float(os.getenv("LEADLAG_START_BALANCE", "10000"))
RISK_PER_TRADE = float(os.getenv("LEADLAG_RISK_PER_TRADE", "0.002"))
MAX_NOTIONAL_SHARE = float(os.getenv("LEADLAG_MAX_NOTIONAL_SHARE", "0.35"))

SCAN_SECONDS = int(os.getenv("LEADLAG_SCAN_SECONDS", "12"))
STATE_HEARTBEAT_SECONDS = float(os.getenv("LEADLAG_STATE_HEARTBEAT_SECONDS", "60"))
MAX_HOLD_MINUTES = float(os.getenv("LEADLAG_MAX_HOLD_MINUTES", "8"))
WIN_COOLDOWN_MINUTES = 2
LOSS_COOLDOWN_MINUTES = 5
LOSS_STREAK_COOLDOWN_MINUTES = 30
MAX_CONSECUTIVE_LOSSES = 4
MAX_DAILY_LOSS_PCT = 0.012

MOMENTUM_MIN_Z = 0.80
LEADER_COMPONENT_MIN_Z = 0.25
LAG_GAP_MIN_Z = 0.35
LEADER_RETURN_MIN = 0.0017
LAG_RETURN_MIN = 0.0012
MIN_EXPECTED_MOVE = LAG_RETURN_MIN * 0.80  # consistent with expected_move = 80% of lag
EXIT_LAG_RETURN = 0.00045
LEADER_FADE_RETURN = 0.00045

BOOK_LONG_MIN = 0.52
BOOK_SHORT_MAX = 0.48
BOOK_FLIP_LONG = 0.48
BOOK_FLIP_SHORT = 0.52
MAX_SPREAD_PCT = 0.0008

MIN_STOP_RATE = 0.0035
MAX_STOP_RATE = 0.0075
MIN_TARGET_RATE = 0.0040
MAX_TARGET_RATE = 0.0100
ATR_STOP_MULT = 1.05

DB_STATE_TABLE = "leadlag_state"
DB_TRADE_TABLE = "leadlag_trades"
DB_SIGNAL_TABLE = "leadlag_signals"

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
    "last_scan": None,
    "last_signal": None,
    "cooldown_until": None,
    "last_entry_candle": None,
    "analysis": None,
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
        "trades": state["trades"][-250:],
        "cooldown_until": state["cooldown_until"],
        "last_entry_candle": state["last_entry_candle"],
        "last_signal": state["last_signal"],
        "status": state["status"],
        "error": state["error"],
        "last_scan": state["last_scan"],
        "analysis": state["analysis"],
        "build": state["build"],
    }


def init_persistence():
    global DATABASE_URL
    DATABASE_URL = getattr(base, "DATABASE_URL", None) or os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        state["persistence"] = "memory"
        state["persistence_error"] = "DATABASE_URL is not configured"
        return
    try:
        with _db() as conn:
            conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {DB_STATE_TABLE} (
                    id integer PRIMARY KEY,
                    state jsonb NOT NULL,
                    updated_at timestamptz NOT NULL DEFAULT now()
                )
            """)
            conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {DB_TRADE_TABLE} (
                    id bigserial PRIMARY KEY,
                    side text NOT NULL,
                    entry double precision NOT NULL,
                    exit double precision NOT NULL,
                    qty double precision NOT NULL,
                    gross_pnl double precision NOT NULL,
                    fees double precision NOT NULL,
                    net_pnl double precision NOT NULL,
                    reason text,
                    leader_return double precision,
                    lag_return double precision,
                    leader_z double precision,
                    gap_z double precision,
                    opened_at timestamptz,
                    closed_at timestamptz
                )
            """)
            conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {DB_SIGNAL_TABLE} (
                    id bigserial PRIMARY KEY,
                    candle_time bigint,
                    side text,
                    decision text,
                    reason text,
                    leader_return double precision,
                    xrp_return double precision,
                    lag_return double precision,
                    leader_z double precision,
                    xrp_z double precision,
                    gap_z double precision,
                    book_imbalance double precision,
                    spread_pct double precision,
                    created_at timestamptz NOT NULL DEFAULT now()
                )
            """)
            row = conn.execute(f"SELECT state FROM {DB_STATE_TABLE} WHERE id=1").fetchone()
            if row and isinstance(row[0], dict):
                saved = row[0]
                for key in ("balance", "equity", "open_position", "trades",
                            "cooldown_until", "last_entry_candle", "last_signal"):
                    if key in saved:
                        state[key] = saved[key]
            else:
                conn.execute(
                    f"INSERT INTO {DB_STATE_TABLE}(id,state,updated_at) VALUES(1,%s,now()) "
                    "ON CONFLICT(id) DO NOTHING",
                    (Jsonb(_payload()),),
                )
        state["persistence"] = "postgres"
        state["persistence_error"] = None
        _last_state_save = time.monotonic()
    except Exception as e:
        state["persistence"] = "memory"
        state["persistence_error"] = repr(e)
        print("LEADLAG PERSIST INIT", repr(e), flush=True)


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
    except Exception as e:
        state["persistence_error"] = repr(e)
        print("LEADLAG SAVE STATE", repr(e), flush=True)


def heartbeat_state(force=False):
    if force or time.monotonic() - _last_state_save >= STATE_HEARTBEAT_SECONDS:
        save_state()


def save_signal(a, decision, reason):
    if not DATABASE_URL:
        return
    try:
        with _db() as conn:
            conn.execute(
                f"""INSERT INTO {DB_SIGNAL_TABLE}(
                    candle_time,side,decision,reason,leader_return,xrp_return,lag_return,
                    leader_z,xrp_z,gap_z,book_imbalance,spread_pct
                ) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    a.get("candle_time"), a.get("signal"), decision, reason,
                    a.get("leader_return"), a.get("xrp_return"), a.get("lag_return"),
                    a.get("leader_z"), a.get("xrp_z"), a.get("gap_z"),
                    a.get("book_imbalance"), a.get("spread_pct"),
                ),
            )
    except Exception as e:
        state["persistence_error"] = repr(e)


def save_trade(t):
    if not DATABASE_URL:
        return
    try:
        with _db() as conn:
            conn.execute(
                f"""INSERT INTO {DB_TRADE_TABLE}(
                    side,entry,exit,qty,gross_pnl,fees,net_pnl,reason,
                    leader_return,lag_return,leader_z,gap_z,opened_at,closed_at
                ) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    t["side"], t["entry"], t["exit"], t["qty"],
                    t["gross_pnl"], t["fees"], t["net_pnl"], t["reason"],
                    t.get("leader_return"), t.get("lag_return"),
                    t.get("leader_z"), t.get("gap_z"),
                    t["opened_at"], t["closed_at"],
                ),
            )
    except Exception as e:
        state["persistence_error"] = repr(e)


def log_return(closes, minutes=3):
    if len(closes) <= minutes or closes[-1-minutes] <= 0 or closes[-1] <= 0:
        return 0.0
    return math.log(closes[-1] / closes[-1-minutes])


def z_momentum(closes, minutes=3, window=30):
    if len(closes) < max(window + 2, minutes + 2):
        return 0.0
    rets = []
    start = max(1, len(closes) - window - 1)
    for i in range(start, len(closes)):
        if closes[i] > 0 and closes[i-1] > 0:
            rets.append(math.log(closes[i] / closes[i-1]))
    if len(rets) < 8:
        return 0.0
    mean = sum(rets) / len(rets)
    var = sum((x - mean) ** 2 for x in rets) / len(rets)
    sigma = math.sqrt(var)
    if sigma <= 1e-12:
        return 0.0
    return log_return(closes, minutes) / (sigma * math.sqrt(minutes))


def atr_rate(klines, period=14):
    rows = klines[:-1]
    if len(rows) < period + 2:
        return MIN_STOP_RATE
    h = [float(x[2]) for x in rows]
    l = [float(x[3]) for x in rows]
    c = [float(x[4]) for x in rows]
    atr = base.atr_wilder(h, l, c, period)
    return (atr / c[-1]) if atr and c[-1] else MIN_STOP_RATE


async def order_book():
    d = await base.binance_get("/api/v3/depth", {"symbol": TRADE_SYMBOL, "limit": 20})
    bids = d.get("bids", [])
    asks = d.get("asks", [])
    if not bids or not asks:
        return {"imbalance": 0.5, "spread_pct": 1.0}
    bid_value = sum(float(p) * float(q) for p, q in bids)
    ask_value = sum(float(p) * float(q) for p, q in asks)
    best_bid = float(bids[0][0])
    best_ask = float(asks[0][0])
    mid = (best_bid + best_ask) / 2
    return {
        "imbalance": bid_value / (bid_value + ask_value) if bid_value + ask_value else 0.5,
        "spread_pct": (best_ask - best_bid) / mid if mid else 1.0,
    }


async def analyze():
    btc_k, eth_k, xrp_k, book = await asyncio.gather(
        base.get_klines(BTC_SYMBOL, "1m", limit=90),
        base.get_klines(ETH_SYMBOL, "1m", limit=90),
        base.get_klines(TRADE_SYMBOL, "1m", limit=90),
        order_book(),
    )
    btc = [float(x[4]) for x in btc_k[:-1]]
    eth = [float(x[4]) for x in eth_k[:-1]]
    xrp = [float(x[4]) for x in xrp_k[:-1]]

    rb = log_return(btc, 3)
    re = log_return(eth, 3)
    rx = log_return(xrp, 3)
    zb = z_momentum(btc, 3)
    ze = z_momentum(eth, 3)
    zx = z_momentum(xrp, 3)

    leader_return = 0.55 * rb + 0.45 * re
    leader_z = 0.55 * zb + 0.45 * ze
    lag_return = leader_return - rx
    gap_z = leader_z - zx
    imbalance = float(book["imbalance"])
    spread = float(book["spread_pct"])
    expected_move = min(abs(lag_return) * 0.80, MAX_TARGET_RATE)

    side = "WAIT"
    reason = "NO_SETUP"

    long_ok = (
        rb > 0 and re > 0
        and zb >= LEADER_COMPONENT_MIN_Z and ze >= LEADER_COMPONENT_MIN_Z
        and leader_z >= MOMENTUM_MIN_Z
        and leader_return >= LEADER_RETURN_MIN
        and gap_z >= LAG_GAP_MIN_Z
        and lag_return >= LAG_RETURN_MIN
        and zx > -0.35
        and imbalance >= BOOK_LONG_MIN
        and spread <= MAX_SPREAD_PCT
        and expected_move >= MIN_EXPECTED_MOVE
    )
    short_ok = (
        rb < 0 and re < 0
        and zb <= -LEADER_COMPONENT_MIN_Z and ze <= -LEADER_COMPONENT_MIN_Z
        and leader_z <= -MOMENTUM_MIN_Z
        and leader_return <= -LEADER_RETURN_MIN
        and gap_z <= -LAG_GAP_MIN_Z
        and lag_return <= -LAG_RETURN_MIN
        and zx < 0.35
        and imbalance <= BOOK_SHORT_MAX
        and spread <= MAX_SPREAD_PCT
        and expected_move >= MIN_EXPECTED_MOVE
    )

    blockers = []
    if long_ok:
        side, reason = "LONG", "BTC_ETH_LEAD_XRP_LAG"
    elif short_ok:
        side, reason = "SHORT", "BTC_ETH_LEAD_XRP_LAG"
    else:
        if leader_return >= 0:
            reason = "WAIT_LONG_FILTERS"
            checks = [
                ("BTC není v růstu", rb > 0),
                ("ETH není v růstu", re > 0),
                (f"BTC momentum z < {LEADER_COMPONENT_MIN_Z:.2f}", zb >= LEADER_COMPONENT_MIN_Z),
                (f"ETH momentum z < {LEADER_COMPONENT_MIN_Z:.2f}", ze >= LEADER_COMPONENT_MIN_Z),
                (f"Leader z < {MOMENTUM_MIN_Z:.2f}", leader_z >= MOMENTUM_MIN_Z),
                (f"Leader pohyb < {LEADER_RETURN_MIN*100:.2f} %", leader_return >= LEADER_RETURN_MIN),
                (f"XRP lag gap z < {LAG_GAP_MIN_Z:.2f}", gap_z >= LAG_GAP_MIN_Z),
                (f"XRP zaostání < {LAG_RETURN_MIN*100:.2f} %", lag_return >= LAG_RETURN_MIN),
                ("XRP momentum je příliš záporné", zx > -0.35),
                (f"Order book < {BOOK_LONG_MIN:.2f}", imbalance >= BOOK_LONG_MIN),
                (f"Spread > {MAX_SPREAD_PCT*100:.3f} %", spread <= MAX_SPREAD_PCT),
                (f"Očekávaný pohyb < {MIN_EXPECTED_MOVE*100:.2f} %", expected_move >= MIN_EXPECTED_MOVE),
            ]
        else:
            reason = "WAIT_SHORT_FILTERS"
            checks = [
                ("BTC není v poklesu", rb < 0),
                ("ETH není v poklesu", re < 0),
                (f"BTC momentum z > {-LEADER_COMPONENT_MIN_Z:.2f}", zb <= -LEADER_COMPONENT_MIN_Z),
                (f"ETH momentum z > {-LEADER_COMPONENT_MIN_Z:.2f}", ze <= -LEADER_COMPONENT_MIN_Z),
                (f"Leader z > {-MOMENTUM_MIN_Z:.2f}", leader_z <= -MOMENTUM_MIN_Z),
                (f"Leader pokles < {LEADER_RETURN_MIN*100:.2f} %", leader_return <= -LEADER_RETURN_MIN),
                (f"XRP lag gap z > {-LAG_GAP_MIN_Z:.2f}", gap_z <= -LAG_GAP_MIN_Z),
                (f"XRP zaostání < {LAG_RETURN_MIN*100:.2f} %", lag_return <= -LAG_RETURN_MIN),
                ("XRP momentum je příliš kladné", zx < 0.35),
                (f"Order book > {BOOK_SHORT_MAX:.2f}", imbalance <= BOOK_SHORT_MAX),
                (f"Spread > {MAX_SPREAD_PCT*100:.3f} %", spread <= MAX_SPREAD_PCT),
                (f"Očekávaný pohyb < {MIN_EXPECTED_MOVE*100:.2f} %", expected_move >= MIN_EXPECTED_MOVE),
            ]
        blockers = [label for label, ok in checks if not ok]

    out = {
        "signal": side,
        "reason": reason,
        "candle_time": int(xrp_k[-2][0]),
        "price": float(xrp_k[-1][4]),
        "btc_return": rb,
        "eth_return": re,
        "xrp_return": rx,
        "leader_return": leader_return,
        "lag_return": lag_return,
        "btc_z": zb,
        "eth_z": ze,
        "xrp_z": zx,
        "leader_z": leader_z,
        "gap_z": gap_z,
        "book_imbalance": imbalance,
        "spread_pct": spread,
        "expected_move": expected_move,
        "atr_rate": atr_rate(xrp_k),
        "blockers": blockers,
    }
    state["analysis"] = out
    return out


def net_pnl_for_exit(p, market_price):
    entry = float(p["entry"])
    qty = float(p["qty"])
    side = p["side"]
    exit_exec = market_price * (1 - base.SLIPPAGE_RATE if side == "LONG" else 1 + base.SLIPPAGE_RATE)
    gross = (exit_exec - entry) * qty if side == "LONG" else (entry - exit_exec) * qty
    fees = (entry * qty + exit_exec * qty) * base.FEE_RATE
    return exit_exec, gross, fees, gross - fees


def open_trade(a, market_price):
    if state["open_position"]:
        return False
    side = a["signal"]
    if side not in ("LONG", "SHORT"):
        return False

    entry = market_price * (1 + base.SLIPPAGE_RATE if side == "LONG" else 1 - base.SLIPPAGE_RATE)
    stop_rate = min(MAX_STOP_RATE, max(MIN_STOP_RATE, float(a["atr_rate"]) * ATR_STOP_MULT))
    target_rate = min(MAX_TARGET_RATE, max(MIN_TARGET_RATE, float(a["expected_move"]) * 0.90))

    stop = entry * (1 - stop_rate) if side == "LONG" else entry * (1 + stop_rate)
    tp = entry * (1 + target_rate) if side == "LONG" else entry * (1 - target_rate)

    _, _, _, loss_one = net_pnl_for_exit(
        {"entry": entry, "qty": 1.0, "side": side},
        stop,
    )
    loss_one = abs(loss_one)
    if loss_one <= 0:
        return False

    risk_dollars = float(state["balance"]) * RISK_PER_TRADE
    qty_by_risk = risk_dollars / loss_one
    qty_by_cap = float(state["balance"]) * MAX_NOTIONAL_SHARE / entry
    qty = min(qty_by_risk, qty_by_cap)
    if qty <= 0:
        return False

    state["open_position"] = {
        "side": side,
        "entry": entry,
        "stop": stop,
        "tp": tp,
        "qty": qty,
        "notional": qty * entry,
        "risk_dollars": risk_dollars,
        "stop_rate": stop_rate,
        "target_rate": target_rate,
        "leader_return": a["leader_return"],
        "lag_return": a["lag_return"],
        "leader_z": a["leader_z"],
        "gap_z": a["gap_z"],
        "book_imbalance": a["book_imbalance"],
        "book_flip_count": 0,
        "opened_at": utcnow().isoformat(),
        "candle_time": a["candle_time"],
    }
    state["last_entry_candle"] = a["candle_time"]
    state["last_signal"] = {
        "side": side,
        "reason": a["reason"],
        "leader_return": a["leader_return"],
        "lag_return": a["lag_return"],
        "leader_z": a["leader_z"],
        "gap_z": a["gap_z"],
        "opened_at": state["open_position"]["opened_at"],
    }
    save_signal(a, "ENTER", a["reason"])
    save_state()
    print(
        "LEADLAG OPEN {} XRP entry={:.6f} lag={:.3f}% leader={:.3f}%".format(
            side, entry, a["lag_return"] * 100, a["leader_return"] * 100
        ),
        flush=True,
    )
    return True


def consecutive_losses():
    n = 0
    for t in reversed(state["trades"]):
        if float(t.get("net_pnl", 0)) < 0:
            n += 1
        else:
            break
    return n


def daily_loss():
    today = utcnow().date()
    total = 0.0
    for t in state["trades"]:
        try:
            if datetime.fromisoformat(t["closed_at"]).date() == today:
                total += float(t["net_pnl"])
        except Exception:
            pass
    return total


def close_trade(market_price, reason):
    p = state["open_position"]
    if not p:
        return
    exit_exec, gross, fees, net = net_pnl_for_exit(p, market_price)
    state["balance"] = float(state["balance"]) + net
    state["equity"] = state["balance"]
    trade = {
        **p,
        "exit": exit_exec,
        "gross_pnl": gross,
        "fees": fees,
        "net_pnl": net,
        "reason": reason,
        "closed_at": utcnow().isoformat(),
    }
    state["trades"].append(trade)
    state["trades"] = state["trades"][-250:]
    state["open_position"] = None

    streak = consecutive_losses()
    cooldown = LOSS_COOLDOWN_MINUTES if net < 0 else WIN_COOLDOWN_MINUTES
    if net < 0 and streak >= MAX_CONSECUTIVE_LOSSES:
        cooldown = LOSS_STREAK_COOLDOWN_MINUTES
    state["cooldown_until"] = (utcnow() + timedelta(minutes=cooldown)).isoformat()

    save_trade(trade)
    save_state()
    print(
        "LEADLAG CLOSE {} net={:.2f} reason={}".format(p["side"], net, reason),
        flush=True,
    )


async def manage_position(a=None):
    p = state["open_position"]
    if not p:
        return
    price = await base.get_live_price(TRADE_SYMBOL, max_age=1.0)
    _, _, _, net = net_pnl_for_exit(p, price)
    state["equity"] = float(state["balance"]) + net

    if p["side"] == "LONG":
        if price <= float(p["stop"]):
            close_trade(price, "STOP LOSS")
            return
        if price >= float(p["tp"]):
            close_trade(price, "TAKE PROFIT")
            return
    else:
        if price >= float(p["stop"]):
            close_trade(price, "STOP LOSS")
            return
        if price <= float(p["tp"]):
            close_trade(price, "TAKE PROFIT")
            return

    age_min = (utcnow() - datetime.fromisoformat(p["opened_at"])).total_seconds() / 60.0
    if age_min >= MAX_HOLD_MINUTES:
        close_trade(price, "TIME EXIT")
        return

    if a is None or age_min < 0.75:
        return

    if p["side"] == "LONG":
        if a["lag_return"] <= EXIT_LAG_RETURN:
            close_trade(price, "LAG CLOSED")
            return
        if a["leader_return"] <= LEADER_FADE_RETURN:
            close_trade(price, "LEADER FADED")
            return
        if a["book_imbalance"] <= BOOK_FLIP_LONG:
            p["book_flip_count"] = int(p.get("book_flip_count", 0)) + 1
            if p["book_flip_count"] >= 3:
                close_trade(price, "BOOK FLIP x3")
                return
        else:
            p["book_flip_count"] = 0
    else:
        if a["lag_return"] >= -EXIT_LAG_RETURN:
            close_trade(price, "LAG CLOSED")
            return
        if a["leader_return"] >= -LEADER_FADE_RETURN:
            close_trade(price, "LEADER FADED")
            return
        if a["book_imbalance"] >= BOOK_FLIP_SHORT:
            p["book_flip_count"] = int(p.get("book_flip_count", 0)) + 1
            if p["book_flip_count"] >= 3:
                close_trade(price, "BOOK FLIP x3")
                return
        else:
            p["book_flip_count"] = 0


def cooldown_active():
    raw = state.get("cooldown_until")
    if not raw:
        return False
    try:
        return utcnow() < datetime.fromisoformat(raw)
    except Exception:
        return False


async def cycle():
    a = await analyze()
    state["last_scan"] = utcnow().isoformat()
    state["status"] = "running"
    state["error"] = None

    if state["open_position"]:
        await manage_position(a)
        return

    state["equity"] = state["balance"]

    if cooldown_active():
        return

    max_daily_loss = max(START_BALANCE, float(state["balance"])) * MAX_DAILY_LOSS_PCT
    if daily_loss() <= -max_daily_loss:
        state["status"] = "daily_loss_guard"
        return

    if a["signal"] in ("LONG", "SHORT"):
        if state.get("last_entry_candle") == a["candle_time"]:
            return
        price = await base.get_live_price(TRADE_SYMBOL, max_age=1.0)
        open_trade(a, price)


async def bot_loop():
    await asyncio.sleep(4)
    while True:
        try:
            await cycle()
        except Exception as e:
            state["status"] = "error"
            state["error"] = f"{type(e).__name__}: {e}"
            print("LEADLAG CYCLE", state["error"], flush=True)
        finally:
            heartbeat_state()
        await asyncio.sleep(SCAN_SECONDS)


def install(base_module):
    global base
    base = base_module
    init_persistence()
    heartbeat_state(force=True)
    return state
