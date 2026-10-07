import asyncio
from fastapi.responses import JSONResponse
import app_v9 as core
from liquidity_hunter import signal_from_closed_candles

# Liquidity Hunter V2 — dedicated PAPER 24/7 strategy. No exchange order routing.
core.SYMBOLS=["XRPUSDT"]
core.TRADING_MODE="PAPER"
core.RISK_PER_TRADE=0.005
core.ATR_STOP_MULT=1.0
core.NET_RISK_REWARD=2.0
core.MAX_OPEN_POSITIONS=1
core.MAX_TRADE_MINUTES=240

async def analyze_liquidity(symbol):
    k5,k15,k1h=await asyncio.gather(core.klines(symbol,"5m",250),core.klines(symbol,"15m",250),core.klines(symbol,"1h",250))
    c5,c15,c1h=k5[:-1],k15[:-1],k1h[:-1]
    o5=[float(x[1]) for x in c5]; h5=[float(x[2]) for x in c5]; l5=[float(x[3]) for x in c5]
    cl5=[float(x[4]) for x in c5]; v5=[float(x[5]) for x in c5]
    cl15=[float(x[4]) for x in c15]; cl1h=[float(x[4]) for x in c1h]
    # Taker ratio intentionally optional until live historical-compatible source is wired.
    sig=signal_from_closed_candles(h5,l5,o5,cl5,v5,cl15,cl1h,taker_buy_ratio=None,
        lookback=24,volume_ratio_min=1.05,min_wick_atr=.12,stop_atr=1.0,rr=2.0)
    av=core.atr(h5,l5,cl5,14); market=float(k5[-1][4])
    if sig:
        a={"symbol":symbol,"signal":sig.side,"setup":"LIQUIDITY_HUNTER_V2","reason":sig.reason,
           "candle_time":int(c5[-1][0]),"closed_price":cl5[-1],"market_price":market,"atr":av,
           "sweep_level":sig.sweep_level,"planned_stop":sig.stop,"planned_target":sig.target}
    else:
        a={"symbol":symbol,"signal":"WAIT","setup":"LIQUIDITY_HUNTER_V2",
           "reason":"čekám: liquidity sweep -> reclaim -> potvrzovací svíčka -> 15m/1h safety filter -> volume",
           "candle_time":int(c5[-1][0]),"closed_price":cl5[-1],"market_price":market,"atr":av}
    core.last_analysis[symbol]=a
    return a

core.analyze_symbol=analyze_liquidity
app=core.app

@app.get("/liquidity/status")
async def liquidity_status():
    return JSONResponse({"bot":"LIQUIDITY HUNTER V2","mode":"PAPER",
        "running":core.bot_task is not None and not core.bot_task.done(),"last_cycle_at":core.last_cycle_at,
        "last_error":core.last_error,"balance":core.paper_balance,"positions":core.positions,
        "trades":core.trade_history[:50],"analysis":core.last_analysis,
        "risk_per_trade_pct":core.RISK_PER_TRADE*100,"atr_stop_mult":core.ATR_STOP_MULT,
        "net_rr":core.NET_RISK_REWARD},headers={"Cache-Control":"no-store"})
