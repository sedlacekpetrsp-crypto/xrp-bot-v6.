"""
FAST Edge Scalper — PAPER ONLY.

Purpose:
- Preserve the frequent-entry behavior of the older high-turnover V8 period.
- Require enough expected movement to cover modeled fees + slippage.
- Keep a separate paper balance and history so FAST does not contaminate FLY results.
- One open FAST position at a time across XRP/ETH/SOL.
"""
from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone, timedelta

import psycopg
from psycopg.types.json import Jsonb

BUILD = "fast-edge-v3-no-time-cutoff-20260921"
MODE = "PAPER"

SYMBOLS = ("XRPUSDC", "ETHUSDC", "SOLUSDC")
START_BALANCE = float(os.getenv("FAST_START_BALANCE", "10000"))
RISK_PER_TRADE = float(os.getenv("FAST_RISK_PER_TRADE", "0.0015"))
MAX_NOTIONAL_SHARE = float(os.getenv("FAST_MAX_NOTIONAL_SHARE", "0.30"))

SCAN_SECONDS = 12
SOFT_HOLD_MINUTES = 5.0
EMERGENCY_HOLD_MINUTES = 120.0
WIN_COOLDOWN_SECONDS = 30
LOSS_COOLDOWN_SECONDS = 120
LOSS_STREAK_COOLDOWN_MINUTES = 20
MAX_CONSECUTIVE_LOSSES = 4
MAX_DAILY_LOSS_PCT = 0.008

MIN_LONG_SHORT_SCORE = 6
MIN_VOLUME_RATIO = 1.15
MIN_ADX = 16.0
MIN_Z = 0.55
TRANSITION_Z = 0.90
BOOK_LONG_MIN = 0.53
BOOK_SHORT_MAX = 0.47
MAX_SPREAD_PCT = 0.0006
MIN_EDGE_MULTIPLE = 2.50

MIN_STOP_RATE = 0.0025
MAX_STOP_RATE = 0.0050
ATR_STOP_MULT = 0.85
MIN_NET_TARGET_RATE = 0.0018
NET_RISK_REWARD = 1.10

EARLY_PROFIT_USDC = 4.0
PROFIT_LOCK_START_USDC = 6.0
PROFIT_GIVEBACK_USDC = 2.0
EARLY_EXIT_MIN_AGE = 0.75
BREAKEVEN_TRIGGER_R = 0.60

DB_STATE_TABLE = "fast_scalp_state"
DB_TRADE_TABLE = "fast_scalp_trades"

base = None
DATABASE_URL = None

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
    "analysis": [],
    "last_scan": None,
    "last_entry_candle": {},
    "cooldown_until": None,
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
        "trades": state["trades"][-300:],
        "last_entry_candle": state["last_entry_candle"],
        "cooldown_until": state["cooldown_until"],
    }


def init_persistence():
    global DATABASE_URL
    DATABASE_URL = getattr(base, "DATABASE_URL", None) or os.getenv("DATABASE_URL")
    if not DATABASE_URL:
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
                    symbol text NOT NULL,
                    side text NOT NULL,
                    entry double precision NOT NULL,
                    exit double precision NOT NULL,
                    qty double precision NOT NULL,
                    gross_pnl double precision NOT NULL,
                    fees double precision NOT NULL,
                    net_pnl double precision NOT NULL,
                    reason text,
                    score integer,
                    volume_ratio double precision,
                    z_momentum double precision,
                    book_imbalance double precision,
                    spread_pct double precision,
                    edge_pct double precision,
                    risk_dollars double precision,
                    opened_at timestamptz,
                    closed_at timestamptz
                )
            """)
            row = conn.execute(f"SELECT state FROM {DB_STATE_TABLE} WHERE id=1").fetchone()
            if row and isinstance(row[0], dict):
                saved = row[0]
                for key in ("balance", "equity", "open_position", "trades",
                            "last_entry_candle", "cooldown_until"):
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
    except Exception as e:
        state["persistence_error"] = repr(e)
        print("FAST PERSIST INIT", repr(e), flush=True)


def save_state():
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
        print("FAST SAVE STATE", repr(e), flush=True)


def save_trade(t):
    if not DATABASE_URL:
        return
    try:
        with _db() as conn:
            conn.execute(
                f"""INSERT INTO {DB_TRADE_TABLE}(
                    symbol,side,entry,exit,qty,gross_pnl,fees,net_pnl,reason,
                    score,volume_ratio,z_momentum,book_imbalance,spread_pct,
                    edge_pct,risk_dollars,opened_at,closed_at
                ) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    t["symbol"], t["side"], t["entry"], t["exit"], t["qty"],
                    t["gross_pnl"], t["fees"], t["net_pnl"], t["reason"],
                    t.get("score"), t.get("volume_ratio"), t.get("z_momentum"),
                    t.get("book_imbalance"), t.get("spread_pct"), t.get("edge_pct"),
                    t.get("risk_dollars"), t["opened_at"], t["closed_at"],
                ),
            )
    except Exception as e:
        state["persistence_error"] = repr(e)
        print("FAST SAVE TRADE", repr(e), flush=True)


