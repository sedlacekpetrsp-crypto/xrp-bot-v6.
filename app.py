import asyncio
import time
import httpx
from fastapi.responses import HTMLResponse, JSONResponse
import app_v81_core as core
from fib_strategy import fib_pullback

app = core.app
_original_dashboard = core.dashboard
_original_analyze = core.analyze
_original_detect_setup = core.detect_setup
_original_strategy_analysis = core.strategy_analysis
_original_open_trade = core.open_trade
_original_close_trade = core.close_trade

# V8.1: BREAKOUT + separately tagged confirmed Fibonacci pullback.
core.ENABLED_SETUPS = {"BREAKOUT", "FIB_0618_0786"}
core.MIN_VOLUME_BREAKOUT = 1.25
core.BREAKOUT_BODY_RATIO = 0.62
core.BREAKOUT_BUFFER_RATE = 0.0005
core.MIN_TREND_STRENGTH = 0.0010
core.POSITION_LOOP_SECONDS = 3
_CHOP_FLOOR = 0.00045
SMART_TIME_GRACE_MINUTES = 5.0
SMART_TIME_MAX_EXTENSIONS = 3
SMART_TIME_MAX_SPREAD_PCT = 0.0008

# Fly confirmation is deliberately advisory only. It is recorded with each
# accepted V8.1 setup so we can later compare 5/8, 6/8, 7/8 and 8/8 results
# without changing V8.1's own entry logic.
FLY_CONFIRMATION_MODE = "ADVISORY_ONLY"
FLY_BOOK_LONG_MIN = 0.535
FLY_BOOK_SHORT_MAX = 0.465
FLY_MAX_SPREAD_PCT = 0.0008
FLY_MIN_VOLUME = 0.90


def _ema(values, period):
    if len(values) < period:
        return None
    alpha = 2.0 / (period + 1.0)
    value = sum(values[:period]) / period
    for x in values[period:]:
        value = alpha * x + (1.0 - alpha) * value
    return value


def _ema_series(values, period):
    if len(values) < period:
        return []
    alpha = 2.0 / (period + 1.0)
    out = [None] * (period - 1)
    value = sum(values[:period]) / period
    out.append(value)
    for x in values[period:]:
        value = alpha * x + (1.0 - alpha) * value
        out.append(value)
    return out


def _rsi_wilder(values, period=14):
    if len(values) < period + 2:
        return None
    gains, losses = [], []
    for i in range(1, period + 1):
        change = values[i] - values[i - 1]
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    for i in range(period + 1, len(values)):
        change = values[i] - values[i - 1]
        avg_gain = (avg_gain * (period - 1) + max(change, 0.0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-change, 0.0)) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - 100.0 / (1.0 + rs)


def _macd_hist(values):
    e12 = _ema_series(values, 12)
    e26 = _ema_series(values, 26)
    macd = [
        e12[i] - e26[i]
        for i in range(len(values))
        if i < len(e12) and i < len(e26) and e12[i] is not None and e26[i] is not None
    ]
    if len(macd) < 11:
        return None, None
    signal = _ema(macd, 9)
    previous_signal = _ema(macd[:-1], 9)
    current = macd[-1] - signal if signal is not None else None
    previous = macd[-2] - previous_signal if previous_signal is not None else None
    return current, previous


def _vwap(highs, lows, closes, volumes, window=120):
    n = min(window, len(closes))
    if n <= 0:
        return None
    total_volume = sum(volumes[-n:])
    if total_volume <= 0:
        return None
    return sum(
        ((h + l + c) / 3.0) * v
        for h, l, c, v in zip(highs[-n:], lows[-n:], closes[-n:], volumes[-n:])
    ) / total_volume


