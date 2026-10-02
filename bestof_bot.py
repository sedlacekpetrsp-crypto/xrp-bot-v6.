"""
BEST-OF PAPER 24/7
Built from the profitable historical setup/symbol/direction buckets only.
Historical selection (small samples; PAPER validation required):
- BTCUSDT BREAKOUT LONG: 8 trades, +59.79, 62.5% wins
- XRPUSDT FIB_0618_0786 LONG: 6 trades, +58.99, 50.0% wins
- SOLUSDT FIB_0618_0786 LONG: 4 trades, +16.71, 50.0% wins
- XRPUSDT BREAKOUT LONG: 7 trades, +15.55, 42.9% wins
- SOLUSDT BREAKOUT SHORT: 3 trades, +11.27, 66.7% wins
No live orders: PAPER only.
"""
import asyncio
from fastapi.responses import JSONResponse
import app_bestof_core as core
from bestof_fib_strategy import fib_pullback
import bestof_ema4h as ema4h

app=core.app
core.ENABLED_SETUPS={"BREAKOUT","FIB_0618_0786"}
core.MIN_VOLUME_BREAKOUT=1.25
core.BREAKOUT_BODY_RATIO=0.62
core.BREAKOUT_BUFFER_RATE=0.0005
core.MIN_TREND_STRENGTH=0.0010
core.POSITION_LOOP_SECONDS=3
core.RISK_PER_TRADE=0.0015
core.MAX_OPEN_POSITIONS=2
core.NET_RISK_REWARD=1.30
core.BREAKEVEN_TRIGGER_R=0.75
_original_detect=core.detect_setup
_original_strategy=core.strategy_analysis

ALLOWED={
 ("BTCUSDT","BREAKOUT","LONG"),
 ("XRPUSDT","FIB_0618_0786","LONG"),
 ("SOLUSDT","FIB_0618_0786","LONG"),
 ("XRPUSDT","BREAKOUT","LONG"),
 ("SOLUSDT","BREAKOUT","SHORT"),
}

def detect_bestof(closed):
    base=_original_detect(closed)
    if base.get("signal") in ("LONG","SHORT") and base.get("setup")=="BREAKOUT":
        return base
    highs=[float(x[2]) for x in closed]; lows=[float(x[3]) for x in closed]
    closes=[float(x[4]) for x in closed]; volumes=[float(x[5]) for x in closed]
    fib=fib_pullback(highs,lows,closes,volumes,lookback=24,min_impulse_pct=0.006,min_volume_ratio=0.85)
    if not fib:return base
    cur=closed[-1]
    return {"signal":fib["signal"],"setup":"FIB_0618_0786","reason":"BEST-OF FIB 0.618-0.786 rejection",
      "candle_time":int(cur[0]),"price_closed":float(cur[4]),"signal_high":float(cur[2]),"signal_low":float(cur[3]),
      "volume_ratio":fib["volume_ratio"],"fib_0618":fib["fib_0618"],"fib_0786":fib["fib_0786"]}
core.detect_setup=detect_bestof

async def strategy_bestof(symbol):
    a=await _original_strategy(symbol)
    side=a.get("signal"); setup=a.get("setup")
    if side in ("LONG","SHORT") and (symbol,setup,side) not in ALLOWED:
        a["raw_signal"]=side; a["signal"]="WAIT"; a["reason"]="BEST-OF: historicky nevybraný setup/směr"
    a["bestof_allowed"]=sorted(["|".join(x) for x in ALLOWED])
    return a
core.strategy_analysis=strategy_bestof
ema4h.install(core)

@app.get("/bestof/status")
async def bestof_status():
    return JSONResponse({
      "mode":"PAPER","build":ema4h.BUILD,"ema4h":ema4h.summary(core),"allowed":[{"symbol":s,"setup":u,"side":d} for s,u,d in sorted(ALLOWED)]+[{"symbol":s,"setup":ema4h.SETUP,"side":"LONG"} for s in core.SYMBOLS],
      "balance":core.PAPER_BALANCE,"positions":core.positions,"trades":core.trade_history[:50],
      "last_cycle_at":core.last_cycle_at,"last_error":core.last_error,
      "persistence":"postgres" if core.DATABASE_URL else "memory"
    },headers={"Cache-Control":"no-store"})
