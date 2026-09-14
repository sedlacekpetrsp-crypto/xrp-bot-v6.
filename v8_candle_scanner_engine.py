from market_data import market_get, install_data_health
import os
import time
from entry_rules import ENTRY_INTERVAL, STRATEGY_VERSION, MAX_ENTRY_DEVIATION, rejection
import json
import psycopg
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

import httpx
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(title="V8 Candle Scanner")
install_data_health(app)

BINANCE_API = os.getenv("BINANCE_API", "https://data-api.binance.vision")
SYMBOLS = [s.strip().upper() for s in os.getenv(
    "SCANNER_SYMBOLS",
    "XRPUSDT,SOLUSDT,ETHUSDT,DOGEUSDT,ADAUSDT,SUIUSDT,LINKUSDT,AVAXUSDT,HBARUSDT,FETUSDT,DOTUSDT,ATOMUSDT,NEARUSDT,ARBUSDT,RENDERUSDT"
).split(",") if s.strip()]

STARTING_BALANCE = float(os.getenv("STARTING_BALANCE", "10000"))
RISK_PER_TRADE = float(os.getenv("RISK_PER_TRADE", "0.003"))
RISK_REWARD = float(os.getenv("RISK_REWARD", "2.0"))
FEE_RATE = float(os.getenv("FEE_RATE", "0.0005"))
SLIPPAGE_RATE = float(os.getenv("SLIPPAGE_RATE", "0.0002"))
MAX_NOTIONAL_SHARE = float(os.getenv("MAX_NOTIONAL_SHARE", "0.50"))
MAX_TOTAL_NOTIONAL_SHARE = float(os.getenv("MAX_TOTAL_NOTIONAL_SHARE", "1.00"))
MAX_OPEN_POSITIONS = int(os.getenv("MAX_OPEN_POSITIONS", "5"))

BREAKOUT_LOOKBACK = int(os.getenv("EARLY_BREAKOUT_LOOKBACK", "4"))
BREAKOUT_VOLUME_RATIO = float(os.getenv("EARLY_BREAKOUT_VOLUME_RATIO", "1.05"))
MOMENTUM_MIN_MOVE = float(os.getenv("EARLY_MOMENTUM_MIN_MOVE", "0.0015"))
MOMENTUM_BODY_RATIO = float(os.getenv("EARLY_MOMENTUM_BODY_RATIO", "0.55"))
MOMENTUM_VOLUME_RATIO = float(os.getenv("EARLY_MOMENTUM_VOLUME_RATIO", "1.05"))
MAX_TRIGGER_EXTENSION = float(os.getenv("MAX_TRIGGER_EXTENSION", "0.0020"))

# 15m trend is now an adaptive filter, not a hard yes/no gate.
# When EMA20/EMA50 are very close, the 15m market is treated as neutral and
# a strong 1m breakout may enter in either direction with stricter confirmation.
TREND_NEUTRAL_STRENGTH = float(os.getenv("TREND_NEUTRAL_STRENGTH", "0.00035"))
NEUTRAL_VOLUME_RATIO = float(os.getenv("NEUTRAL_VOLUME_RATIO", "1.20"))
NEUTRAL_BODY_RATIO = float(os.getenv("NEUTRAL_BODY_RATIO", "0.62"))

TOP_N = int(os.getenv("TOP_N", "5"))
SCAN_SECONDS = int(os.getenv("SCAN_SECONDS", "15"))
last_scan_at = 0.0
MAX_TRADE_MINUTES = int(os.getenv("MAX_TRADE_MINUTES", "120"))
COOLDOWN_AFTER_LOSS_MIN = 0

paper_balance = STARTING_BALANCE
paper_positions: Dict[str, Dict[str, Any]] = {}
paper_position: Optional[Dict[str, Any]] = None
history: List[Dict[str, Any]] = []
last_scan: List[Dict[str, Any]] = []
last_signal: Dict[str, Any] = {"side": "WAIT"}
last_signals: List[Dict[str, Any]] = []
cooldown_until: Optional[datetime] = None
last_entry_candle: Dict[str, int] = {}
bot_task = None

DATABASE_URL = os.getenv("DATABASE_URL")
cycle_lock = asyncio.Lock()
state_loaded = False


def sync_legacy_position():
    global paper_position
    paper_position = next(iter(paper_positions.values()), None)