def _fly_confirmation(side, k1, depth):
    closed = k1[:-1]
    if len(closed) < 60:
        return {"available": False, "score": None, "max_score": 8, "reason": "málo 1m dat"}

    highs = [float(x[2]) for x in closed]
    lows = [float(x[3]) for x in closed]
    closes = [float(x[4]) for x in closed]
    volumes = [float(x[5]) for x in closed]
    hi, lo, cl = highs[-1], lows[-1], closes[-1]
    rng = max(hi - lo, 1e-12)
    bull = (cl - lo) / rng
    bear = (hi - cl) / rng
    e9, e21 = _ema(closes, 9), _ema(closes, 21)
    rsi = _rsi_wilder(closes)
    mh, mhp = _macd_hist(closes)
    vw = _vwap(highs, lows, closes, volumes)
    previous_volumes = volumes[-21:-1]
    avg_volume = sum(previous_volumes) / len(previous_volumes) if previous_volumes else 0.0
    volume_ratio = volumes[-1] / avg_volume if avg_volume > 0 else 0.0

    bids = depth.get("bids") or []
    asks = depth.get("asks") or []
    if bids and asks:
        bid_value = sum(float(p) * float(q) for p, q in bids)
        ask_value = sum(float(p) * float(q) for p, q in asks)
        imbalance = bid_value / max(bid_value + ask_value, 1e-12)
        best_bid = float(bids[0][0])
        best_ask = float(asks[0][0])
        mid = (best_bid + best_ask) / 2.0
        spread_pct = (best_ask - best_bid) / max(mid, 1e-12)
    else:
        imbalance = 0.5
        spread_pct = 1.0

    spread_ok = spread_pct <= FLY_MAX_SPREAD_PCT
    mac_up = mh is not None and (mh > 0 or (mhp is not None and mh > mhp))
    mac_down = mh is not None and (mh < 0 or (mhp is not None and mh < mhp))

    if side == "LONG":
        checks = {
            "ema9_ema21": bool(e9 is not None and e21 is not None and e9 > e21),
            "price_vs_ema9": bool(e9 is not None and cl > e9),
            "rsi": bool(rsi is not None and 40 <= rsi <= 70),
            "macd": bool(mac_up),
            "candle_close_strength": bool(bull >= 0.55),
            "volume": bool(volume_ratio >= FLY_MIN_VOLUME),
            "order_book": bool(spread_ok and imbalance >= FLY_BOOK_LONG_MIN),
            "vwap": bool(vw is not None and cl >= vw),
        }
    else:
        checks = {
            "ema9_ema21": bool(e9 is not None and e21 is not None and e9 < e21),
            "price_vs_ema9": bool(e9 is not None and cl < e9),
            "rsi": bool(rsi is not None and 30 <= rsi <= 60),
            "macd": bool(mac_down),
            "candle_close_strength": bool(bear >= 0.55),
            "volume": bool(volume_ratio >= FLY_MIN_VOLUME),
            "order_book": bool(spread_ok and imbalance <= FLY_BOOK_SHORT_MAX),
            "vwap": bool(vw is not None and cl <= vw),
        }

    return {
        "available": True,
        "score": sum(checks.values()),
        "max_score": 8,
        "mode": FLY_CONFIRMATION_MODE,
        "checks": checks,
        "metrics": {
            "rsi": rsi,
            "macd_hist": mh,
            "volume_ratio": volume_ratio,
            "book_imbalance": imbalance,
            "spread_pct": spread_pct,
            "vwap": vw,
            "close": cl,
        },
    }


def detect_setup_with_fib(closed):
    base = _original_detect_setup(closed)
    if base.get("signal") in ("LONG", "SHORT") and base.get("setup") == "BREAKOUT":
        return base
    highs = [float(x[2]) for x in closed]
    lows = [float(x[3]) for x in closed]
    closes = [float(x[4]) for x in closed]
    volumes = [float(x[5]) for x in closed]
    fib = fib_pullback(highs, lows, closes, volumes, lookback=24, min_impulse_pct=0.006, min_volume_ratio=0.85)
    if not fib:
        return base
    cur = closed[-1]
    return {
        "signal": fib["signal"], "setup": "FIB_0618_0786",
        "reason": "FIB 0.618-0.786 pullback + rejection + volume potvrzen",
        "candle_time": int(cur[0]), "price_closed": float(cur[4]),
        "signal_high": float(cur[2]), "signal_low": float(cur[3]),
        "volume_ratio": fib["volume_ratio"], "fib_0618": fib["fib_0618"],
        "fib_0786": fib["fib_0786"], "swing_high": fib["swing_high"], "swing_low": fib["swing_low"],
    }


