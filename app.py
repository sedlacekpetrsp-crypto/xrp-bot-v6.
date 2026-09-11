import time
import httpx
from fastapi.responses import HTMLResponse
import app_v81_core as core

app = core.app
_original_dashboard = core.dashboard

# ============================================================
# MARKET-DATA SAFETY LAYER
# Binance may temporarily ban a shared Render egress IP with HTTP 418.
# Render/Oregon can also be geo-blocked by Bybit. Therefore the fallback
# provider here is Kraken public market data, which is available in the US.
# Strategy, balance, positions and DB logic stay unchanged.
# ============================================================

_ORIGINAL_BINANCE_API = core.BINANCE_API
_KRAKEN_API = "https://api.kraken.com"
_binance_blocked_until = 0.0

# Kraken uses XBT for bitcoin in REST pair names.
_KRAKEN_SYMBOLS = {
    "XRPUSDT": "XRPUSDT",
    "BTCUSDT": "XBTUSDT",
    "ETHUSDT": "ETHUSDT",
    "SOLUSDT": "SOLUSDT",
}

_KRAKEN_INTERVALS = {
    "1m": 1,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "1h": 60,
    "4h": 240,
    "1d": 1440,
}

_INTERVAL_MS = {
    "1m": 60_000,
    "5m": 300_000,
    "15m": 900_000,
    "30m": 1_800_000,
    "1h": 3_600_000,
    "4h": 14_400_000,
    "1d": 86_400_000,
}


def _retry_after_seconds(response, default_seconds):
    raw = response.headers.get("Retry-After")
    try:
        value = float(raw) if raw else float(default_seconds)
    except (TypeError, ValueError):
        value = float(default_seconds)
    return max(float(default_seconds), min(value, 86_400.0))


async def _kraken_get(path, params=None):
    params = params or {}
    if core.http_client is None:
        raise RuntimeError("HTTP client not initialized")

    symbol = str(params.get("symbol", ""))
    pair = _KRAKEN_SYMBOLS.get(symbol)
    if not pair:
        raise RuntimeError(f"Unsupported Kraken fallback symbol: {symbol}")

    if path == "/api/v3/klines":
        interval = str(params.get("interval", "5m"))
        kraken_interval = _KRAKEN_INTERVALS.get(interval)
        if kraken_interval is None:
            raise RuntimeError(f"Unsupported Kraken fallback interval: {interval}")

        limit = max(2, int(params.get("limit", 100)))
        response = await core.http_client.get(
            f"{_KRAKEN_API}/0/public/OHLC",
            params={"pair": pair, "interval": kraken_interval},
        )
        response.raise_for_status()
        payload = response.json()
        errors = payload.get("error") or []
        if errors:
            raise RuntimeError(f"Kraken OHLC error: {errors}")

        result = payload.get("result") or {}
        data_key = next((k for k in result.keys() if k != "last"), None)
        if not data_key:
            raise RuntimeError(f"Kraken OHLC returned no data for {pair}")

        rows = result.get(data_key) or []
        rows = rows[-limit:]
        duration_ms = _INTERVAL_MS.get(interval, 300_000)

        converted = []
        for row in rows:
            # Kraken OHLC: time, open, high, low, close, vwap, volume, count
            start_ms = int(float(row[0]) * 1000)
            converted.append([
                start_ms,
                str(row[1]),
                str(row[2]),
                str(row[3]),
                str(row[4]),
                str(row[6]),
                start_ms + duration_ms - 1,
                "0",
                int(row[7]) if len(row) > 7 else 0,
                "0",
                "0",
                "0",
            ])
        return converted

    if path == "/api/v3/ticker/price":
        response = await core.http_client.get(
            f"{_KRAKEN_API}/0/public/Ticker",
            params={"pair": pair},
        )
        response.raise_for_status()
        payload = response.json()
        errors = payload.get("error") or []
        if errors:
            raise RuntimeError(f"Kraken ticker error: {errors}")

        result = payload.get("result") or {}
        if not result:
            raise RuntimeError(f"Kraken ticker returned no data for {pair}")
        ticker = next(iter(result.values()))
        price = ticker.get("c", [None])[0]
        if price is None:
            raise RuntimeError(f"Kraken ticker has no last price for {pair}")
        return {"symbol": symbol, "price": str(price)}

    raise RuntimeError(f"No Kraken fallback mapping for Binance path: {path}")


async def resilient_market_get(path, params=None):
    global _binance_blocked_until

    if core.http_client is None:
        raise RuntimeError("HTTP client not initialized")

    now = time.monotonic()

    # During the Binance ban window, do not keep hitting Binance.
    if now < _binance_blocked_until:
        return await _kraken_get(path, params)

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
                f"Kraken fallback active for {int(wait_seconds)}s"
            )
            return await _kraken_get(path, params)

        if response.status_code in (403, 451) or response.status_code >= 500:
            _binance_blocked_until = time.monotonic() + 60
            core.last_error = (
                f"Binance HTTP {response.status_code}; temporary Kraken fallback"
            )
            return await _kraken_get(path, params)

        response.raise_for_status()
        return response.json()

    except (httpx.TimeoutException, httpx.NetworkError) as exc:
        _binance_blocked_until = time.monotonic() + 30
        core.last_error = f"Binance network error; Kraken fallback: {exc}"
        return await _kraken_get(path, params)


# Replace only market-data transport.
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

    return html
