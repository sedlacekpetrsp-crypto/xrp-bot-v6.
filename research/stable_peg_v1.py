"""Fixed stablecoin peg-reversion simulator."""
from dataclasses import dataclass
from math import isfinite
STEP=900_000
@dataclass(frozen=True)
class Config:
    trigger:float=.994; max_open:float=.996; target:float=.999; stop:float=.988; max_hold:int=672
    fee:float=.00095; slippage:float=.0002; risk:float=.005; notional_cap:float=.20
def validate(bars):
    last=None
    for b in bars:
        o,h,l,c=(float(b[k]) for k in ('open','high','low','close'))
        if not all(isfinite(v) for v in (o,h,l,c)) or not 0<l<=min(o,c)<=max(o,c)<=h:raise ValueError('OHLC')
        t=int(b['timestamp'])
        if t%STEP or (last is not None and t-last!=STEP):raise ValueError('gap/duplicate')
        last=t
def backtest(bars,start,end,c=Config(),initial=10_000/3):
    validate(bars);out=[];equity=initial;i=0
    while i<len(bars)-1:
        if bars[i+1]['timestamp']<start:i+=1;continue
        if bars[i+1]['timestamp']>=end:break
        if bars[i]['close']>c.trigger or bars[i+1]['open']>c.max_open:i+=1;continue
        ei=i+1;entry=bars[ei]['open']*(1+c.slippage)
        if entry<=c.stop:i+=1;continue
        qty=min(equity*c.risk/(entry-c.stop),equity*c.notional_cap/entry);last=ei
        while last+1<len(bars) and bars[last+1]['timestamp']<end:last+=1
        xi=min(ei+c.max_hold-1,last);raw=bars[xi]['close'];reason='TIME' if xi<last else 'END'
        for j in range(ei,xi+1):
            b=bars[j]
            if b['open']<=c.stop:xi,raw,reason=j,b['open'],'GAP_STOP';break
            if b['low']<=c.stop:xi,raw,reason=j,c.stop,'STOP';break
            if b['high']>=c.target:xi,raw,reason=j,c.target,'TARGET';break
        fill=raw*(1-c.slippage);fees=c.fee*qty*(entry+fill);gross=qty*(raw-entry/(1+c.slippage));pnl=qty*(fill-entry)-fees;equity+=pnl
        out.append(dict(signal_index=i,entry_index=ei,exit_index=xi,entry=entry,exit=fill,stop=c.stop,target=c.target,qty=qty,pnl=pnl,equity=equity,fees=fees,gross=gross,slippage_cost=gross-fees-pnl,reason=reason))
        if equity<=0:break
        i=xi+1
    return out
