import time
import httpx
from fastapi.responses import HTMLResponse
import app_v81_core as core

app = core.app
_original_dashboard = core.dashboard

# ============================================================
# MARKET-DATA SAFETY LAYER
# Binance may temporarily ban a shared Render egress IP with HTTP 418
# after rate-limit violations. During that ban, use Bybit public spot
# market data so the paper bot keeps running, and retry Binance later.
# ============================================================

_ORIGINAL_BINANCE_API = core.BINANCE_API
_BYBIT_API = "https://api.bybit.com"
_binance_blocked_until = 0.0

_INTERVAL_TO_BYBIT = {
    "1m": "1",
    "3m": "3",
    "5m": "5",
    "15m": "15",
    "30m": "30",
    "1h": "60",
    "2h": "120",
    "4h": "240",
    "6h": "360",
    "12h": "720",
    "1d": "D",
}

_INTERVAL_MS = {
    "1m": 60_000,
    "3m": 180_000,
    "5m": 300_000,
    "15m": 900_000,
    "30m": 1_800_000,
    "1h": 3_600_000,
    "2h": 7_200_000,
    "4h": 14_400_000,
    "6h": 21_600_000,
    "12h": 43_200_000,
    "1d": 86_400_000,
}


def _retry_after_seconds(response, default_seconds):
    raw = response.headers.get("Retry-After")
    try:
        value = float(raw) if raw else float(default_seconds)
    except (TypeError, ValueError):
        value = float(default_seconds)
    return max(float(default_seconds), min(value, 86_400.0))


async def _bybit_get(path, params=None):
    params = params or {}
    if core.http_client is None:
        raise RuntimeError("HTTP client not initialized")

    if path == "/api/v3/klines":
        interval = str(params.get("interval", "5m"))
        bybit_interval = _INTERVAL_TO_BYBIT.get(interval)
        if not bybit_interval:
            raise RuntimeError(f"Unsupported fallback interval: {interval}")

        symbol = str(params.get("symbol"))
        limit = int(params.get("limit", 100))
        response = await core.http_client.get(
            f"{_BYBIT_API}/v5/market/kline",
            params={
                "category": "spot",
                "symbol": symbol,
                "interval": bybit_interval,
                "limit": min(limit, 1000),
            },
        )
        response.raise_for_status()
        payload = response.json()
        if int(payload.get("retCode", -1)) != 0:
            raise RuntimeError(f"Bybit kline error: {payload.get('retMsg', 'unknown error')}")

        rows = payload.get("result", {}).get("list", []) or []
        rows = list(reversed(rows))  # Binance-style: oldest -> newest
        duration_ms = _INTERVAL_MS.get(interval, 300_000)

        converted = []
        for row in rows:
            start_ms = int(row[0])
            turnover = row[6] if len(row) > 6 else "0"
            converted.append([
                start_ms,
                row[1],  # open
                row[2],  # high
                row[3],  # low
                row[4],  # close
                row[5],  # volume
                start_ms + duration_ms - 1,
                turnover,
                0,
                "0",
                "0",
                "0",
            ])
        return converted

    if path == "/api/v3/ticker/price":
        symbol = str(params.get("symbol"))
        response = await core.http_client.get(
            f"{_BYBIT_API}/v5/market/tickers",
            params={"category": "spot", "symbol": symbol},
        )
        response.raise_for_status()
        payload = response.json()
        if int(payload.get("retCode", -1)) != 0:
            raise RuntimeError(f"Bybit ticker error: {payload.get('retMsg', 'unknown error')}")
        items = payload.get("result", {}).get("list", []) or []
        if not items:
            raise RuntimeError(f"Bybit ticker returned no data for {symbol}")
        return {"symbol": symbol, "price": items[0]["lastPrice"]}

    raise RuntimeError(f"No fallback mapping for Binance path: {path}")


async def resilient_market_get(path, params=None):
    global _binance_blocked_until

    if core.http_client is None:
        raise RuntimeError("HTTP client not initialized")

    now = time.monotonic()

    # While Binance's IP ban/rate-limit window is active, do not keep
    # hammering Binance. Go directly to the fallback provider.
    if now < _binance_blocked_until:
        return await _bybit_get(path, params)

    try:
        response = await core.http_client.get(
            f"{_ORIGINAL_BINANCE_API}{path}", params=params
        )

        if response.status_code in (418, 429):
            if response.status_code == 429:
                core.http_429_count += 1
            default_wait = 300 if response.status_code == 418 else 60
            wait_seconds = _retry_after_seconds(response, default_wait)
            _binance_blocked_until = time.monotonic() + wait_seconds
            core.last_error = (
                f"Binance HTTP {response.status_code}; "
                f"fallback Bybit active for {int(wait_seconds)}s"
            )
            return await _bybit_get(path, params)

        # Other temporary Binance/WAF/server failures also use fallback,
        # but only briefly so Binance can be retried automatically.
        if response.status_code in (403, 451) or response.status_code >= 500:
            _binance_blocked_until = time.monotonic() + 60
            core.last_error = (
                f"Binance HTTP {response.status_code}; temporary Bybit fallback"
            )
            return await _bybit_get(path, params)

        response.raise_for_status()
        return response.json()

    except (httpx.TimeoutException, httpx.NetworkError) as exc:
        _binance_blocked_until = time.monotonic() + 30
        core.last_error = f"Binance network error; Bybit fallback: {exc}"
        return await _bybit_get(path, params)


# Replace only the market-data transport. Strategy, risk, balance,
# open positions and database logic remain unchanged.
core.binance_get = resilient_market_get


# Keep the trading engine untouched. Only adjust dashboard presentation.
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

    # Distinguish closed trades from currently open positions.
    html = html.replace(
        "      ['Obchody',s.count||0],",
        "      ['Uzavřené obchody',s.count||0],\n"
        "      ['Otevřené pozice',Object.keys(d.open_positions||{}).length],",
    )

    # Direction colors: LONG = green, SHORT = red.
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

    return html