def daily_pnl():
    today = utcnow().date()
    total = 0.0
    for t in state["trades"]:
        try:
            if datetime.fromisoformat(t["closed_at"]).date() == today:
                total += float(t.get("net_pnl") or 0)
        except Exception:
            pass
    return total


def consecutive_losses():
    n = 0
    for t in reversed(state["trades"]):
        if float(t.get("net_pnl") or 0) < 0:
            n += 1
        else:
            break
    return n


def cooldown_active():
    raw = state.get("cooldown_until")
    if not raw:
        return False
    try:
        return utcnow() < datetime.fromisoformat(raw)
    except Exception:
        return False


def _fast_signal(row):
    if not row or row.get("symbol") not in SYMBOLS:
        return dict(row or {}, fast_signal="WAIT", fast_score=0, fast_blockers=["NO_DATA"])

    regime = row.get("regime")
    vr = float(row.get("volume_ratio") or 0)
    adx = float(row.get("adx5") or 0)
    z = float(row.get("z_momentum") or 0)
    imb = float(row.get("book_imbalance") or 0.5)
    spread = float(row.get("real_spread_pct") or row.get("book_spread") or 1)
    edge = float(row.get("expected_move_pct") or 0)
    ls = int(row.get("long_score") or 0)
    ss = int(row.get("short_score") or 0)
    news = row.get("news") or {}

    cost_ok = edge >= float(base.ROUND_TRIP_COST) * MIN_EDGE_MULTIPLE
    common = [
        ("VOLUME", vr >= MIN_VOLUME_RATIO),
        ("ADX", adx >= MIN_ADX),
        ("SPREAD", spread <= MAX_SPREAD_PCT),
        ("EDGE", cost_ok),
    ]

    long_checks = common + [
        ("REGIME", regime in ("TREND_LONG", "TRANSITION")),
        ("SCORE", ls >= MIN_LONG_SHORT_SCORE),
        ("MOMENTUM", z >= (TRANSITION_Z if regime == "TRANSITION" else MIN_Z)),
        ("BOOK", imb >= BOOK_LONG_MIN),
        ("NEWS", not bool(news.get("bearish"))),
    ]
    short_checks = common + [
        ("REGIME", regime in ("TREND_SHORT", "TRANSITION")),
        ("SCORE", ss >= MIN_LONG_SHORT_SCORE),
        ("MOMENTUM", z <= -(TRANSITION_Z if regime == "TRANSITION" else MIN_Z)),
        ("BOOK", imb <= BOOK_SHORT_MAX),
        ("NEWS", not bool(news.get("bullish"))),
    ]

    long_ok = all(ok for _, ok in long_checks)
    short_ok = all(ok for _, ok in short_checks)

    side = "LONG" if long_ok else "SHORT" if short_ok else "WAIT"
    score = 0
    if side == "LONG":
        score = ls + (1 if vr >= 1.5 else 0) + (1 if z >= 1.0 else 0) + (1 if imb >= 0.56 else 0)
        blockers = []
    elif side == "SHORT":
        score = ss + (1 if vr >= 1.5 else 0) + (1 if z <= -1.0 else 0) + (1 if imb <= 0.44 else 0)
        blockers = []
    else:
        chosen = long_checks if z >= 0 else short_checks
        blockers = [name for name, ok in chosen if not ok]

    out = dict(row)
    out["fast_signal"] = side
    out["fast_score"] = score
    out["fast_blockers"] = blockers
    return out


