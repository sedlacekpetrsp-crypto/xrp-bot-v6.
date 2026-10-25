"""Causal derivatives-crowding signal with spot-only execution."""
from dataclasses import dataclass
from math import isfinite,sqrt
STEP=300_000
@dataclass(frozen=True)
class Config:
    window:int=288; z:float=-2.; taker:float=1.15; oi_lookback:int=12; oi_drop:float=-.01; atr_window:int=36
    stop_atr:float=1.5; target_r:float=2.; max_hold:int=36; fee:float=.00095; slippage:float=.0002; risk:float=.005; notional_cap:float=.20
def validate(bars,metrics):
    bt=[b['timestamp'] for b in bars];mt=[m['timestamp'] for m in metrics]
    for seq in (bt,mt):
        if any(t%STEP for t in seq) or any(b<=a for a,b in zip(seq,seq[1:])):raise ValueError('timestamp')
    if bt!=mt:raise ValueError('alignment')
    for b in bars:
        o,h,l,c=(float(b[k]) for k in ('open','high','low','close'))
        if not all(isfinite(x) for x in (o,h,l,c)) or not 0<l<=min(o,c)<=max(o,c)<=h:raise ValueError('OHLC')
    for m in metrics:
        if not all(isfinite(float(m[k])) and float(m[k])>0 for k in ('open_interest','long_short','taker_ratio')):raise ValueError('metric')
def signal(bars,m,i,c=Config()):
    if i<max(c.window,c.oi_lookback,c.atr_window):return None
    if m[i]['timestamp']-m[i-c.window]['timestamp']!=c.window*STEP:return None
    hist=[x['long_short'] for x in m[i-c.window:i]];mean=sum(hist)/len(hist);sd=sqrt(sum((x-mean)**2 for x in hist)/len(hist))
    if sd<=0:return None
    z=(m[i]['long_short']-mean)/sd;oid=m[i]['open_interest']/m[i-c.oi_lookback]['open_interest']-1
    if z>c.z or m[i]['taker_ratio']<c.taker or oid>c.oi_drop:return None
    tr=[max(bars[k]['high']-bars[k]['low'],abs(bars[k]['high']-bars[k-1]['close']),abs(bars[k]['low']-bars[k-1]['close'])) for k in range(i-c.atr_window+1,i+1)];atr=sum(tr)/len(tr)
    return dict(atr=atr,z=z,oi_change=oid,taker_ratio=m[i]['taker_ratio']) if atr>0 else None
def backtest(bars,m,start,end,c=Config(),initial=10000.):
    validate(bars,m);out=[];equity=initial;i=max(c.window,c.oi_lookback,c.atr_window)
    while i<len(bars)-1:
        if bars[i+1]['timestamp']<start:i+=1;continue
        if bars[i+1]['timestamp']>=end:break
        s=signal(bars,m,i,c)
        if s is None:i+=1;continue
        ei=i+1;entry=bars[ei]['open']*(1+c.slippage);stop=entry-c.stop_atr*s['atr']
        if stop<=0:i+=1;continue
        qty=min(equity*c.risk/(entry-stop),equity*c.notional_cap/entry);target=entry+c.target_r*(entry-stop);last=ei
        while last+1<len(bars) and bars[last+1]['timestamp']<end:last+=1
        xi=min(ei+c.max_hold-1,last);raw=bars[xi]['close'];reason='TIME' if xi<last else 'END'
        for j in range(ei,xi+1):
            b=bars[j]
            if b['open']<=stop:xi,raw,reason=j,b['open'],'GAP_STOP';break
            if b['low']<=stop:xi,raw,reason=j,stop,'STOP';break
            if b['high']>=target:xi,raw,reason=j,target,'TARGET';break
        fill=raw*(1-c.slippage);fees=c.fee*qty*(entry+fill);gross=qty*(raw-entry/(1+c.slippage));pnl=qty*(fill-entry)-fees;equity+=pnl
        out.append(dict(signal_index=i,entry_index=ei,exit_index=xi,entry=entry,exit=fill,stop=stop,target=target,qty=qty,pnl=pnl,equity=equity,fees=fees,gross=gross,slippage_cost=gross-fees-pnl,reason=reason,z=s['z'],oi_change=s['oi_change'],taker_ratio=s['taker_ratio']))
        if equity<=0:break
        i=xi+1
    return out
