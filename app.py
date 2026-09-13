from fastapi.responses import HTMLResponse, JSONResponse
import app_v9 as core

app = core.app
_original_analyze = core.analyze
_original_dashboard = core.dashboard

# Technical refresh only: strategy, entries, SL/TP and risk remain unchanged.
core.POSITION_LOOP_SECONDS = 3

# Replace only the public analyze/dashboard GET routes so open-position prices
# are marked from a fresh ticker instead of waiting for the slower strategy scan.
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
    unrealized = 0.0
    for symbol, position in (data.get("open_positions") or {}).items():
        try:
            price = await core.live_price(symbol)
            data.setdefault("symbols", {}).setdefault(symbol, {})["market_price"] = price
            entry = float(position["entry_price"])
            qty = float(position["qty"])
            pnl = (price - entry) * qty if position["side"] == "LONG" else (entry - price) * qty
            unrealized += pnl
        except Exception:
            # Keep the last known value if the live quote provider is temporarily unavailable.
            raw = data.get("symbols", {}).get(symbol, {}).get("market_price")
            if raw is not None:
                entry = float(position["entry_price"])
                qty = float(position["qty"])
                price = float(raw)
                unrealized += (price - entry) * qty if position["side"] == "LONG" else (entry - price) * qty
    data["equity"] = float(data.get("paper_balance", 0.0)) + unrealized
    data["live_price_refresh_seconds"] = 3
    return JSONResponse(data, headers={"Cache-Control": "no-store"})


@app.get("/", response_class=HTMLResponse)
async def dashboard_live():
    response = await _original_dashboard()
    body = response.body.decode("utf-8") if hasattr(response, "body") else str(response)
    body = body.replace("setInterval(go,15000)", "setInterval(go,3000)")
    body = body.replace("setInterval(go,10000)", "setInterval(go,3000)")
    body = body.replace("setInterval(go,5000)", "setInterval(go,3000)")
    return HTMLResponse(body, headers={"Cache-Control": "no-store"})