def save_state():
    if not DATABASE_URL:
        return
    sync_legacy_position()
    state = {
        "paper_balance": paper_balance,
        "paper_positions": paper_positions,
        "paper_position": paper_position,
        "history": history,
        "last_entry_candle": last_entry_candle,
    }
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(
            "INSERT INTO candle_v8_scanner_state (id, state) VALUES (1, %s::jsonb) "
            "ON CONFLICT (id) DO UPDATE SET state=EXCLUDED.state",
            (json.dumps(state),),
        )


def load_state():
    global paper_balance, paper_positions, history, last_entry_candle, state_loaded
    if state_loaded:
        return
    if not DATABASE_URL:
        raise RuntimeError("Scanner: DATABASE_URL chybí; nelze bezpečně ukládat historii")
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS candle_v8_scanner_state "
            "(id INTEGER PRIMARY KEY, state JSONB NOT NULL)"
        )
        row = conn.execute("SELECT state FROM candle_v8_scanner_state WHERE id=1").fetchone()

    state = row[0] if row else json.loads(os.getenv("SCANNER_INITIAL_STATE", "{}"))
    paper_balance = float(state.get("paper_balance", STARTING_BALANCE))
    stored_positions = state.get("paper_positions")
    if isinstance(stored_positions, dict):
        paper_positions = {
            str(symbol): position
            for symbol, position in stored_positions.items()
            if isinstance(position, dict)
        }
    elif isinstance(stored_positions, list):
        paper_positions = {
            str(position.get("symbol")): position
            for position in stored_positions
            if isinstance(position, dict) and position.get("symbol")
        }
    else:
        old = state.get("paper_position")
        paper_positions = (
            {str(old.get("symbol", "XRPUSDT")): old}
            if isinstance(old, dict)
            else {}
        )

    history = state.get("history", [])
    last_entry_candle = state.get("last_entry_candle", {})
    sync_legacy_position()
    save_state()
    state_loaded = True


def c(k):
    return {
        "t": int(k[0]), "o": float(k[1]), "h": float(k[2]),
        "l": float(k[3]), "c": float(k[4]), "v": float(k[5]),
    }


def ema(vals, period):
    if len(vals) < period:
        return None
    a = 2 / (period + 1)
    e = sum(vals[:period]) / period
    for x in vals[period:]:
        e = a * x + (1 - a) * e
    return e


def bullish(x): return x["c"] > x["o"]
def bearish(x): return x["c"] < x["o"]
def body(x): return abs(x["c"] - x["o"])
def rng(x): return max(x["h"] - x["l"], 1e-12)


