import asyncio
import httpx
from fastapi.responses import HTMLResponse, JSONResponse
import app_v9 as core

app = core.app
_original_analyze = core.analyze
_original_dashboard = core.dashboard
_original_analyze_symbol = core.analyze_symbol
_original_open_position = core.open_position
_original_close_position = core.close_position

# Fly confirmation is advisory only. V9 still decides entries with its own
# Best-Of logic; the Fly score is attached for later 5/8-8/8 performance review.
FLY_CONFIRMATION_MODE = "ADVISORY_ONLY"
FLY_BOOK_LONG_MIN = 0.535
FLY_BOOK_SHORT_MAX = 0.465
FLY_MAX_SPREAD_PCT = 0.0008
FLY_MIN_VOLUME = 0.90


def _ema(values, period):
    if len(values) < period:
        return None
    a = 2.0 / (period + 1.0)
    value = sum(values[:period]) / period
    for x in values[period:]:
        value = a * x + (1.0 - a) * value
    return value


def _ema_series(values, period):
    if len(values) < period:
        return []
    a = 2.0 / (period + 1.0)
    out = [None] * (period - 1)
    value = sum(values[:period]) / period
    out.append(value)
    for x in values[period:]:
        value = a * x + (1.0 - a) * value
        out.append(value)
    return out


def _rsi(values, period=14):
    if len(values) < period + 2:
        return None
    gains, losses = [], []
    for i in range(1, period + 1):
        d = values[i] - values[i - 1]
        gains.append(max(d, 0.0)); losses.append(max(-d, 0.0))
    ag = sum(gains) / period; al = sum(losses) / period
    for i in range(period + 1, len(values)):
        d = values[i] - values[i - 1]
        ag = (ag * (period - 1) + max(d, 0.0)) / period
        al = (al * (period - 1) + max(-d, 0.0)) / period
    if al == 0:
        return 100.0
    rs = ag / al
    return 100.0 - 100.0 / (1.0 + rs)


def _macd_hist(values):
    e12, e26 = _ema_series(values, 12), _ema_series(values, 26)
    macd = [e12[i] - e26[i] for i in range(len(values)) if i < len(e12) and i < len(e26) and e12[i] is not None and e26[i] is not None]
    if len(macd) < 11:
        return None, None
    s = _ema(macd, 9); sp = _ema(macd[:-1], 9)
    return (macd[-1] - s if s is not None else None, macd[-2] - sp if sp is not None else None)


def _vwap(highs, lows, closes, volumes, window=120):
    n = min(window, len(closes))
    if n <= 0:
        return None
    total = sum(volumes[-n:])
    if total <= 0:
        return None
    return sum(((h + l + c) / 3.0) * v for h, l, c, v in zip(highs[-n:], lows[-n:], closes[-n:], volumes[-n:])) / total


async def _depth(symbol):
    return await core.api_get("/api/v3/depth", {"symbol": symbol, "limit": 20})


