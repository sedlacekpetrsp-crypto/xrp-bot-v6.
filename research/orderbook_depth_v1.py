"""Causal passive order-book depth imbalance strategy."""
from dataclasses import dataclass
from math import isfinite,log
STEP=3_600_000

@dataclass(frozen=True)
class Config:
    window:int=720; quantile:float=.975; min_ratio:float=1.5; atr_window:int=24
    stop_atr:float=1.5; target_r:float=2.; max_hold:int=12
    fee:float=.00095; slippage:float=.0002; risk:float=.005; notional_cap:float=.20

def validate(bars,depth):
    if [b['timestamp'] for b in bars] != [d['timestamp'] for d in depth]: raise ValueError('alignment')
    ts=[b['timestamp'] for b in bars]
    if any(t%STEP for t in ts) or any(b<=a for a,b in zip(ts,ts[1:])): raise ValueError('timestamp')
    for b in bars:
        o,h,l,c=(float(b[k]) for k in ('open','high','low','close'))
        if not all(isfinite(x) for x in (o,h,l,c)) or not 0<l<=min(o,c)<=max(o,c)<=h: raise ValueError('OHLC')
    if any(not isfinite(float(d[k])) or float(d[k])<=0 for d in depth for k in ('bid_notional','ask_notional')): raise ValueError('depth')

def percentile(values,q):
    values=sorted(values); r=q*(len(values)-1); lo=int(r); hi=min(lo+1,len(values)-1); w=r-lo
    return values[lo]*(1-w)+values[hi]*w

def imbalance(d): return log(d['bid_notional']/d['ask_notional'])

def signal(bars,depth,i,c=Config()):
    if i<max(c.window,c.atr_window) or bars[i]['timestamp']-bars[i-c.window]['timestamp']!=c.window*STEP: return None
    current=imbalance(depth[i]); threshold=percentile([imbalance(d) for d in depth[i-c.window:i]],c.quantile)
    if current<log(c.min_ratio) or current<threshold: return None
    ranges=[max(bars[k]['high']-bars[k]['low'],abs(bars[k]['high']-bars[k-1]['close']),abs(bars[k]['low']-bars[k-1]['close'])) for k in range(i-c.atr_window+1,i+1)]
    atr=sum(ranges)/len(ranges)
    return dict(atr=atr,log_imbalance=current,threshold=threshold) if atr>0 else None

def backtest(bars,depth,start,end,c=Config(),initial=10_000.):
    validate(bars,depth); out=[]; equity=initial; i=max(c.window,c.atr_window)
    while i<len(bars)-1:
        if bars[i+1]['timestamp']<start: i+=1; continue
        if bars[i+1]['timestamp']>=end: break
        found=signal(bars,depth,i,c)
        if found is None: i+=1; continue
        ei=i+1; entry=bars[ei]['open']*(1+c.slippage); stop=entry-c.stop_atr*found['atr']
        if stop<=0: i+=1; continue
        qty=min(equity*c.risk/(entry-stop),equity*c.notional_cap/entry); target=entry+c.target_r*(entry-stop); xi=ei
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

