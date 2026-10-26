"""Causal Amihud-style downside illiquidity shock reversal."""
from dataclasses import dataclass
from math import isfinite,log

STEP=3_600_000

@dataclass(frozen=True)
class Config:
    window:int=720
    quantile:float=.975
    return_floor:float=-.01
    atr_window:int=24
    stop_atr:float=1.5
    target_r:float=2.
    max_hold:int=12
    fee:float=.00095
    slippage:float=.0002
    risk:float=.005
    notional_cap:float=.20

def validate(bars):
    times=[b['timestamp'] for b in bars]
    if any(t%STEP for t in times) or any(b<=a for a,b in zip(times,times[1:])): raise ValueError('timestamp')
    for b in bars:
        o,h,l,c,q=(float(b[k]) for k in ('open','high','low','close','quote_volume'))
        if not all(isfinite(x) for x in (o,h,l,c,q)) or not 0<l<=min(o,c)<=max(o,c)<=h or q<0: raise ValueError('bar')

def percentile(values,q):
    values=sorted(values); rank=q*(len(values)-1); lo=int(rank); hi=min(lo+1,len(values)-1); w=rank-lo
    return values[lo]*(1-w)+values[hi]*w

def impact(bars,i): return max(0.,-log(bars[i]['close']/bars[i-1]['close']))/bars[i]['quote_volume']

def signal(bars,i,c=Config()):
    need=max(c.window+1,c.atr_window)
    if i<need or bars[i]['timestamp']-bars[i-c.window-1]['timestamp']!=(c.window+1)*STEP: return None
    if any(b['quote_volume']<=0 for b in bars[i-c.window-1:i+1]): return None
    ret=log(bars[i]['close']/bars[i-1]['close'])
    if ret>c.return_floor: return None
    current=impact(bars,i); threshold=percentile([impact(bars,k) for k in range(i-c.window,i)],c.quantile)
    if current<threshold: return None
    ranges=[max(bars[k]['high']-bars[k]['low'],abs(bars[k]['high']-bars[k-1]['close']),abs(bars[k]['low']-bars[k-1]['close'])) for k in range(i-c.atr_window+1,i+1)]
    atr=sum(ranges)/len(ranges)
    return dict(atr=atr,log_return=ret,impact=current,threshold=threshold) if atr>0 else None

def backtest(bars,start,end,c=Config(),initial=10_000.):
    validate(bars); out=[]; equity=initial; i=max(c.window+1,c.atr_window)
    while i<len(bars)-1:
        if bars[i+1]['timestamp']<start: i+=1; continue
        if bars[i+1]['timestamp']>=end: break
        found=signal(bars,i,c)
        if found is None: i+=1; continue
        ei=i+1; entry=bars[ei]['open']*(1+c.slippage); stop=entry-c.stop_atr*found['atr']
        if stop<=0: i+=1; continue
        qty=min(equity*c.risk/(entry-stop),equity*c.notional_cap/entry); target=entry+c.target_r*(entry-stop)
        xi=ei
        while xi+1<len(bars) and xi-ei+1<c.max_hold and bars[xi+1]['timestamp']<end and bars[xi+1]['timestamp']==bars[xi]['timestamp']+STEP: xi+=1
        raw,reason=bars[xi]['close'],'TIME'
        for j in range(ei,xi+1):
            b=bars[j]
            if b['open']<=stop: xi,raw,reason=j,b['open'],'GAP_STOP'; break
            if b['low']<=stop: xi,raw,reason=j,stop,'STOP'; break
            if b['high']>=target: xi,raw,reason=j,target,'TARGET'; break
        fill=raw*(1-c.slippage); fees=c.fee*qty*(entry+fill); gross=qty*(raw-entry/(1+c.slippage)); pnl=qty*(fill-entry)-fees; equity+=pnl
        out.append(dict(signal_index=i,entry_index=ei,exit_index=xi,entry=entry,exit=fill,stop=stop,target=target,qty=qty,pnl=pnl,equity=equity,fees=fees,gross=gross,slippage_cost=gross-fees-pnl,reason=reason,**found))
        if equity<=0: break
        i=xi+1
    return out