def _fly_confirmation(side, k1, depth):
    closed = k1[:-1]
    if len(closed) < 60:
        return {"available": False, "score": None, "max_score": 8, "mode": FLY_CONFIRMATION_MODE, "reason": "málo 1m dat"}
    h = [float(x[2]) for x in closed]; l = [float(x[3]) for x in closed]
    c = [float(x[4]) for x in closed]; v = [float(x[5]) for x in closed]
    hi, lo, cl = h[-1], l[-1], c[-1]
    rng = max(hi - lo, 1e-12); bull = (cl - lo) / rng; bear = (hi - cl) / rng
    e9, e21 = _ema(c, 9), _ema(c, 21); rsi = _rsi(c); mh, mhp = _macd_hist(c); vw = _vwap(h, l, c, v)
    pv = v[-21:-1]; avg = sum(pv) / len(pv) if pv else 0.0; vr = v[-1] / avg if avg > 0 else 0.0
    bids = depth.get("bids") or []; asks = depth.get("asks") or []
    if bids and asks:
        bv = sum(float(p) * float(q) for p, q in bids); av = sum(float(p) * float(q) for p, q in asks)
        imb = bv / max(bv + av, 1e-12); bid = float(bids[0][0]); ask = float(asks[0][0]); mid = (bid + ask) / 2.0
        spread = (ask - bid) / max(mid, 1e-12)
    else:
        imb, spread = 0.5, 1.0
    mac_up = mh is not None and (mh > 0 or (mhp is not None and mh > mhp))
    mac_dn = mh is not None and (mh < 0 or (mhp is not None and mh < mhp))
    spread_ok = spread <= FLY_MAX_SPREAD_PCT
    if side == "LONG":
        checks = {
            "ema9_ema21": bool(e9 is not None and e21 is not None and e9 > e21),
            "price_vs_ema9": bool(e9 is not None and cl > e9),
            "rsi": bool(rsi is not None and 40 <= rsi <= 70),
            "macd": bool(mac_up),
            "candle_close_strength": bool(bull >= 0.55),
            "volume": bool(vr >= FLY_MIN_VOLUME),
            "order_book": bool(spread_ok and imb >= FLY_BOOK_LONG_MIN),
            "vwap": bool(vw is not None and cl >= vw),
        }
    else:
        checks = {
            "ema9_ema21": bool(e9 is not None and e21 is not None and e9 < e21),
            "price_vs_ema9": bool(e9 is not None and cl < e9),
            "rsi": bool(rsi is not None and 30 <= rsi <= 60),
            "macd": bool(mac_dn),
            "candle_close_strength": bool(bear >= 0.55),
            "volume": bool(vr >= FLY_MIN_VOLUME),
            "order_book": bool(spread_ok and imb <= FLY_BOOK_SHORT_MAX),
            "vwap": bool(vw is not None and cl <= vw),
        }
    return {
        "available": True, "score": sum(checks.values()), "max_score": 8,
        "mode": FLY_CONFIRMATION_MODE, "checks": checks,
        "metrics": {"rsi": rsi, "macd_hist": mh, "volume_ratio": vr, "book_imbalance": imb, "spread_pct": spread, "vwap": vw, "close": cl},
    }


async def analyze_symbol_with_fly(symbol):
    analysis = await _original_analyze_symbol(symbol)
    side = analysis.get("signal")
    if side in ("LONG", "SHORT"):
        try:
            k1, depth = await asyncio.gather(core.klines(symbol, "1m", 140), _depth(symbol))
            fly = _fly_confirmation(side, k1, depth)
        except Exception as exc:
            fly = {"available": False, "score": None, "max_score": 8, "mode": FLY_CONFIRMATION_MODE, "reason": str(exc)}
        analysis["fly_confirmation"] = fly
        analysis["fly_score"] = fly.get("score")
        analysis["fly_max_score"] = 8
        analysis["fly_confirmation_mode"] = FLY_CONFIRMATION_MODE
        core.last_analysis[symbol] = analysis
    return analysis


core.analyze_symbol = analyze_symbol_with_fly


def open_position_with_fly(symbol, analysis, market, atr_value):
    opened = _original_open_position(symbol, analysis, market, atr_value)
    if opened:
        p = core.positions.get(symbol)
        if p is not None:
            p["fly_score"] = analysis.get("fly_score")
            p["fly_max_score"] = 8
            p["fly_confirmation"] = analysis.get("fly_confirmation")
            p["fly_confirmation_mode"] = FLY_CONFIRMATION_MODE
            core.save_state()
    return opened


core.open_position = open_position_with_fly


def close_position_with_fly(symbol, market, reason):
    p = core.positions.get(symbol)
    score = p.get("fly_score") if p else None
    if score is not None:
        reason = f"{reason} | FLY={score}/8"
    return _original_close_position(symbol, market, reason)


core.close_position = close_position_with_fly


async def _direct_binance_price(client, symbol):
    last_exc = None
    for base in ("https://data-api.binance.vision", "https://api.binance.com"):
        try:
            r = await client.get(base + "/api/v3/ticker/price", params={"symbol": symbol}, timeout=5, headers={"Cache-Control": "no-cache"})
            r.raise_for_status(); px = float(r.json()["price"])
            if px > 0:
                return px
        except Exception as exc:
            last_exc = exc
    raise RuntimeError(f"Binance live ticker unavailable for {symbol}: {last_exc}")


