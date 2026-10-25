"""Frozen causal cross-market residual mean-reversion simulator."""
from dataclasses import dataclass
from math import isfinite,log,sqrt
STEP=3_600_000

@dataclass(frozen=True)
class Config:
    window:int=168; z:float=2.5; factor_floor:float=-.005; atr_window:int=24
    stop_atr:float=1.75; target_r:float=1.5; max_hold:int=12
    fee:float=.00095; slippage:float=.0002; risk:float=.005; notional_cap:float=.20

def validate(markets):
    ref=None
    for s in ('XRPUSDT','BTCUSDT','ETHUSDT'):
        times=[]
        for b in markets[s]:
            o,h,l,c=(float(b[k]) for k in ('open','high','low','close'))
            if not all(isfinite(v) for v in (o,h,l,c)) or not 0<l<=min(o,c)<=max(o,c)<=h:raise ValueError('invalid OHLC')
            times.append(int(b['timestamp']))
        if any(t%STEP for t in times) or any(b<=a for a,b in zip(times,times[1:])):raise ValueError('timestamp')
        if ref is not None and times!=ref:raise ValueError('alignment')
        ref=times

def signal(m,i,c=Config()):
    if i<c.window+1:return None
    x=m['XRPUSDT']
    if x[i]['timestamp']-x[i-c.window-1]['timestamp']!=(c.window+1)*STEP:return None
    xr=[log(x[k]['close']/x[k-1]['close']) for k in range(i-c.window,i+1)]
    fr=[.5*(log(m['BTCUSDT'][k]['close']/m['BTCUSDT'][k-1]['close'])+log(m['ETHUSDT'][k]['close']/m['ETHUSDT'][k-1]['close'])) for k in range(i-c.window,i+1)]
    train_x,train_f=xr[:-1],fr[:-1];den=sum(v*v for v in train_f)
    if den<=0:return None
    beta=sum(a*b for a,b in zip(train_x,train_f))/den
    residuals=[a-beta*b for a,b in zip(train_x,train_f)]
    mean=sum(residuals)/len(residuals);sd=sqrt(sum((r-mean)**2 for r in residuals)/len(residuals))
    current=xr[-1]-beta*fr[-1]
    if sd<=0 or current>mean-c.z*sd or fr[-1]<c.factor_floor:return None
    tr=[max(x[k]['high']-x[k]['low'],abs(x[k]['high']-x[k-1]['close']),abs(x[k]['low']-x[k-1]['close'])) for k in range(i-c.atr_window+1,i+1)]
    atr=sum(tr)/len(tr)
    return dict(atr=atr,beta=beta,residual=current,zscore=(current-mean)/sd) if atr>0 else None

def backtest(m,start,end,c=Config(),initial=10_000.):
    validate(m);bars=m['XRPUSDT'];trades=[];equity=initial;i=c.window+1
    while i<len(bars)-1:
        if bars[i+1]['timestamp']<start:i+=1;continue
        if bars[i+1]['timestamp']>=end:break
        s=signal(m,i,c)
        if s is None:i+=1;continue
        ei=i+1;entry=bars[ei]['open']*(1+c.slippage);stop=entry-c.stop_atr*s['atr']
        if stop<=0:i+=1;continue
        qty=min(equity*c.risk/(entry-stop),equity*c.notional_cap/entry);target=entry+c.target_r*(entry-stop)
        last=ei
        while last+1<len(bars) and bars[last+1]['timestamp']<end:last+=1
        xi=min(ei+c.max_hold-1,last);raw=bars[xi]['close'];reason='TIME' if xi<last else 'END'
        for j in range(ei,xi+1):
            b=bars[j]
            if b['open']<=stop:xi,raw,reason=j,b['open'],'GAP_STOP';break
            if b['low']<=stop:xi,raw,reason=j,stop,'STOP';break
            if b['high']>=target:xi,raw,reason=j,target,'TARGET';break
        fill=raw*(1-c.slippage);fees=c.fee*qty*(entry+fill);gross=qty*(raw-entry/(1+c.slippage));pnl=qty*(fill-entry)-fees;equity+=pnl
        trades.append(dict(signal_index=i,entry_index=ei,exit_index=xi,entry=entry,exit=fill,stop=stop,target=target,qty=qty,pnl=pnl,equity=equity,fees=fees,gross=gross,slippage_cost=gross-fees-pnl,reason=reason,beta=s['beta'],zscore=s['zscore']))
        if equity<=0:break
        i=xi+1
    return trades
