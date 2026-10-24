"""Isolated offline AUTOCORR_REGIME_SWITCH_V1, spot LONG only; no broker imports."""
from dataclasses import dataclass
from math import log, sqrt, isfinite

@dataclass(frozen=True)
class Config:
    window: int = 96
    breakout: int = 4
    regime: float = .12
    move: float = .0035
    atr_window: int = 14
    stop_atr: float = 1.8
    target_r: float = 2.2
    max_hold: int = 24
    fee: float = .00095
    slippage: float = .0002
    risk: float = .005
    notional_cap: float = .20

def validate(bars):
    last = None
    for b in bars:
        o,h,l,c = (float(b[k]) for k in ("open","high","low","close"))
        if not all(map(isfinite,(o,h,l,c))) or not 0<l<=min(o,c)<=max(o,c)<=h:
            raise ValueError("invalid OHLC")
        if "timestamp" in b:
            t=int(b["timestamp"])
            if last is not None and t-last!=900000:
                raise ValueError("missing/duplicate 15m candle")
            last=t

def pearson_lag_one(returns):
    x,y=returns[:-1],returns[1:]
    mx=sum(x)/len(x);my=sum(y)/len(y)
    cov=sum((a-mx)*(b-my) for a,b in zip(x,y))
    vx=sum((a-mx)**2 for a in x);vy=sum((b-my)**2 for b in y)
    return cov/sqrt(vx*vy) if vx>0 and vy>0 else 0.

def signal(bars,i,c=Config()):
    if i < max(c.window+1,c.atr_window,c.breakout):
        return None
    rets=[log(bars[k]["close"]/bars[k-1]["close"]) for k in range(i-c.window+1,i+1)]
    rho=pearson_lag_one(rets)
    move=bars[i]["close"]/bars[i-c.breakout]["close"]-1
    continuation=rho>=c.regime and move>=c.move
    reversal=rho<=-c.regime and move<=-c.move
    if not (continuation or reversal): return None
    trs=[max(bars[k]["high"]-bars[k]["low"],abs(bars[k]["high"]-bars[k-1]["close"]),abs(bars[k]["low"]-bars[k-1]["close"])) for k in range(i-c.atr_window+1,i+1)]
    atr=sum(trs)/len(trs)
    return (atr,"CONTINUATION" if continuation else "REVERSAL") if atr>0 else None

def backtest(bars,c=Config(),initial_equity=10000.):
    validate(bars)
    trades=[];equity=initial_equity
    i=max(c.window+1,c.atr_window,c.breakout)
    while i<len(bars)-1:
        s=signal(bars,i,c)
        if s is None: i+=1;continue
        atr,regime=s
        entry_i=i+1
        entry=bars[entry_i]["open"]*(1+c.slippage)
        stop=entry-c.stop_atr*atr
        if stop<=0: i+=1;continue
        qty=min(equity*c.risk/(entry-stop),equity*c.notional_cap/entry)
        target=entry+c.target_r*(entry-stop)
        end=min(entry_i+c.max_hold-1,len(bars)-1)
        raw=bars[end]["close"];reason="TIME" if end<len(bars)-1 else "END"
        for j in range(entry_i,end+1):
            b=bars[j]
            if b["open"]<=stop: end,raw,reason=j,b["open"],"GAP_STOP";break
            if b["low"]<=stop: end,raw,reason=j,stop,"STOP";break
            if b["high"]>=target: end,raw,reason=j,target,"TARGET";break
        fill=raw*(1-c.slippage)
        pnl=qty*(fill-entry)-c.fee*qty*(entry+fill)
        equity+=pnl
        trades.append(dict(signal_index=i,entry_index=entry_i,exit_index=end,regime=regime,qty=qty,entry=entry,exit=fill,pnl=pnl,equity=equity,reason=reason))
        if equity<=0: break
        i=end+1
    return trades
