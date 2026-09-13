import time
import httpx
from fastapi.responses import HTMLResponse
import app_v81_core as core

app = core.app
_original_dashboard = core.dashboard

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

app.router.routes[:] = [
    route for route in app.router.routes
    if not (
        getattr(route, "path", None) == "/"
        and "GET" in (getattr(route, "methods", set()) or set())
    )
]


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

    return html