async def analyze():
    # FLY refreshes these rows every cycle. Reuse them to avoid doubling API load.
    rows = list(getattr(base, "last_analysis", {}).values())
    if len(rows) < len(SYMBOLS) or any(r.get("signal") == "ERROR" for r in rows if isinstance(r, dict)):
        rows = await base.analyze_all()
    out = [_fast_signal(r) for r in rows if isinstance(r, dict) and r.get("symbol") in SYMBOLS]
    state["analysis"] = out
    return out


def choose_best(rows):
    candidates = []
    for a in rows:
        side = a.get("fast_signal")
        if side not in ("LONG", "SHORT"):
            continue
        if state["last_entry_candle"].get(a["symbol"]) == a.get("candle_time"):
            continue
        rank = (
            int(a.get("fast_score") or 0),
            float(a.get("expected_move_pct") or 0),
            float(a.get("volume_ratio") or 0),
            abs(float(a.get("z_momentum") or 0)),
        )
        candidates.append((rank, a))
    if not candidates:
        return None
    candidates.sort(key=lambda z: z[0], reverse=True)
    return candidates[0][1]


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
    side = a.get("fast_signal")
    if side not in ("LONG", "SHORT"):
        return False

    entry = market_price * (1 + base.SLIPPAGE_RATE if side == "LONG" else 1 - base.SLIPPAGE_RATE)
    atr = float(a.get("atr") or 0)
    atr_rate = atr / market_price if atr > 0 and market_price > 0 else MIN_STOP_RATE
    stop_rate = min(MAX_STOP_RATE, max(MIN_STOP_RATE, atr_rate * ATR_STOP_MULT))
    stop = entry * (1 - stop_rate) if side == "LONG" else entry * (1 + stop_rate)

    _, _, _, loss_one = net_pnl_for_exit({"entry": entry, "qty": 1.0, "side": side}, stop)
    loss_one = abs(loss_one)
    if loss_one <= 0:
        return False

    risk_dollars = float(state["balance"]) * RISK_PER_TRADE
    qty = min(
        risk_dollars / loss_one,
        float(state["balance"]) * MAX_NOTIONAL_SHARE / entry,
    )
    if qty <= 0:
        return False

    target_net_per_unit = max(loss_one * NET_RISK_REWARD, entry * MIN_NET_TARGET_RATE)
    tp = base.target_market_for_net_profit(side, entry, target_net_per_unit)

    p = {
        "symbol": a["symbol"],
        "side": side,
        "entry": entry,
        "stop": stop,
        "tp": tp,
        "qty": qty,
        "notional": qty * entry,
        "risk_dollars": qty * loss_one,
        "score": int(a.get("fast_score") or 0),
        "volume_ratio": float(a.get("volume_ratio") or 0),
        "z_momentum": float(a.get("z_momentum") or 0),
        "book_imbalance": float(a.get("book_imbalance") or 0.5),
        "spread_pct": float(a.get("real_spread_pct") or a.get("book_spread") or 1),
        "edge_pct": float(a.get("expected_move_pct") or 0),
        "peak_net": 0.0,
        "breakeven_moved": False,
        "opened_at": utcnow().isoformat(),
        "candle_time": a.get("candle_time"),
    }
    state["open_position"] = p
    state["last_entry_candle"][a["symbol"]] = a.get("candle_time")
    save_state()
    print(
        "FAST OPEN {} {} entry={:.6f} score={} edge={:.3f}%".format(
            a["symbol"], side, entry, p["score"], p["edge_pct"] * 100
        ),
        flush=True,
    )
    return True


def close_trade(market_price, reason):
    p = state["open_position"]
    if not p:
        return
    exit_exec, gross, fees, net = net_pnl_for_exit(p, market_price)
    state["balance"] = float(state["balance"]) + net
    state["equity"] = state["balance"]
    t = {
        **p,
        "exit": exit_exec,
        "gross_pnl": gross,
        "fees": fees,
        "net_pnl": net,
        "reason": reason,
        "closed_at": utcnow().isoformat(),
    }
    state["trades"].append(t)
    state["trades"] = state["trades"][-300:]
    state["open_position"] = None

    streak = consecutive_losses()
    if net < 0 and streak >= MAX_CONSECUTIVE_LOSSES:
        seconds = LOSS_STREAK_COOLDOWN_MINUTES * 60
    else:
        seconds = LOSS_COOLDOWN_SECONDS if net < 0 else WIN_COOLDOWN_SECONDS
    state["cooldown_until"] = (utcnow() + timedelta(seconds=seconds)).isoformat()

    save_trade(t)
    save_state()
    print("FAST CLOSE {} net={:.2f} reason={}".format(p["symbol"], net, reason), flush=True)


