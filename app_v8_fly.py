from fastapi.responses import HTMLResponse, JSONResponse
import app_v8 as base
import app_blue_whale_mirror as whale
from v8_fly_layer import install

install(base)
app = base.app
_original_analyze = base.analyze
_original_dashboard = base.dashboard
_whale_task = None

app.router.routes[:] = [
    route for route in app.router.routes
    if not (
        getattr(route, "path", None) in ("/", "/analyze")
        and "GET" in (getattr(route, "methods", set()) or set())
    )
]


@app.get("/analyze")
async def analyze_with_pnl_breakdown():
    data = await _original_analyze()
    p = data.get("position")
    gross = net = costs = 0.0
    if p:
        cached = base.price_cache.get(p["symbol"])
        if cached:
            px = float(cached["price"])
            entry = float(p["entry_price"])
            qty = float(p["qty"])
            side = p["side"]
            gross = ((px - entry) if side == "LONG" else (entry - px)) * qty
            net = base.estimated_net_per_unit(side, entry, px) * qty
            costs = max(gross - net, 0.0)
    data["unrealized_gross_pnl"] = gross
    data["unrealized_pnl"] = net
    data["estimated_costs"] = costs
    data["equity"] = float(data.get("paper_balance", 0.0)) + net
    return JSONResponse(data, headers={"Cache-Control": "no-store"})


@app.get("/", response_class=HTMLResponse)
async def dashboard_with_pnl_breakdown():
    html = await _original_dashboard()
    old = "const p=d.position; document.getElementById('position').innerHTML=p?`<b>${p.symbol} ${p.side}</b> • entry ${f(p.entry_price,6)} • SL ${f(p.stop_loss,6)} • TP ${f(p.take_profit,6)} • uPnL ${f(d.unrealized_pnl,2)}`:'Žádná otevřená pozice';"
    new = "const p=d.position; document.getElementById('position').innerHTML=p?`<b>${p.symbol} ${p.side}</b> • entry ${f(p.entry_price,6)} • SL ${f(p.stop_loss,6)} • TP ${f(p.take_profit,6)}<br>Hrubý P/L <b class=\"${Number(d.unrealized_gross_pnl)>=0?'green':'red'}\">${Number(d.unrealized_gross_pnl)>=0?'+':''}${f(d.unrealized_gross_pnl,2)} USDC</b> • Čistý P/L <b class=\"${Number(d.unrealized_pnl)>=0?'green':'red'}\">${Number(d.unrealized_pnl)>=0?'+':''}${f(d.unrealized_pnl,2)} USDC</b> • Náklady ${f(d.estimated_costs,2)} USDC`:'Žádná otevřená pozice';"
    html = html.replace(old, new)
    html = html.replace("setInterval(refresh,10000)", "setInterval(refresh,3000)")
    return HTMLResponse(html, headers={"Cache-Control": "no-store"})


@app.on_event("startup")
async def start_whale_worker():
    global _whale_task
    whale.init_persistence()
    if _whale_task is None or _whale_task.done():
        _whale_task = __import__("asyncio").create_task(whale.bot_loop())

@app.get("/whale/status")
async def whale_status():
    return JSONResponse(whale.state, headers={"Cache-Control":"no-store"})

@app.get("/combined/health")
async def combined_health():
    return JSONResponse({
        "ok": True,
        "fly": {
            "last_cycle_at": getattr(base, "last_cycle_at", None),
            "last_error": getattr(base, "last_error", None),
            "balance": getattr(base, "PAPER_BALANCE", None),
            "open_position": getattr(base, "paper_position", None),
        },
        "whale": {
            "status": whale.state.get("status"),
            "error": whale.state.get("error"),
            "last_scan": whale.state.get("last_scan"),
            "persistence": whale.state.get("persistence"),
            "persistence_error": whale.state.get("persistence_error"),
            "balance": whale.state.get("balance"),
            "open_position": whale.state.get("open_position"),
        }
    }, headers={"Cache-Control":"no-store"})
