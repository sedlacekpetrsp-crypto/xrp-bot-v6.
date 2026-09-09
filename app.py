from fastapi.responses import HTMLResponse
import app_v81_core as core

app = core.app
_original_dashboard = core.dashboard

# Keep the trading engine untouched. Only replace the dashboard GET / route
# so the counters clearly distinguish closed trades from live positions.
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
    old = "      ['Obchody',s.count||0],"
    new = (
        "      ['Uzavřené obchody',s.count||0],\n"
        "      ['Otevřené pozice',Object.keys(d.open_positions||{}).length],"
    )
    return html.replace(old, new)