core.detect_setup = detect_setup_with_fib


def balanced_trend_filter(trend_closed, side):
    if len(trend_closed) < core.TREND_EMA_SLOW + 5:
        return False, "málo 15m dat", {}
    closes = [float(x[4]) for x in trend_closed]
    close = closes[-1]
    fast = core.ema(closes[-80:], core.TREND_EMA_FAST)
    slow = core.ema(closes[-100:], core.TREND_EMA_SLOW)
    strength = abs(fast - slow) / max(close, 1e-12)
    if fast > slow and close > slow:
        trend = "LONG"
    elif fast < slow and close < slow:
        trend = "SHORT"
    else:
        trend = "MIXED"
    meta = {"trend": trend if strength >= _CHOP_FLOOR else "CHOP", "ema_fast": fast, "ema_slow": slow, "trend_strength": strength}
    if strength < _CHOP_FLOOR:
        return False, "15m chop - vstup blokován", meta
    if strength >= core.MIN_TREND_STRENGTH:
        ok = trend == side
        return ok, ("trend potvrzen" if ok else "signál proti 15m trendu"), meta
    if trend == side:
        return True, "mírný 15m trend potvrzen", meta
    return False, "slabý trend bez směrového potvrzení", meta


core.trend_filter = balanced_trend_filter

from market_data import market_get, market, install_data_health
install_data_health(app)


async def resilient_market_get(path, params=None):
    response = await market_get(core.http_client, core.BINANCE_API + path, params=params)
    return response.json()


core.binance_get = resilient_market_get


async def strategy_analysis_with_fly(symbol):
    analysis = await _original_strategy_analysis(symbol)
    side = analysis.get("signal")
    if side in ("LONG", "SHORT"):
        try:
            k1, depth = await asyncio.gather(
                core.get_klines(symbol, "1m", 140),
                core.binance_get("/api/v3/depth", {"symbol": symbol, "limit": 20}),
            )
            fly = _fly_confirmation(side, k1, depth)
        except Exception as exc:
            fly = {"available": False, "score": None, "max_score": 8, "mode": FLY_CONFIRMATION_MODE, "reason": str(exc)}
        analysis["fly_confirmation"] = fly
        analysis["fly_score"] = fly.get("score")
        analysis["fly_max_score"] = 8
        analysis["fly_confirmation_mode"] = FLY_CONFIRMATION_MODE
    return analysis


core.strategy_analysis = strategy_analysis_with_fly


def open_trade_with_fly(symbol, analysis, market_price):
    opened = _original_open_trade(symbol, analysis, market_price)
    if opened:
        position = core.positions.get(symbol)
        if position is not None:
            position["fly_score"] = analysis.get("fly_score")
            position["fly_max_score"] = 8
            position["fly_confirmation"] = analysis.get("fly_confirmation")
            position["fly_confirmation_mode"] = FLY_CONFIRMATION_MODE
            core.save_state()
    return opened


core.open_trade = open_trade_with_fly


def close_trade_with_fly(symbol, market_price, reason):
    position = core.positions.get(symbol)
    score = position.get("fly_score") if position else None
    if score is not None:
        reason = f"{reason} | FLY={score}/8"
    return _original_close_trade(symbol, market_price, reason)


core.close_trade = close_trade_with_fly


async def _direct_binance_price(client, symbol):
    last_exc = None
    for base in ("https://data-api.binance.vision", "https://api.binance.com"):
        try:
            r = await client.get(base + "/api/v3/ticker/price", params={"symbol": symbol}, timeout=5, headers={"Cache-Control": "no-cache"})
            r.raise_for_status()
            px = float(r.json()["price"])
            if px > 0:
                return px
        except Exception as exc:
            last_exc = exc
    raise RuntimeError(f"Binance live ticker unavailable for {symbol}: {last_exc}")


