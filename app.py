import asyncio
import httpx
from fastapi.responses import HTMLResponse, JSONResponse
import app_v9 as core

app = core.app
_original_analyze = core.analyze
_original_dashboard = core.dashboard

# Trading logic is unchanged. This wrapper changes dashboard marking only.


async def _direct_binance_price(client, symbol):
    """Display quote from Binance Spot only; never substitute a stale candle."""
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
    symbols = list((data.get("open_positions") or {}).keys())
    live_errors = {}

    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(
            *[_direct_binance_price(client, s) for s in symbols],
            return_exceptions=True,
        )

    unrealized = 0.0
    for symbol, result in zip(symbols, results):
        position = data["open_positions"][symbol]
        if isinstance(result, Exception):
            live_errors[symbol] = str(result)
            data.setdefault("symbols", {}).setdefault(symbol, {})["live_price_ok"] = False
            continue

        price = float(result)
        row = data.setdefault("symbols", {}).setdefault(symbol, {})
        row["market_price"] = price
        row["live_price_ok"] = True
        row["price_source"] = "BINANCE_SPOT"
        entry = float(position["entry_price"])
        qty = float(position["qty"])
        unrealized += (price - entry) * qty if position["side"] == "LONG" else (entry - price) * qty

    data["equity"] = float(data.get("paper_balance", 0.0)) + unrealized
    data["live_price_source"] = "BINANCE_SPOT"
    data["live_price_refresh_seconds"] = 3
    data["live_price_errors"] = live_errors
    return JSONResponse(data, headers={"Cache-Control": "no-store, no-cache, must-revalidate"})


@app.get("/", response_class=HTMLResponse)
async def dashboard_live():
    response = await _original_dashboard()
    body = response.body.decode("utf-8") if hasattr(response, "body") else str(response)
    body = body.replace("setInterval(go,15000)", "setInterval(go,3000)")
    body = body.replace("setInterval(go,10000)", "setInterval(go,3000)")
    body = body.replace("setInterval(go,5000)", "setInterval(go,3000)")
    return HTMLResponse(body, headers={"Cache-Control": "no-store, no-cache, must-revalidate"})