async def klines(client, symbol, interval, limit):
    r = await market_get(
        client,
        f"{BINANCE_API}/api/v3/klines",
        params={"symbol": symbol, "interval": interval, "limit": limit},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


async def price(client, symbol):
    r = await market_get(
        client,
        f"{BINANCE_API}/api/v3/ticker/price",
        params={"symbol": symbol}, timeout=15,
    )
    r.raise_for_status()
    return float(r.json()["price"])


async def strength_for(client, symbol):
    try:
        h1, h4 = await asyncio.gather(
            klines(client, symbol, "1h", 6),
            klines(client, symbol, "4h", 6),
        )
        h1 = [c(x) for x in h1][:-1]
        h4 = [c(x) for x in h4][:-1]
        m1 = (h1[-1]["c"] / h1[-5]["o"] - 1) * 100 if len(h1) >= 5 else 0
        m4 = (h4[-1]["c"] / h4[-3]["o"] - 1) * 100 if len(h4) >= 3 else 0
        return {"symbol": symbol, "m1h": m1, "m4h": m4,
                "strength": 0.65 * m1 + 0.35 * m4}
    except Exception:
        return None


async def build_scan(client):
    rows = [r for r in await asyncio.gather(
        *(strength_for(client, s) for s in SYMBOLS)
    ) if r]
    rows.sort(key=lambda x: x["strength"], reverse=True)
    longs = {x["symbol"] for x in rows[:TOP_N]}
    shorts = {x["symbol"] for x in rows[-TOP_N:]}
    for rank, x in enumerate(rows, start=1):
        x["rank"] = rank
        x["bucket"] = (
            "LONG" if x["symbol"] in longs else
            "SHORT" if x["symbol"] in shorts else "NEUTRAL"
        )
        x["tradable"] = True
    return rows


def trigger_extension(side, trigger_level, current):
    if trigger_level <= 0 or current <= 0:
        return float("inf")
    return current / trigger_level - 1 if side == "LONG" else trigger_level / current - 1


def classify_15m_trend(e20, e50, reference_price):
    direction = "LONG" if e20 > e50 else "SHORT"
    strength = abs(e20 - e50) / reference_price
    state = "NEUTRAL" if strength <= TREND_NEUTRAL_STRENGTH else direction
    return direction, state, strength


async def signal_for(client, row):
    symbol = row["symbol"]
    if symbol in paper_positions:
        return None
    try:
        raw1, raw15 = await asyncio.gather(
            klines(client, symbol, ENTRY_INTERVAL, 60),
            klines(client, symbol, "15m", 70),
        )
        m = [c(x) for x in raw1][:-1]
        s = [c(x) for x in raw15][:-1]
        if len(m) < max(25, BREAKOUT_LOOKBACK + 3):
            return None

        a, b, conf = m[-3], m[-2], m[-1]
        avg_vol = sum(x["v"] for x in m[-21:-1]) / 20
        vol = conf["v"] / avg_vol if avg_vol else 0.0
        conf_body_ratio = body(conf) / rng(conf)

        closes = [x["c"] for x in s]
        e20, e50 = ema(closes, 20), ema(closes, 50)
        if not e20 or not e50:
            return None
        trend, trend_state, trend_strength = classify_15m_trend(e20, e50, conf["c"])

        side = None
        setup = None
        p_low = None
        p_high = None
        trigger_level = None
        required_vol = BREAKOUT_VOLUME_RATIO

        prev = m[-(BREAKOUT_LOOKBACK + 1):-1]
        prev_high = max(x["h"] for x in prev)
        prev_low = min(x["l"] for x in prev)

        if bullish(conf) and conf["c"] > prev_high:
            side = "LONG"
            setup = "EARLY_BREAKOUT"
            trigger_level = prev_high
            p_low = min(x["l"] for x in m[-4:])
            p_high = conf["h"]
            required_vol = BREAKOUT_VOLUME_RATIO
        elif bearish(conf) and conf["c"] < prev_low:
            side = "SHORT"
            setup = "EARLY_BREAKOUT"
            trigger_level = prev_low
            p_low = conf["l"]
            p_high = max(x["h"] for x in m[-4:])
            required_vol = BREAKOUT_VOLUME_RATIO

        if side is None:
            move = abs(conf["c"] / conf["o"] - 1)
            above_prev = conf["c"] > max(a["h"], b["h"])
            below_prev = conf["c"] < min(a["l"], b["l"])
            if bullish(conf) and move >= MOMENTUM_MIN_MOVE and conf_body_ratio >= MOMENTUM_BODY_RATIO and above_prev:
                side = "LONG"
                setup = "EARLY_MOMENTUM"
                trigger_level = max(a["h"], b["h"])
                p_low = min(x["l"] for x in m[-4:])
                p_high = conf["h"]
                required_vol = MOMENTUM_VOLUME_RATIO
            elif bearish(conf) and move >= MOMENTUM_MIN_MOVE and conf_body_ratio >= MOMENTUM_BODY_RATIO and below_prev:
                side = "SHORT"
                setup = "EARLY_MOMENTUM"
                trigger_level = min(a["l"], b["l"])
                p_low = conf["l"]
                p_high = max(x["h"] for x in m[-4:])
                required_vol = MOMENTUM_VOLUME_RATIO

        if not side:
            return None

        # Adaptive 15m filter:
        # 1) clear 15m trend -> only trade with that trend;
        # 2) neutral 15m EMA zone -> allow either direction, but only with
        #    stronger volume and a stronger 1m candle.
        if trend_state == "NEUTRAL":
            required_vol = max(required_vol, NEUTRAL_VOLUME_RATIO)
            if conf_body_ratio < NEUTRAL_BODY_RATIO:
                return None
            trend_filter = "NEUTRAL_15M_STRONG_1M"
        else:
            if side != trend:
                return None
            trend_filter = "ALIGNED_15M"

        if vol < required_vol:
            return None

        extension = trigger_extension(side, trigger_level, conf["c"])
        if extension < 0 or extension > MAX_TRIGGER_EXTENSION:
            return None
        if last_entry_candle.get(symbol) == conf["t"]:
            return None

        return {
            "symbol": symbol,
            "side": side,
            "setup": setup,
            "entry": conf["c"],
            "trigger_level": trigger_level,
            "trigger_extension": extension,
            "pattern_low": p_low,
            "pattern_high": p_high,
            "volume_ratio": vol,
            "candle_body_ratio": conf_body_ratio,
            "trend_strength": trend_strength,
            "trend": trend,
            "trend_state": trend_state,
            "trend_filter": trend_filter,
            "strength": row["strength"],
            "strength_bucket": row["bucket"],
            "candle_time": conf["t"],
        }
    except Exception:
        return None


def est_net_unit(side, entry, exit_market):
    exit_exec = exit_market * (1 - SLIPPAGE_RATE if side == "LONG" else 1 + SLIPPAGE_RATE)
    gross = (exit_exec - entry) if side == "LONG" else (entry - exit_exec)
    return gross - (entry + exit_exec) * FEE_RATE


def target_for_net(side, entry, target):
    f, s = FEE_RATE, SLIPPAGE_RATE
    if side == "LONG":
        ex = (target + entry * (1 + f)) / (1 - f)
        return ex / (1 - s)
    ex = (entry * (1 - f) - target) / (1 + f)
    return ex / (1 + s)


def open_notional():
    return sum(float(p.get("entry_price", 0)) * float(p.get("qty", 0))
               for p in paper_positions.values())


def open_position(sig, market):
    symbol = sig["symbol"]
    if symbol in paper_positions:
        sig["reason"] = "Na tomto coinu už je otevřená pozice"
        return False
    if len(paper_positions) >= MAX_OPEN_POSITIONS:
        sig["reason"] = "Dosažen maximální počet souběžných pozic"
        return False

    error = rejection(sig, market)
    if error:
        sig["reason"] = error
        return False

    market_extension = trigger_extension(sig["side"], float(sig["trigger_level"]), market)
    if market_extension < 0 or market_extension > MAX_TRIGGER_EXTENSION:
        sig["reason"] = f"NO CHASE: cena je {market_extension * 100:.2f} % od průrazu"
        return False

    side = sig["side"]
    entry = market * (1 + SLIPPAGE_RATE if side == "LONG" else 1 - SLIPPAGE_RATE)
    buf = market * 0.0002
    stop = (float(sig["pattern_low"]) - buf if side == "LONG"
            else float(sig["pattern_high"]) + buf)
    loss = -est_net_unit(side, entry, stop)
    if loss <= 0:
        sig["reason"] = "Neplatná vzdálenost stop-lossu"
        return False

    total_cap = paper_balance * MAX_TOTAL_NOTIONAL_SHARE
    available_notional = max(0.0, total_cap - open_notional())
    notional_cap = min(paper_balance * MAX_NOTIONAL_SHARE, available_notional)
    if notional_cap <= 0:
        sig["reason"] = "Není volný kapitál pro další pozici"
        return False

    qty = min((paper_balance * RISK_PER_TRADE) / loss, notional_cap / entry)
    if qty <= 0:
        sig["reason"] = "Vypočtené množství je nulové"
        return False

    tp = target_for_net(side, entry, loss * RISK_REWARD)
    paper_positions[symbol] = {
        **sig,
        "strategy_version": STRATEGY_VERSION,
        "signal_price": sig["entry"],
        "entry_market": market,
        "entry_price": entry,
        "stop_loss": stop,
        "take_profit": tp,
        "qty": qty,
        "risk_usdt": qty * loss,
        "entry_time": datetime.now(timezone.utc).isoformat(),
    }
    last_entry_candle[symbol] = sig["candle_time"]
    save_state()
    return True


def close_position(symbol, market, reason):
    global paper_balance
    p = paper_positions.get(symbol)
    if not p:
        return
    ex = market * (1 - SLIPPAGE_RATE if p["side"] == "LONG" else 1 + SLIPPAGE_RATE)
    gross = ((ex - p["entry_price"]) * p["qty"] if p["side"] == "LONG"
             else (p["entry_price"] - ex) * p["qty"])
    fees = (p["entry_price"] * p["qty"] + ex * p["qty"]) * FEE_RATE
    net = gross - fees
    paper_balance += net
    history.insert(0, {
        **p, "exit_price": ex, "net_pnl": net, "reason": reason,
        "exit_time": datetime.now(timezone.utc).isoformat(),
    })
    del history[100:]
    paper_positions.pop(symbol, None)
    save_state()


async def manage_positions(client):
    symbols = list(paper_positions)
    if not symbols:
        return
    quotes = await asyncio.gather(*(price(client, symbol) for symbol in symbols), return_exceptions=True)
    now = datetime.now(timezone.utc)
    for symbol, px in zip(symbols, quotes):
        if isinstance(px, Exception):
            continue
        p = paper_positions.get(symbol)
        if not p:
            continue
        age = (now - datetime.fromisoformat(p["entry_time"])).total_seconds() / 60
        if p["side"] == "LONG":
            if px <= p["stop_loss"]:
                close_position(symbol, px, "STOP_LOSS")
                continue
            if px >= p["take_profit"]:
                close_position(symbol, px, "TAKE_PROFIT")
                continue
        else:
            if px >= p["stop_loss"]:
                close_position(symbol, px, "STOP_LOSS")
                continue
            if px <= p["take_profit"]:
                close_position(symbol, px, "TAKE_PROFIT")
                continue
        if symbol in paper_positions and age >= MAX_TRADE_MINUTES:
            close_position(symbol, px, "TIME_EXIT")


async def marked_positions(client):
    symbols = list(paper_positions)
    if not symbols:
        return [], 0.0
    quotes = await asyncio.gather(*(price(client, symbol) for symbol in symbols), return_exceptions=True)
    out = []
    total_upnl = 0.0
    for symbol, px in zip(symbols, quotes):
        p = paper_positions.get(symbol)
        if not p:
            continue
        if isinstance(px, Exception):
            px = float(p.get("entry_market", p["entry_price"]))
        px = float(px)
        upnl = est_net_unit(p["side"], p["entry_price"], px) * p["qty"]
        total_upnl += upnl
        out.append({**p, "current_price": px, "unrealized_pnl": upnl})
    return out, total_upnl


async def cycle():
    async with cycle_lock:
        load_state()
        return await _cycle()


async def _cycle():
    global last_scan, last_signal, last_signals, last_scan_at
    async with httpx.AsyncClient() as client:
        if not last_scan or time.monotonic() - last_scan_at >= 60:
            last_scan = await build_scan(client)
            last_scan_at = time.monotonic()

        await manage_positions(client)

        opened_symbols = []
        if len(paper_positions) < MAX_OPEN_POSITIONS:
            watch = [row for row in last_scan if row["symbol"] not in paper_positions]
            signals = [s for s in await asyncio.gather(
                *(signal_for(client, row) for row in watch)
            ) if s]
            priority = {"EARLY_BREAKOUT": 3, "EARLY_MOMENTUM": 2}
            signals.sort(key=lambda x: (
                priority.get(x["setup"], 0),
                1 if x.get("trend_filter") == "ALIGNED_15M" else 0,
                x["volume_ratio"], abs(x["strength"]),
            ), reverse=True)
            last_signals = [dict(s) for s in signals[:10]]

            if signals:
                last_signal = signals[0]
                for sig in signals:
                    if len(paper_positions) >= MAX_OPEN_POSITIONS:
                        break
                    try:
                        market = await price(client, sig["symbol"])
                    except Exception:
                        continue
                    if open_position(sig, market):
                        opened_symbols.append(sig["symbol"])
            else:
                last_signal = {
                    "side": "WAIT",
                    "reason": (
                        "Čekám na časný 1m průraz. Jasný 15m trend musí souhlasit; "
                        "v neutrální 15m zóně stačí silnější 1m svíčka a objem."
                    ),
                }
        else:
            last_signal = {
                "side": "WAIT",
                "reason": f"Otevřeno {len(paper_positions)}/{MAX_OPEN_POSITIONS} pozic.",
            }
            last_signals = []

        positions_out, total_upnl = await marked_positions(client)
        primary = positions_out[0] if positions_out else None
        return {
            "bot": "V8 Candle Scanner",
            "mode": "PAPER",
            "balance": paper_balance,
            "equity": paper_balance + total_upnl,
            "unrealized_pnl": float(primary["unrealized_pnl"]) if primary else 0.0,
            "total_unrealized_pnl": total_upnl,
            "price": float(primary["current_price"]) if primary else None,
            "position": primary,
            "positions": positions_out,
            "open_positions": len(positions_out),
            "max_open_positions": MAX_OPEN_POSITIONS,
            "opened_this_cycle": opened_symbols,
            "signal": last_signal,
            "signals": last_signals,
            "scan": last_scan,
            "history": history,
            "cooldown_until": None,
            "cooldown_after_loss_min": 0,
            "history_persistent": state_loaded,
            "top_n": TOP_N,
            "all_symbols_tradable": True,
            "strategy_version": STRATEGY_VERSION,
            "entry_interval": ENTRY_INTERVAL,
            "breakout_lookback": BREAKOUT_LOOKBACK,
            "max_entry_deviation": MAX_ENTRY_DEVIATION,
            "max_trigger_extension": MAX_TRIGGER_EXTENSION,
            "trend_filter_mode": "adaptive_15m",
            "trend_neutral_strength": TREND_NEUTRAL_STRENGTH,
            "neutral_volume_ratio": NEUTRAL_VOLUME_RATIO,
            "neutral_body_ratio": NEUTRAL_BODY_RATIO,
            "enabled_setups": ["EARLY_BREAKOUT", "EARLY_MOMENTUM"],
            "risk_per_trade": RISK_PER_TRADE,
            "risk_reward": RISK_REWARD,
            "max_total_notional_share": MAX_TOTAL_NOTIONAL_SHARE,
            "time": datetime.now(timezone.utc).isoformat(),
        }


async def loop():
    while True:
        try:
            await cycle()
        except Exception as e:
            print("SCANNER LOOP ERROR", repr(e))
        await asyncio.sleep(SCAN_SECONDS)


@app.on_event("startup")
async def startup():
    global bot_task
    bot_task = asyncio.create_task(loop())


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "bot": "V8 Candle Scanner",
        "symbols": len(SYMBOLS),
        "strategy": "all coins + early 1m + adaptive 15m trend + multi-position",
        "rr": "1:2",
        "max_open_positions": MAX_OPEN_POSITIONS,
        "breakout_lookback": BREAKOUT_LOOKBACK,
        "trend_filter_mode": "adaptive_15m",
    }