async def _smart_time_health(symbol, p, price):
    k5, k15, depth = await asyncio.gather(
        core.get_klines(symbol, "5m", 100),
        core.get_klines(symbol, "15m", 100),
        core.binance_get("/api/v3/depth", {"symbol": symbol, "limit": 20}),
    )
    c5 = [float(x[4]) for x in k5[:-1]]
    closed15 = k15[:-1]
    side = p["side"]
    trend_ok, _, _ = balanced_trend_filter(closed15, side)
    e9 = core.ema(c5[-40:], 9)
    e21 = core.ema(c5[-60:], 21)
    momentum_ok = (e9 > e21 and c5[-1] >= e9) if side == "LONG" else (e9 < e21 and c5[-1] <= e9)
    bids = depth.get("bids") or []
    asks = depth.get("asks") or []
    if bids and asks:
        bv = sum(float(x[0]) * float(x[1]) for x in bids)
        av = sum(float(x[0]) * float(x[1]) for x in asks)
        imb = bv / max(bv + av, 1e-12)
        bid = float(bids[0][0])
        ask = float(asks[0][0])
        spread = (ask - bid) / max((ask + bid) / 2, 1e-12)
    else:
        imb = .5
        spread = 1.0
    book_ok = imb >= .52 if side == "LONG" else imb <= .48
    entry = float(p["entry_market"])
    risk_market = max(abs(entry - float(p["stop_loss"])), entry * core.MIN_STOP_RATE)
    structure_ok = price >= entry - risk_market * .15 if side == "LONG" else price <= entry + risk_market * .15
    spread_ok = spread <= SMART_TIME_MAX_SPREAD_PCT
    return sum([trend_ok, momentum_ok, book_ok, structure_ok, spread_ok]), {
        "trend": trend_ok, "momentum": momentum_ok, "book": book_ok,
        "structure": structure_ok, "spread": spread_ok, "imbalance": imb, "spread_pct": spread,
    }


async def smart_manage_position(symbol):
    p = core.positions.get(symbol)
    if not p:
        return
    price = await core.get_live_price(symbol, max_age=1.0)
    side = p["side"]
    stop_loss = float(p["stop_loss"])
    take_profit = float(p["take_profit"])
    opened_at = core.datetime.fromisoformat(p["opened_at"])
    age = (core.utcnow() - opened_at).total_seconds() / 60
    current_net = core.estimated_net_per_unit(side, float(p["entry_price"]), price) * float(p["qty"])
    risk = float(p.get("risk_usdt", 0.0))
    if not p.get("breakeven_moved") and risk > 0 and current_net >= risk * core.BREAKEVEN_TRIGGER_R:
        p["stop_loss"] = core.target_market_for_net_profit(side, float(p["entry_price"]), 0.0)
        p["breakeven_moved"] = True
        stop_loss = float(p["stop_loss"])
        core.save_state()
    if (side == "LONG" and price <= stop_loss) or (side == "SHORT" and price >= stop_loss):
        core.close_trade(symbol, price, "BREAK EVEN" if p.get("breakeven_moved") else "STOP LOSS")
        return
    if (side == "LONG" and price >= take_profit) or (side == "SHORT" and price <= take_profit):
        core.close_trade(symbol, price, "TAKE PROFIT")
        return
    due = float(p.get("next_time_check_min", core.MAX_TRADE_MINUTES))
    if age < due:
        return
    health, meta = await _smart_time_health(symbol, p, price)
    extensions = int(p.get("time_extensions", 0))
    if health >= 3 and extensions < SMART_TIME_MAX_EXTENSIONS:
        p["time_extensions"] = extensions + 1
        p["next_time_check_min"] = age + SMART_TIME_GRACE_MINUTES
        p["last_time_health"] = health
        p["last_time_health_meta"] = meta
        core.save_state()
        print("SMART TIME EXTEND V8.1", symbol, health, "/5", p["time_extensions"])
        return
    core.close_trade(symbol, price, f"SMART TIME EXIT health={health}/5 ext={extensions}")


core.manage_position = smart_manage_position

app.router.routes[:] = [
    route for route in app.router.routes
    if not (getattr(route, "path", None) in ("/", "/analyze") and "GET" in (getattr(route, "methods", set()) or set()))
]