async def manage_position(rows):
    p = state["open_position"]
    if not p:
        return
    price = await base.get_live_price(p["symbol"], max_age=1.0)
    _, _, _, net = net_pnl_for_exit(p, price)
    p["peak_net"] = max(float(p.get("peak_net") or 0), net)
    state["equity"] = float(state["balance"]) + net

    if p["side"] == "LONG":
        if price <= float(p["stop"]):
            close_trade(price, "FAST STOP")
            return
        if price >= float(p["tp"]):
            close_trade(price, "FAST TAKE PROFIT")
            return
    else:
        if price >= float(p["stop"]):
            close_trade(price, "FAST STOP")
            return
        if price <= float(p["tp"]):
            close_trade(price, "FAST TAKE PROFIT")
            return

    age = (utcnow() - datetime.fromisoformat(p["opened_at"])).total_seconds() / 60.0
    row = next((x for x in rows if x.get("symbol") == p["symbol"]), None)

    risk = max(float(p.get("risk_dollars") or 0), 1e-12)
    if not p.get("breakeven_moved") and float(p.get("peak_net") or 0) >= risk * BREAKEVEN_TRIGGER_R:
        p["stop"] = base.target_market_for_net_profit(p["side"], float(p["entry"]), 0.0)
        p["breakeven_moved"] = True
        save_state()

    if float(p.get("peak_net") or 0) >= PROFIT_LOCK_START_USDC:
        if float(p["peak_net"]) - net >= PROFIT_GIVEBACK_USDC:
            close_trade(price, "FAST PROFIT LOCK")
            return

    continuation = False
    danger = False
    if row:
        z = float(row.get("z_momentum") or 0)
        imb = float(row.get("book_imbalance") or 0.5)
        vr = float(row.get("volume_ratio") or 0)
        if p["side"] == "LONG":
            continuation = z >= 0.35 and imb >= 0.50 and vr >= 0.90
            danger = z <= -0.35 or imb <= 0.47
        else:
            continuation = z <= -0.35 and imb <= 0.50 and vr >= 0.90
            danger = z >= 0.35 or imb >= 0.53

        if age >= EARLY_EXIT_MIN_AGE and net >= EARLY_PROFIT_USDC and not continuation:
            close_trade(price, "FAST +4 NET / NO CONTINUATION")
            return
        if age >= EARLY_EXIT_MIN_AGE and net < 0 and danger:
            close_trade(price, "FAST MOMENTUM FLIP")
            return

    if age >= SOFT_HOLD_MINUTES and (row is None or not continuation):
        close_trade(price, "FAST ADAPTIVE EXIT / NO CONTINUATION")
        return

    if age >= EMERGENCY_HOLD_MINUTES:
        close_trade(price, "FAST EMERGENCY STALE EXIT")
        return

    save_state()


async def cycle():
    rows = await analyze()
    state["last_scan"] = utcnow().isoformat()
    state["status"] = "running"
    state["error"] = None

    if state["open_position"]:
        await manage_position(rows)
        return

    state["equity"] = state["balance"]
    if cooldown_active():
        state["status"] = "cooldown"
        return

    max_daily_loss = max(START_BALANCE, float(state["balance"])) * MAX_DAILY_LOSS_PCT
    if daily_pnl() <= -max_daily_loss:
        state["status"] = "daily_loss_guard"
        return

    best = choose_best(rows)
    if best:
        price = await base.get_live_price(best["symbol"], max_age=1.0)
        open_trade(best, price)


async def bot_loop():
    await asyncio.sleep(7)
    while True:
        try:
            await cycle()
        except Exception as e:
            state["status"] = "error"
            state["error"] = f"{type(e).__name__}: {e}"
            print("FAST CYCLE", state["error"], flush=True)
        await asyncio.sleep(SCAN_SECONDS)


def install(base_module):
    global base
    base = base_module
    init_persistence()
    return state
