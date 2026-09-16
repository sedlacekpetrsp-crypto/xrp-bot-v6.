import asyncio
import time
import httpx
from fastapi.responses import HTMLResponse, JSONResponse
import app_v81_core as core
from fib_strategy import fib_pullback

app = core.app
_original_dashboard = core.dashboard
_original_analyze = core.analyze
_original_detect_setup = core.detect_setup

# V8.1: BREAKOUT + separately tagged confirmed Fibonacci pullback.
core.ENABLED_SETUPS = {"BREAKOUT", "FIB_0618_0786"}
core.MIN_VOLUME_BREAKOUT = 1.25
core.BREAKOUT_BODY_RATIO = 0.62
core.BREAKOUT_BUFFER_RATE = 0.0005
core.MIN_TREND_STRENGTH = 0.0010
core.POSITION_LOOP_SECONDS = 3
_CHOP_FLOOR = 0.00045


def detect_setup_with_fib(closed):
    base = _original_detect_setup(closed)
    # Preserve a valid breakout. FIB is an additional setup, never a replacement.
    if base.get("signal") in ("LONG", "SHORT") and base.get("setup") == "BREAKOUT":
        return base
    highs=[float(x[2]) for x in closed]; lows=[float(x[3]) for x in closed]
    closes=[float(x[4]) for x in closed]; volumes=[float(x[5]) for x in closed]
    fib=fib_pullback(highs,lows,closes,volumes,lookback=24,min_impulse_pct=0.006,min_volume_ratio=0.85)
    if not fib:
        return base
    cur=closed[-1]
    return {
        "signal":fib["signal"], "setup":"FIB_0618_0786",
        "reason":"FIB 0.618-0.786 pullback + rejection + volume potvrzen",
        "candle_time":int(cur[0]), "price_closed":float(cur[4]),
        "signal_high":float(cur[2]), "signal_low":float(cur[3]),
        "volume_ratio":fib["volume_ratio"], "fib_0618":fib["fib_0618"],
        "fib_0786":fib["fib_0786"], "swing_high":fib["swing_high"], "swing_low":fib["swing_low"],
    }

core.detect_setup = detect_setup_with_fib


def balanced_trend_filter(trend_closed, side):
    if len(trend_closed) < core.TREND_EMA_SLOW + 5:
        return False, "málo 15m dat", {}
    closes=[float(x[4]) for x in trend_closed]; close=closes[-1]
    fast=core.ema(closes[-80:],core.TREND_EMA_FAST); slow=core.ema(closes[-100:],core.TREND_EMA_SLOW)
    strength=abs(fast-slow)/max(close,1e-12)
    if fast>slow and close>slow: trend="LONG"
    elif fast<slow and close<slow: trend="SHORT"
    else: trend="MIXED"
    meta={"trend":trend if strength>=_CHOP_FLOOR else "CHOP","ema_fast":fast,"ema_slow":slow,"trend_strength":strength}
    if strength<_CHOP_FLOOR: return False,"15m chop - vstup blokován",meta
    if strength>=core.MIN_TREND_STRENGTH:
        ok=trend==side; return ok,("trend potvrzen" if ok else "signál proti 15m trendu"),meta
    if trend==side: return True,"mírný 15m trend potvrzen",meta
    return False,"slabý trend bez směrového potvrzení",meta

core.trend_filter=balanced_trend_filter

from market_data import market_get, market, install_data_health
install_data_health(app)
async def resilient_market_get(path,params=None):
    response=await market_get(core.http_client,core.BINANCE_API+path,params=params); return response.json()
core.binance_get=resilient_market_get

async def _direct_binance_price(client,symbol):
    last_exc=None
    for base in ("https://data-api.binance.vision","https://api.binance.com"):
        try:
            r=await client.get(base+"/api/v3/ticker/price",params={"symbol":symbol},timeout=5,headers={"Cache-Control":"no-cache"}); r.raise_for_status(); px=float(r.json()["price"])
            if px>0:return px
        except Exception as exc:last_exc=exc
    raise RuntimeError(f"Binance live ticker unavailable for {symbol}: {last_exc}")

app.router.routes[:]=[route for route in app.router.routes if not (getattr(route,"path",None) in ("/","/analyze") and "GET" in (getattr(route,"methods",set()) or set()))]

@app.get("/analyze")
async def analyze_live():
    data=await _original_analyze(); symbols=list(data.get("symbols") or []); live_errors={}
    async with httpx.AsyncClient() as client:
        results=await asyncio.gather(*[_direct_binance_price(client,s) for s in symbols],return_exceptions=True)
    unrealized_total=0.0
    for symbol,result in zip(symbols,results):
        row=data.setdefault("market",{}).setdefault(symbol,{})
        if isinstance(result,Exception): live_errors[symbol]=str(result); row["live_price_ok"]=False; continue
        px=float(result); row.update(price=px,live_price_ok=True,price_source="BINANCE_SPOT")
        p=row.get("position") or (data.get("open_positions") or {}).get(symbol); upnl=0.0
        if p: upnl=core.estimated_net_per_unit(p["side"],float(p["entry_price"]),px)*float(p["qty"])
        row["unrealized_pnl"]=upnl; unrealized_total+=upnl
    data["unrealized_pnl"]=unrealized_total; data["equity"]=float(data.get("paper_balance",0.0))+unrealized_total
    data["live_price_source"]="BINANCE_SPOT"; data["live_price_refresh_seconds"]=3; data["live_price_errors"]=live_errors
    data["enabled_setups"]=["BREAKOUT","FIB_0618_0786"]
    return JSONResponse(data,headers={"Cache-Control":"no-store, no-cache, must-revalidate"})

@app.get("/",response_class=HTMLResponse)
async def dashboard():
    html=await _original_dashboard()
    html=html.replace("      ['Obchody',s.count||0],","      ['Uzavřené obchody',s.count||0],\n      ['Otevřené pozice',Object.keys(d.open_positions||{}).length],")
    html=html.replace('<div class="row"><span>15m trend</span><span>${x.trend||\'—\'}</span></div>','<div class="row"><span>15m trend</span><b class="${x.trend===\'LONG\'?\'green\':x.trend===\'SHORT\'?\'red\':\'\'}">${x.trend||\'—\'}</b></div>')
    html=html.replace('<div class="row"><span>Pozice</span><span>${p?p.side:\'—\'}</span></div>','<div class="row"><span>Pozice</span><b class="${p?(p.side===\'LONG\'?\'green\':p.side===\'SHORT\'?\'red\':\'\'):\'\'}">${p?p.side:\'—\'}</b></div>')
    html=html.replace('<span>${t.side}</span>','<span class="${t.side===\'LONG\'?\'green\':t.side===\'SHORT\'?\'red\':\'\'}">${t.side}</span>')
    html=html.replace('setInterval(go,15000)','setInterval(go,3000)').replace('setInterval(refresh,15000)','setInterval(refresh,3000)').replace('setInterval(refresh,10000)','setInterval(refresh,3000)')
    return HTMLResponse(html,headers={"Cache-Control":"no-store, no-cache, must-revalidate"})