@app.get("/analyze")
async def analyze_live():
    data = await _original_analyze()
    symbols = list(data.get("symbols") or [])
    live_errors = {}
    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(*[_direct_binance_price(client, s) for s in symbols], return_exceptions=True)
    unrealized_total = 0.0
    for symbol, result in zip(symbols, results):
        row = data.setdefault("market", {}).setdefault(symbol, {})
        if isinstance(result, Exception):
            live_errors[symbol] = str(result)
            row["live_price_ok"] = False
            continue
        px = float(result)
        row.update(price=px, live_price_ok=True, price_source="BINANCE_SPOT")
        p = row.get("position") or (data.get("open_positions") or {}).get(symbol)
        upnl = gross = costs = 0.0
        if p:
            entry = float(p["entry_price"])
            qty = float(p["qty"])
            side = p["side"]
            gross = ((px - entry) if side == "LONG" else (entry - px)) * qty
            upnl = core.estimated_net_per_unit(side, entry, px) * qty
            costs = max(gross - upnl, 0.0)
        row["unrealized_gross_pnl"] = gross
        row["unrealized_pnl"] = upnl
        row["estimated_costs"] = costs
        unrealized_total += upnl
    data["unrealized_pnl"] = unrealized_total
    data["equity"] = float(data.get("paper_balance", 0.0)) + unrealized_total
    data["live_price_source"] = "BINANCE_SPOT"
    data["live_price_refresh_seconds"] = 3
    data["live_price_errors"] = live_errors
    data["enabled_setups"] = ["BREAKOUT", "FIB_0618_0786"]
    data["time_exit"] = "SMART"
    data["fly_confirmation_mode"] = FLY_CONFIRMATION_MODE
    return JSONResponse(data, headers={"Cache-Control": "no-store, no-cache, must-revalidate"})


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    html = await _original_dashboard()
    html = html.replace("      ['Obchody',s.count||0],", "      ['Uzavřené obchody',s.count||0],\n      ['Otevřené pozice',Object.keys(d.open_positions||{}).length],")
    html = html.replace('<div class="row"><span>15m trend</span><span>${x.trend||\'—\'}</span></div>', '<div class="row"><span>15m trend</span><b class="${x.trend===\'LONG\'?\'green\':x.trend===\'SHORT\'?\'red\':\'\'}">${x.trend||\'—\'}</b></div>')
    html = html.replace('<div class="row"><span>Pozice</span><span>${p?p.side:\'—\'}</span></div>', '<div class="row"><span>Pozice</span><b class="${p?(p.side===\'LONG\'?\'green\':p.side===\'SHORT\'?\'red\':\'\'):\'\'}">${p?p.side:\'—\'}</b></div>')
    html = html.replace('<div class="row"><span>uPnL net</span><span>${f(x.unrealized_pnl,2)}</span></div>', '<div class="row"><span>Hrubý P/L</span><b class="${Number(x.unrealized_gross_pnl)>=0?\'green\':\'red\'}">${Number(x.unrealized_gross_pnl)>=0?\'+\':\'\'}${f(x.unrealized_gross_pnl,2)} USDT</b></div><div class="row"><span>Čistý P/L</span><b class="${Number(x.unrealized_pnl)>=0?\'green\':\'red\'}">${Number(x.unrealized_pnl)>=0?\'+\':\'\'}${f(x.unrealized_pnl,2)} USDT</b></div><div class="row"><span>Odhad nákladů</span><span>${f(x.estimated_costs,2)} USDT</span></div>')
    html = html.replace('<span>${t.side}</span>', '<span class="${t.side===\'LONG\'?\'green\':t.side===\'SHORT\'?\'red\':\'\'}">${t.side}</span>')
    html = html.replace('setInterval(go,15000)', 'setInterval(go,3000)').replace('setInterval(refresh,15000)', 'setInterval(refresh,3000)').replace('setInterval(refresh,10000)', 'setInterval(refresh,3000)')
    return HTMLResponse(html, headers={"Cache-Control": "no-store, no-cache, must-revalidate"})
