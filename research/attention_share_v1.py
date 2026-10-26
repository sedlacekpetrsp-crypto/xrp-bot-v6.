"""Causal XRP cross-market quote-volume attention-share strategy."""
from dataclasses import dataclass
from math import isfinite
STEP=3_600_000; ASSETS=('BTCUSDT','ETHUSDT','BNBUSDT','SOLUSDT','XRPUSDT')
@dataclass(frozen=True)
class Config:
    days:int=180; quantile:float=.80; stop_pct:float=.03; target_pct:float=.06; max_hold:int=24
    fee:float=.00095; slippage:float=.0002; risk:float=.005; notional_cap:float=.20
def validate(data):
    if set(data)!=set(ASSETS): raise ValueError('assets')
    ts=[b['timestamp'] for b in data['XRPUSDT']]
    if not ts or any(t%STEP for t in ts) or any(b<=a for a,b in zip(ts,ts[1:])): raise ValueError('timestamp')
    for a in ASSETS:
        if [b['timestamp'] for b in data[a]]!=ts: raise ValueError('alignment')
        for b in data[a]:
            o,h,l,c,q=(float(b[k]) for k in ('open','high','low','close','quote_volume'))
            if not all(isfinite(x) for x in (o,h,l,c,q)) or not 0<l<=min(o,c)<=max(o,c)<=h or q<0: raise ValueError('bar')
def percentile(v,q):
    v=sorted(v); r=q*(len(v)-1); lo=int(r); hi=min(lo+1,len(v)-1); w=r-lo; return v[lo]*(1-w)+v[hi]*w
def share(data,i):
    totals={a:sum(b['quote_volume'] for b in data[a][i-23:i+1]) for a in ASSETS}; total=sum(totals.values()); return totals['XRPUSDT']/total if total>0 else None
def signal(data,i,c=Config()):
    if i<24*c.days+23 or (data['XRPUSDT'][i]['timestamp']//STEP)%24!=23: return None
    if data['XRPUSDT'][i]['timestamp']-data['XRPUSDT'][i-24*c.days-23]['timestamp']!=(24*c.days+23)*STEP: return None
    current=share(data,i); history=[share(data,i-24*d) for d in range(c.days,0,-1)]
    if current is None or any(x is None for x in history): return None
    threshold=percentile(history,c.quantile); return dict(attention_share=current,threshold=threshold) if current>threshold else None
def backtest(data,start,end,c=Config(),initial=10_000.):
    validate(data); bars=data['XRPUSDT']; out=[]; equity=initial; i=24*c.days+23
    while i<len(bars)-1:
        if bars[i+1]['timestamp']<start: i+=1; continue
        if bars[i+1]['timestamp']>=end: break
        found=signal(data,i,c)
        if found is None: i+=1; continue
        ei=i+1; entry=bars[ei]['open']*(1+c.slippage); stop=entry*(1-c.stop_pct); target=entry*(1+c.target_pct); qty=min(equity*c.risk/(entry-stop),equity*c.notional_cap/entry); xi=ei
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

