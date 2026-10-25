"""Causal large-average-trade continuation; isolated spot simulator."""
from dataclasses import dataclass
from math import isfinite,log,sqrt
STEP=3_600_000
@dataclass(frozen=True)
class Config:
    window:int=168; size_z:float=2.; min_return:float=.001; max_return:float=.015; min_clv:float=.75
    atr_window:int=24; stop_atr:float=1.5; target_r:float=2.; max_hold:int=8
    fee:float=.00095; slippage:float=.0002; risk:float=.005; notional_cap:float=.20

def validate(bars):
    last=None
    for b in bars:
        o,h,l,c,q,n=(float(b[k]) for k in ('open','high','low','close','quote_volume','trades'))
        if not all(isfinite(v) for v in (o,h,l,c,q,n)) or not 0<l<=min(o,c)<=max(o,c)<=h or q<=0 or n<=0:raise ValueError('invalid bar')
        t=int(b['timestamp'])
        if t%STEP or (last is not None and t-last!=STEP):raise ValueError('missing/duplicate hour')
        last=t

def signal(bars,i,c=Config()):
    if i<c.window:return None
    sizes=[log(bars[k]['quote_volume']/bars[k]['trades']) for k in range(i-c.window,i)]
    mean=sum(sizes)/len(sizes);sd=sqrt(sum((x-mean)**2 for x in sizes)/len(sizes))
    if sd<=0:return None
    z=(log(bars[i]['quote_volume']/bars[i]['trades'])-mean)/sd
    ret=bars[i]['close']/bars[i-1]['close']-1;rng=bars[i]['high']-bars[i]['low'];clv=(bars[i]['close']-bars[i]['low'])/rng if rng>0 else 0
    if z<c.size_z or not c.min_return<=ret<=c.max_return or clv<c.min_clv:return None
    tr=[max(bars[k]['high']-bars[k]['low'],abs(bars[k]['high']-bars[k-1]['close']),abs(bars[k]['low']-bars[k-1]['close'])) for k in range(i-c.atr_window+1,i+1)]
    atr=sum(tr)/len(tr);return dict(atr=atr,size_z=z) if atr>0 else None

def backtest(bars,start,end,c=Config(),initial=10000.):
    validate(bars);out=[];equity=initial;i=c.window
    while i<len(bars)-1:
        if bars[i+1]['timestamp']<start:i+=1;continue
        if bars[i+1]['timestamp']>=end:break
        s=signal(bars,i,c)
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
        out.append(dict(signal_index=i,entry_index=ei,exit_index=xi,entry=entry,exit=fill,stop=stop,target=target,qty=qty,pnl=pnl,equity=equity,fees=fees,gross=gross,slippage_cost=gross-fees-pnl,reason=reason,size_z=s['size_z']))
        if equity<=0:break
        i=xi+1
    return out
