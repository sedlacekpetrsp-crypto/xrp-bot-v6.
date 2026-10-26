"""Continuous perpetual-premium recovery signal with XRP spot execution."""
from dataclasses import dataclass
from math import isfinite

STEP=3_600_000


@dataclass(frozen=True)
class Config:
    window:int=720
    quantile:float=.025
    extreme_ceiling:float=-.001
    recovery:float=.0005
    current_ceiling:float=0.
    atr_window:int=24
    stop_atr:float=1.5
    target_r:float=2.
    max_hold:int=12
    fee:float=.00095
    slippage:float=.0002
    risk:float=.005
    notional_cap:float=.20


def validate(bars,premium):
    if [b['timestamp'] for b in bars] != [p['timestamp'] for p in premium]: raise ValueError('alignment')
    times=[b['timestamp'] for b in bars]
    if any(t%STEP for t in times) or any(b<=a for a,b in zip(times,times[1:])): raise ValueError('timestamp')
    for b in bars:
        o,h,l,c=(float(b[k]) for k in ('open','high','low','close'))
        if not all(isfinite(x) for x in (o,h,l,c)) or not 0<l<=min(o,c)<=max(o,c)<=h: raise ValueError('OHLC')
    for p in premium:
        o,h,l,c=(float(p[k]) for k in ('open','high','low','close'))
        if not all(isfinite(x) for x in (o,h,l,c)) or not l<=min(o,c)<=max(o,c)<=h: raise ValueError('premium')


def quantile(values,q):
    values=sorted(values); rank=q*(len(values)-1); low=int(rank); high=min(low+1,len(values)-1); weight=rank-low
    return values[low]*(1-weight)+values[high]*weight


def signal(bars,premium,i,c=Config()):
    if i<max(c.window+1,c.atr_window): return None
    if premium[i]['timestamp']-premium[i-c.window-1]['timestamp']!=(c.window+1)*STEP: return None
    threshold=quantile([p['close'] for p in premium[i-c.window-1:i-1]],c.quantile)
    previous=premium[i-1]['close']; current=premium[i]['close']
    if previous>threshold or previous>c.extreme_ceiling or current-previous<c.recovery or current>c.current_ceiling: return None
    if bars[i]['timestamp']-bars[i-c.atr_window]['timestamp']!=c.atr_window*STEP: return None
    ranges=[max(bars[k]['high']-bars[k]['low'],abs(bars[k]['high']-bars[k-1]['close']),abs(bars[k]['low']-bars[k-1]['close'])) for k in range(i-c.atr_window+1,i+1)]
    atr=sum(ranges)/len(ranges)
    return dict(atr=atr,previous_premium=previous,current_premium=current,threshold=threshold) if atr>0 else None


def backtest(bars,premium,start,end,c=Config(),initial=10_000.):
    validate(bars,premium); output=[]; equity=initial; i=max(c.window+1,c.atr_window)
    while i<len(bars)-1:
        if bars[i+1]['timestamp']<start: i+=1; continue
        if bars[i+1]['timestamp']>=end: break
        found=signal(bars,premium,i,c)
        if found is None: i+=1; continue
        entry_index=i+1; entry=bars[entry_index]['open']*(1+c.slippage); stop=entry-c.stop_atr*found['atr']
        if stop<=0: i+=1; continue
        qty=min(equity*c.risk/(entry-stop),equity*c.notional_cap/entry); target=entry+c.target_r*(entry-stop)
        exit_index=entry_index
        while exit_index+1<len(bars) and exit_index-entry_index+1<c.max_hold and bars[exit_index+1]['timestamp']<end and bars[exit_index+1]['timestamp']==bars[exit_index]['timestamp']+STEP: exit_index+=1
        raw,reason=bars[exit_index]['close'],'TIME'
        for j in range(entry_index,exit_index+1):
            b=bars[j]
            if b['open']<=stop: exit_index,raw,reason=j,b['open'],'GAP_STOP'; break
            if b['low']<=stop: exit_index,raw,reason=j,stop,'STOP'; break
            if b['high']>=target: exit_index,raw,reason=j,target,'TARGET'; break
        fill=raw*(1-c.slippage); fees=c.fee*qty*(entry+fill); gross=qty*(raw-entry/(1+c.slippage)); pnl=qty*(fill-entry)-fees; equity+=pnl
        output.append(dict(signal_index=i,entry_index=entry_index,exit_index=exit_index,entry=entry,exit=fill,stop=stop,target=target,qty=qty,pnl=pnl,equity=equity,fees=fees,gross=gross,slippage_cost=gross-fees-pnl,reason=reason,previous_premium=found['previous_premium'],current_premium=found['current_premium'],threshold=found['threshold']))
        if equity<=0: break
        i=exit_index+1
    return output