app.router.routes[:] = [route for route in app.router.routes if not (getattr(route, "path", None) in ("/", "/analyze") and "GET" in (getattr(route, "methods", set()) or set()))]


@app.get("/analyze")
async def analyze_live():
    data = await _original_analyze()
    symbols = list((data.get("open_positions") or {}).keys())
    live_errors = {}
    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(*[_direct_binance_price(client, s) for s in symbols], return_exceptions=True)
    unrealized_net = 0.0
    for symbol, result in zip(symbols, results):
        position = data["open_positions"][symbol]
        if isinstance(result, Exception):
            live_errors[symbol] = str(result)
            data.setdefault("symbols", {}).setdefault(symbol, {})["live_price_ok"] = False
            continue
        price = float(result); row = data.setdefault("symbols", {}).setdefault(symbol, {})
        row["market_price"] = price; row["live_price_ok"] = True; row["price_source"] = "BINANCE_SPOT"
        entry = float(position["entry_price"]); qty = float(position["qty"]); side = position["side"]
        gross = ((price - entry) if side == "LONG" else (entry - price)) * qty
        exit_exec = core.execute_exit_price(price, side)
        execution_gross = ((exit_exec - entry) if side == "LONG" else (entry - exit_exec)) * qty
        fees = (entry * qty + exit_exec * qty) * core.FEE_RATE
        net = execution_gross - fees; costs = max(gross - net, 0.0)
        row["unrealized_gross_pnl"] = gross; row["unrealized_net_pnl"] = net; row["estimated_costs"] = costs
        unrealized_net += net
    data["unrealized_pnl"] = unrealized_net
    data["equity"] = float(data.get("paper_balance", 0.0)) + unrealized_net
    data["live_price_source"] = "BINANCE_SPOT"; data["live_price_refresh_seconds"] = 3
    data["live_price_errors"] = live_errors; data["fly_confirmation_mode"] = FLY_CONFIRMATION_MODE
    return JSONResponse(data, headers={"Cache-Control": "no-store, no-cache, must-revalidate"})


@app.get("/", response_class=HTMLResponse)
async def dashboard_live():
    response = await _original_dashboard()
    body = response.body.decode("utf-8") if hasattr(response, "body") else str(response)
    old = "<span class='position-label'>Průběžný výsledek před poplatky</span><div class='position-result ${gross===null?'muted':cls(gross)}'>${gross===null?'Nedostupný':(gross>0?'+':'')+f(gross)+' USDT'}</div><p class='position-note'>Výsledek se mění s cenou. Do historie se obchod zapíše až při uzavření.</p>"
    new = "<span class='position-label'>Průběžný výsledek</span><div class='row'><span>Hrubý P/L</span><b class='${gross===null?'muted':cls(gross)}'>${gross===null?'Nedostupný':(gross>=0?'+':'')+f(gross)+' USDT'}</b></div><div class='row'><span>Čistý P/L</span><b class='${current===null?'muted':cls(d.symbols?.[p.symbol]?.unrealized_net_pnl)}'>${current===null?'Nedostupný':(Number(d.symbols?.[p.symbol]?.unrealized_net_pnl)>=0?'+':'')+f(d.symbols?.[p.symbol]?.unrealized_net_pnl)+' USDT'}</b></div><div class='row'><span>Odhad nákladů</span><span>${current===null?'—':f(d.symbols?.[p.symbol]?.estimated_costs)+' USDT'}</span></div><p class='position-note'>Hrubý P/L ukazuje samotný pohyb ceny. Čistý P/L zahrnuje simulované poplatky a slippage.</p>"
    body = body.replace(old, new)
    body = body.replace("setInterval(go,15000)", "setInterval(go,3000)").replace("setInterval(go,10000)", "setInterval(go,3000)").replace("setInterval(go,5000)", "setInterval(go,3000)")
    return HTMLResponse(body, headers={"Cache-Control": "no-store, no-cache, must-revalidate"})
