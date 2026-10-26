"""Research-only cross-sectional dispersion spread; never sends orders."""
from math import isfinite
from statistics import pstdev
from dataclasses import dataclass
from datetime import datetime, timezone

ASSETS=("BTCUSDT","ETHUSDT","XRPUSDT","SOLUSDT")
HOUR=3600000

@dataclass(frozen=True)
class Config:
    history_days:int=180
    percentile:float=.9
    leg_fraction:float=.10
    stop:float=.03
    fee:float=.00095
    slip:float=.0002
    borrow_day:float=.0003

def validate(markets):
    if set(markets)!=set(ASSETS): raise ValueError("Require four markets")
    times=None
    for symbol,rows in markets.items():
        t=[int(b["timestamp"]) for b in rows]
        if any(y-x!=HOUR for x,y in zip(t,t[1:])): raise ValueError("Gap/duplicate")
        if times is not None and times!=t: raise ValueError("Markets misaligned")
        times=t
        for b in rows:
            o,h,l,c=[float(b[k]) for k in ("open","high","low","close")]
            if not all(isfinite(x) for x in (o,h,l,c)) or not 0<l<=min(o,c)<=max(o,c)<=h: raise ValueError("OHLC")
    return times

def percentile(values,p):
    s=sorted(values); pos=(len(s)-1)*p
    lo=int(pos);hi=min(lo+1,len(s)-1)
    return s[lo]+(s[hi]-s[lo])*(pos-lo)

def daily_disps(markets):
    rows=markets[ASSETS[0]]
    # Only full UTC days, using completed 24h returns at day boundary.
    days=[]
    for i in range(24,len(rows)):
        t=int(rows[i]["timestamp"])
        if t%86400000: continue
        rets={a:markets[a][i-1]["close"]/markets[a][i-25]["close"]-1 for a in ASSETS}
        days.append((i,pstdev(rets.values()),rets))
    return days

def backtest(markets,c=Config(),stress=False,initial=10000):
    validate(markets)
    days=daily_disps(markets)
    equity=initial;trades=[]
    fee=c.fee*(2 if stress else 1);slip=c.slip*(2 if stress else 1)
    for d in range(c.history_days,len(days)-1):
        i,disp,rets=days[d]
        hist=[x[1] for x in days[d-c.history_days:d]]
        if disp<=percentile(hist,c.percentile):continue
        long=min(rets,key=rets.get);short=max(rets,key=rets.get)
        if long==short:continue
        end=days[d+1][0]
        entry_long=markets[long][i]["open"]*(1+slip)
        entry_short=markets[short][i]["open"]*(1-slip)
        qty_l=equity*c.leg_fraction/entry_long
        qty_s=equity*c.leg_fraction/entry_short
        stop_l=entry_long*(1-c.stop);stop_s=entry_short*(1+c.stop)
        exit_i=end;px_l=markets[long][end]["open"];px_s=markets[short][end]["open"]
        reason="TIME"
        for j in range(i,end):
            l=markets[long][j];s=markets[short][j]
            l_hit=l["low"]<=stop_l;s_hit=s["high"]>=stop_s
            if l_hit or s_hit:
                exit_i=j
                px_l=min(l["open"],stop_l) if l_hit else l["open"]
                px_s=max(s["open"],stop_s) if s_hit else s["open"]
                reason="STOP";break
        fill_l=px_l*(1-slip);fill_s=px_s*(1+slip)
        held=(exit_i-i+1)/24
        pnl=qty_l*(fill_l-entry_long)+qty_s*(entry_short-fill_s)
        pnl-=fee*(qty_l*(entry_long+fill_l)+qty_s*(entry_short+fill_s))
        pnl-=c.borrow_day*(2 if stress else 1)*qty_s*entry_short*held
        equity+=pnl
        trades.append(dict(entry_index=i,exit_index=exit_i,long=long,short=short,pnl=pnl,equity=equity,reason=reason,dispersion=disp))
        if equity<=0:break
    return trades
