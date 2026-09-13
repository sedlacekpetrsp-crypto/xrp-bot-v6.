import asyncio
import time
import httpx
from fastapi.responses import HTMLResponse, JSONResponse
import app_v81_core as core

app = core.app
_original_dashboard = core.dashboard
_original_analyze = core.analyze

# ============================================================
# V8.1 CONTROLLED ENTRY TUNING
# Keep BREAKOUT-only strategy after the poor 279-trade mixed-setup sample.
# We only loosen the current breakout gate moderately; engulfing and pin bars
# remain disabled. Strong CHOP is still blocked.
# ============================================================

core.ENABLED_SETUPS = {"BREAKOUT"}
core.MIN_VOLUME_BREAKOUT = 1.25
core.BREAKOUT_BODY_RATIO = 0.62
core.BREAKOUT_BUFFER_RATE = 0.0005
core.MIN_TREND_STRENGTH = 0.0010
core.POSITION_LOOP_SECONDS = 3

_CHOP_FLOOR = 0.00045


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

    meta = {
        "trend": trend if strength >= _CHOP_FLOOR else "CHOP",
        "ema_fast": fast,
        "ema_slow": slow,
        "trend_strength": strength,
    }

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


async def _direct_binance_price(client, symbol):
    """Display quote from Binance Spot only. Never substitute Kraken/derived PnL."""
    last_exc = None
    for base in ("https://data-api.binance.vision", "https://api.binance.com"):
        try:
            r = await client.get(
                base + "/api/v3/ticker/price",
                params={"symbol": symbol},
                timeout=5,
                headers={"Cache-Control": "no-cache"},
            )
            r.raise_for_status()
            px = float(r.json()["price"])
            if px > 0:
                return px
        except Exception as exc:
            last_exc = exc
    raise RuntimeError(f"Binance live ticker unavailable for {symbol}: {last_exc}")


app.router.routes[:] = [
    route for route in app.router.routes
    if not (
        getattr(route, "path", None) in ("/", "/analyze")
        and "GET" in (getattr(route, "methods", set()) or set())
    )
]


@app.get("/analyze")
async def analyze_live():
    data = await _original_analyze()
    symbols = list(data.get("symbols") or [])
    live_errors = {}
    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(
            *[_direct_binance_price(client, s) for s in symbols],
            return_exceptions=True,
        )

    unrealized_total = 0.0
    for symbol, result in zip(symbols, results):
        market_row = data.setdefault("market", {}).setdefault(symbol, {})
        if isinstance(result, Exception):
            live_errors[symbol] = str(result)
            # Do not relabel a fallback/stale quote as live Binance data.
            market_row["live_price_ok"] = False
            continue

        px = float(result)
        market_row["price"] = px
        market_row["live_price_ok"] = True
        market_row["price_source"] = "BINANCE_SPOT"
        p = market_row.get("position") or (data.get("open_positions") or {}).get(symbol)
        upnl = 0.0
        if p:
            upnl = core.estimated_net_per_unit(
                p["side"], float(p["entry_price"]), px
            ) * float(p["qty"])
        market_row["unrealized_pnl"] = upnl
        unrealized_total += upnl

    data["unrealized_pnl"] = unrealized_total
    data["equity"] = float(data.get("paper_balance", 0.0)) + unrealized_total
    data["live_price_source"] = "BINANCE_SPOT"
    data["live_price_refresh_seconds"] = 3
    data["live_price_errors"] = live_errors
    return JSONResponse(data, headers={"Cache-Control": "no-store, no-cache, must-revalidate"})


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    html = await _original_dashboard()

    html = html.replace(
        "      ['Obchody',s.count||0],",
        "      ['Uzavřené obchody',s.count||0],\n"
        "      ['Otevřené pozice',Object.keys(d.open_positions||{}).length],",
    )

    html = html.replace(
        '<div class="row"><span>15m trend</span><span>${x.trend||\'—\'}</span></div>',
        '<div class="row"><span>15m trend</span><b class="${x.trend===\'LONG\'?\'green\':x.trend===\'SHORT\'?\'red\':\'\'}">${x.trend||\'—\'}</b></div>',
    )
    html = html.replace(
        '<div class="row"><span>Pozice</span><span>${p?p.side:\'—\'}</span></div>',
        '<div class="row"><span>Pozice</span><b class="${p?(p.side===\'LONG\'?\'green\':p.side===\'SHORT\'?\'red\':\'\'):\'\'}">${p?p.side:\'—\'}</b></div>',
    )
    html = html.replace(
        '<span>${t.side}</span>',
        '<span class="${t.side===\'LONG\'?\'green\':t.side===\'SHORT\'?\'red\':\'\'}">${t.side}</span>',
    )
    html = html.replace('setInterval(go,15000)', 'setInterval(go,3000)')
    html = html.replace('setInterval(refresh,15000)', 'setInterval(refresh,3000)')
    html = html.replace('setInterval(refresh,10000)', 'setInterval(refresh,3000)')

    return HTMLResponse(html, headers={"Cache-Control": "no-store, no-cache, must-revalidate"})
