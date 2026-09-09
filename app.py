from fastapi.responses import HTMLResponse
import app_v81_core as core

app = core.app
_original_dashboard = core.dashboard

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
