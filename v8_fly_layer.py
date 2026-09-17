from datetime import datetime, timezone
from fastapi.responses import HTMLResponse, JSONResponse
import v8_fly_layer_core as core
from v8_fly_layer_core import *
import v10_precision_bot as v10
import v11_evidence_bot as v11

# Runtime guard for V11 build 2: override the UTC helper so a stale typo cannot stop the loop.
v11.now = lambda: datetime.now(timezone.utc)


def install(module):
    core.install(module)
    original_analyze = module.analyze
    original_dashboard = module.dashboard
    original_startup = module.startup
    original_shutdown = module.shutdown

    async def combined_startup():
        await original_startup()
        try:
            if not v10.bot_task or v10.bot_task.done():
                await v10.startup()
            print("V10_PRECISION_STARTED", v10.BUILD, flush=True)
        except Exception as exc:
            print("V10_PRECISION_START_FAILED", repr(exc), flush=True)
        try:
            if not v11.bot_task or v11.bot_task.done():
                await v11.startup()
            print("V11_EVIDENCE_STARTED", v11.BUILD, flush=True)
        except Exception as exc:
            print("V11_EVIDENCE_START_FAILED", repr(exc), flush=True)

    async def combined_shutdown():
        try:
            await v11.shutdown()
        except Exception as exc:
            print("V11_EVIDENCE_SHUTDOWN_FAILED", repr(exc), flush=True)
        try:
            await v10.shutdown()
        except Exception as exc:
            print("V10_PRECISION_SHUTDOWN_FAILED", repr(exc), flush=True)
        await original_shutdown()

    module.startup = combined_startup
    module.shutdown = combined_shutdown

    module.app.router.routes[:] = [
        route for route in module.app.router.routes
        if not (
            getattr(route, "path", None) in ("/", "/analyze")
            and "GET" in (getattr(route, "methods", set()) or set())
        )
    ]

    @module.app.get("/analyze")
    async def analyze_with_pnl_breakdown():
        data = await original_analyze()
        p = data.get("position")
        gross = net = costs = 0.0
        if p:
            cached = module.price_cache.get(p["symbol"])
            if cached:
                px = float(cached["price"])
                entry = float(p["entry_price"])
                qty = float(p["qty"])
                side = p["side"]
                gross = ((px - entry) if side == "LONG" else (entry - px)) * qty
                net = module.estimated_net_per_unit(side, entry, px) * qty
                costs = max(gross - net, 0.0)
        data["unrealized_gross_pnl"] = gross
        data["unrealized_pnl"] = net
        data["estimated_costs"] = costs
        data["equity"] = float(data.get("paper_balance", 0.0)) + net
        data["v10_precision"] = {
            "build": v10.BUILD,
            "running": bool(v10.bot_task and not v10.bot_task.done()),
            "last_cycle_at": v10.last_cycle_at,
            "error": v10.last_error,
            "dashboard": "/v10/",
        }
        data["v11_evidence"] = {
            "build": v11.BUILD,
            "running": bool(v11.bot_task and not v11.bot_task.done()),
            "last_cycle_at": v11.LAST_CYCLE,
            "error": v11.ERR,
            "dashboard": "/v11/",
            "validation": v11.snapshot().get("validation"),
        }
        return JSONResponse(data, headers={"Cache-Control": "no-store"})

    @module.app.get("/", response_class=HTMLResponse)
    async def dashboard_with_pnl_breakdown():
        html = await original_dashboard()
        old = "const p=d.position; document.getElementById('position').innerHTML=p?`<b>${p.symbol} ${p.side}</b> • entry ${f(p.entry_price,6)} • SL ${f(p.stop_loss,6)} • TP ${f(p.take_profit,6)} • uPnL ${f(d.unrealized_pnl,2)}`:'Žádná otevřená pozice';"
        new = "const p=d.position; document.getElementById('position').innerHTML=p?`<b>${p.symbol} ${p.side}</b> • entry ${f(p.entry_price,6)} • SL ${f(p.stop_loss,6)} • TP ${f(p.take_profit,6)}<br>Hrubý P/L <b class=\"${Number(d.unrealized_gross_pnl)>=0?'green':'red'}\">${Number(d.unrealized_gross_pnl)>=0?'+':''}${f(d.unrealized_gross_pnl,2)} USDC</b> • Čistý P/L <b class=\"${Number(d.unrealized_pnl)>=0?'green':'red'}\">${Number(d.unrealized_pnl)>=0?'+':''}${f(d.unrealized_pnl,2)} USDC</b> • Náklady ${f(d.estimated_costs,2)} USDC`:'Žádná otevřená pozice';"
        html = html.replace(old, new)
        html = html.replace("setInterval(refresh,10000)", "setInterval(refresh,3000)")
        html = html.replace("</body>", '<div style="max-width:900px;margin:16px auto;padding:0 16px"><a href="v10/" style="color:#8ea1b8;font-weight:700;margin-right:16px">V10 Precision XRP →</a><a href="v11/" style="color:#21d19f;font-weight:800">V11 Evidence XRP →</a></div></body>')
        return HTMLResponse(html, headers={"Cache-Control": "no-store"})

    module.app.mount("/v10", v10.app)
    module.app.mount("/v11", v11.app)