@app.get("/analyze")
async def analyze():
    try:
        return JSONResponse(await cycle())
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return '''<!doctype html><html lang="cs"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>V8 Candle Scanner</title>
<style>body{margin:0;background:#07111f;color:#f4f7fb;font-family:system-ui}.w{max-width:920px;margin:auto;padding:18px}.card{background:#0f1b2d;border:1px solid #243650;border-radius:18px;padding:18px;margin:12px 0}.row{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}.big{font-size:34px;font-weight:800}.muted{color:#8ea1b8}.green{color:#21d19f}.red{color:#ff647c}.pos{padding:10px 0;border-bottom:1px solid #243650}@media(max-width:650px){.row{grid-template-columns:1fr}}</style></head>
<body><div class="w"><h1>V8 Candle Scanner</h1><div class="muted">Všechny coiny · EARLY 1m · adaptivní 15m filtr · více pozic · PAPER</div>
<div class="row"><div class="card"><div class="muted">BALANCE</div><div id="bal" class="big">-</div></div><div class="card"><div class="muted">EQUITY</div><div id="eq" class="big">-</div></div></div><div class="card"><h2>Aktuální pozice</h2><div id="pos">Načítám…</div></div></div>
<script>async function go(){let d=await (await fetch('/analyze')).json();bal.textContent=d.balance.toFixed(2)+' USDT';eq.textContent=d.equity.toFixed(2)+' USDT';pos.innerHTML=d.positions?.length?d.positions.map(p=>`<div class="pos"><b>${p.symbol}</b> <span class="${p.side==='LONG'?'green':'red'}">${p.side}</span> · ${p.setup} · ${p.trend_filter||''}<br>Entry ${p.entry_price.toFixed(5)} · Now ${p.current_price.toFixed(5)} · P/L <b class="${p.unrealized_pnl>=0?'green':'red'}">${p.unrealized_pnl.toFixed(2)} USDT</b></div>`).join(''):'Žádná otevřená pozice'}go();setInterval(go,15000)</script></body></html>'''
