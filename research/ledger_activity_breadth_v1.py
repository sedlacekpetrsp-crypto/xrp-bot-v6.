"""Frozen XRPL on-chain activity-breadth strategy (offline only)."""
from dataclasses import dataclass
from math import ceil, isfinite

DAY=86_400_000

@dataclass(frozen=True)
class Config:
    lookback:int=90
    percentile:float=.80
    atr_n:int=14
    stop_atr:float=2.0
    reward_r:float=2.5
    max_hold:int=10
    risk_fraction:float=.005
    notional_cap:float=.20
    fee:float=.00095
    slippage:float=.00020

def validate(rows):
    ts=[x["timestamp"] for x in rows]
    if any(t%DAY for t in ts) or any(b<=a for a,b in zip(ts,ts[1:])): raise ValueError("timestamp")
    for x in rows:
        o,h,l,c=(float(x[k]) for k in ("open","high","low","close"))
        if not all(isfinite(v) for v in (o,h,l,c)) or not 0<l<=min(o,c)<=max(o,c)<=h: raise ValueError("OHLC")
        if not isfinite(float(x["active_addresses"])) or not isfinite(float(x["tx_count"])) or x["active_addresses"]<=0 or x["tx_count"]<=0: raise ValueError("metric")

def nearest_rank(values,p):
    s=sorted(values); return s[ceil(p*len(s))-1]

def median(values):
    s=sorted(values); n=len(s); return s[n//2] if n%2 else (s[n//2-1]+s[n//2])/2

def atr_at(rows,i,n):
    if i<n: return None
    tr=[]
    for j in range(i-n+1,i+1):
        pc=rows[j-1]["close"]
        tr.append(max(rows[j]["high"]-rows[j]["low"],abs(rows[j]["high"]-pc),abs(rows[j]["low"]-pc)))
    return sum(tr)/n

def signal_at(rows,i,c=Config()):
    k=i-1 # metric date D is first usable on signal close D+1
    if k-c.lookback<0: return False
    window=rows[k-c.lookback:k]
    if any(b["timestamp"]-a["timestamp"]!=DAY for a,b in zip(rows[k-c.lookback:i],rows[k-c.lookback+1:i+1])): return False
    breadth=lambda x:x["active_addresses"]/x["tx_count"]
    return breadth(rows[k])>=nearest_rank([breadth(x) for x in window],c.percentile) and rows[k]["tx_count"]>median([x["tx_count"] for x in window])

def backtest(rows,start,end,c=Config(),initial=10_000.0):
    validate(rows); equity=initial; trades=[]; curve=[{"timestamp":start,"equity":initial}]; i=0
    while i+1<len(rows):
        sig,entry=rows[i],rows[i+1]
        a=atr_at(rows,i,c.atr_n)
        if sig["timestamp"]<start or entry["timestamp"]>=end or entry["timestamp"]-sig["timestamp"]!=DAY or a is None or not signal_at(rows,i,c): i+=1; continue
        raw_entry=entry["open"]; fill_entry=raw_entry*(1+c.slippage); stop=fill_entry-c.stop_atr*a
        if stop<=0: i+=1; continue
        risk_dist=fill_entry-stop; qty=min(equity*c.risk_fraction/risk_dist,equity*c.notional_cap/fill_entry)
        target=fill_entry+c.reward_r*risk_dist; entry_fee=qty*fill_entry*c.fee; entry_equity=equity
        j=i+1; closed=False
        while j<len(rows) and rows[j]["timestamp"]<end:
            b=rows[j]
            if j>i+1 and b["timestamp"]-rows[j-1]["timestamp"]!=DAY:
                raw_exit=rows[j-1]["close"]; reason="DATA_GAP"; exit_idx=j-1; exit_time=rows[j-1]["timestamp"]
            elif b["open"]<=stop:
                raw_exit=b["open"]; reason="GAP_STOP"; exit_idx=j; exit_time=b["timestamp"]
            elif b["low"]<=stop:
                raw_exit=stop; reason="STOP"; exit_idx=j; exit_time=b["timestamp"]
            elif b["high"]>=target:
                raw_exit=target; reason="TARGET"; exit_idx=j; exit_time=b["timestamp"]
            elif j-(i+1)>=c.max_hold:
                raw_exit=b["open"]; reason="TIME"; exit_idx=j; exit_time=b["timestamp"]
            else:
                mark=b["low"]*(1-c.slippage); marked=entry_equity+qty*(mark-fill_entry)-entry_fee-qty*mark*c.fee
                curve.append({"timestamp":b["timestamp"],"equity":marked}); j+=1; continue
            fill_exit=raw_exit*(1-c.slippage); exit_fee=qty*fill_exit*c.fee
            gross=qty*(raw_exit-raw_entry); fill=qty*(fill_exit-fill_entry); fees=entry_fee+exit_fee; pnl=fill-fees; equity+=pnl
            trades.append(dict(signal_timestamp=sig["timestamp"],metric_timestamp=rows[i-1]["timestamp"],entry_timestamp=entry["timestamp"],exit_timestamp=exit_time,entry_index=i+1,exit_index=exit_idx,entry_equity=entry_equity,raw_entry=raw_entry,raw_exit=raw_exit,entry=fill_entry,exit=fill_exit,qty=qty,atr=a,stop=stop,target=target,signal_breadth=rows[i-1]["active_addresses"]/rows[i-1]["tx_count"],leg_notional=qty*fill_entry,gross=gross,slippage_cost=gross-fill,fees=fees,pnl=pnl,equity=equity,reason=reason))
            curve.append({"timestamp":exit_time,"equity":equity}); i=exit_idx; closed=True; break
        if not closed:
            exit_idx=min(j-1,len(rows)-1); last=rows[exit_idx]; raw_exit=last["close"]; fill_exit=raw_exit*(1-c.slippage); exit_fee=qty*fill_exit*c.fee
            gross=qty*(raw_exit-raw_entry); fill=qty*(fill_exit-fill_entry); fees=entry_fee+exit_fee; pnl=fill-fees; equity+=pnl
            trades.append(dict(signal_timestamp=sig["timestamp"],metric_timestamp=rows[i-1]["timestamp"],entry_timestamp=entry["timestamp"],exit_timestamp=last["timestamp"],entry_index=i+1,exit_index=exit_idx,entry_equity=entry_equity,raw_entry=raw_entry,raw_exit=raw_exit,entry=fill_entry,exit=fill_exit,qty=qty,atr=a,stop=stop,target=target,signal_breadth=rows[i-1]["active_addresses"]/rows[i-1]["tx_count"],leg_notional=qty*fill_entry,gross=gross,slippage_cost=gross-fill,fees=fees,pnl=pnl,equity=equity,reason="END"))
            curve.append({"timestamp":last["timestamp"],"equity":equity}); i=exit_idx
        i+=1
    return trades,curve
