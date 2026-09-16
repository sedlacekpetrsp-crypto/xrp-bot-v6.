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

    unrealized_net = 0.0
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
        side = position["side"]
        gross = ((price - entry) if side == "LONG" else (entry - price)) * qty
        exit_exec = core.execute_exit_price(price, side)
        execution_gross = ((exit_exec - entry) if side == "LONG" else (entry - exit_exec)) * qty
        fees = (entry * qty + exit_exec * qty) * core.FEE_RATE
        net = execution_gross - fees
        costs = max(gross - net, 0.0)
        row["unrealized_gross_pnl"] = gross
        row["unrealized_net_pnl"] = net
        row["estimated_costs"] = costs
        unrealized_net += net

    data["unrealized_pnl"] = unrealized_net
    data["equity"] = float(data.get("paper_balance", 0.0)) + unrealized_net
    data["live_price_source"] = "BINANCE_SPOT"
    data["live_price_refresh_seconds"] = 3
    data["live_price_errors"] = live_errors
    return JSONResponse(data, headers={"Cache-Control": "no-store, no-cache, must-revalidate"})


@app.get("/", response_class=HTMLResponse)
async def dashboard_live():
    response = await _original_dashboard()
    body = response.body.decode("utf-8") if hasattr(response, "body") else str(response)
    old = "<span class='position-label'>Průběžný výsledek před poplatky</span><div class='position-result ${gross===null?'muted':cls(gross)}'>${gross===null?'Nedostupný':(gross>0?'+':'')+f(gross)+' USDT'}</div><p class='position-note'>Výsledek se mění s cenou. Do historie se obchod zapíše až při uzavření.</p>"
    new = "<span class='position-label'>Průběžný výsledek</span><div class='row'><span>Hrubý P/L</span><b class='${gross===null?'muted':cls(gross)}'>${gross===null?'Nedostupný':(gross>=0?'+':'')+f(gross)+' USDT'}</b></div><div class='row'><span>Čistý P/L</span><b class='${current===null?'muted':cls(d.symbols?.[p.symbol]?.unrealized_net_pnl)}'>${current===null?'Nedostupný':(Number(d.symbols?.[p.symbol]?.unrealized_net_pnl)>=0?'+':'')+f(d.symbols?.[p.symbol]?.unrealized_net_pnl)+' USDT'}</b></div><div class='row'><span>Odhad nákladů</span><span>${current===null?'—':f(d.symbols?.[p.symbol]?.estimated_costs)+' USDT'}</span></div><p class='position-note'>Hrubý P/L ukazuje samotný pohyb ceny. Čistý P/L zahrnuje simulované poplatky a slippage.</p>"
    body = body.replace(old, new)
    body = body.replace("setInterval(go,15000)", "setInterval(go,3000)")
    body = body.replace("setInterval(go,10000)", "setInterval(go,3000)")
    body = body.replace("setInterval(go,5000)", "setInterval(go,3000)")
    return HTMLResponse(body, headers={"Cache-Control": "no-store, no-cache, must-revalidate"})
