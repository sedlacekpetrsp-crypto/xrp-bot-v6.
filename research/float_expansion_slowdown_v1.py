"""Frozen XRP_FLOAT_EXPANSION_SLOWDOWN_V1; offline research only."""
from dataclasses import dataclass
from math import ceil,isfinite
DAY=86_400_000
@dataclass(frozen=True)
class Config:
    change_n:int=30;rank_n:int=365;quantile:float=.20;atr_n:int=14;stop_atr:float=2.;reward_r:float=3.;max_hold:int=10;risk_fraction:float=.005;notional_cap:float=.20;fee:float=.00095;slippage:float=.00020
def validate_prices(rows):
    ts=[x['timestamp'] for x in rows]
    if any(t%DAY for t in ts) or any(b<=a for a,b in zip(ts,ts[1:])):raise ValueError('timestamp')
    for x in rows:
        o,h,l,c=(float(x[k]) for k in ('open','high','low','close'))
        if not all(isfinite(v) for v in (o,h,l,c)) or not 0<l<=min(o,c)<=max(o,c)<=h:raise ValueError('value')
def make_signals(rows,config=Config()):
    if any(b['timestamp']-a['timestamp']!=DAY for a,b in zip(rows,rows[1:])):raise ValueError('metric gap')
    ratio=[]
    for x in rows:
        est=float(x['estimated_cap']);cur=float(x['current_cap'])
        if not all(isfinite(v) and v>0 for v in (est,cur)):raise ValueError('metric value')
        ratio.append(est/cur)
    growth=[None]*len(rows)
    for i in range(config.change_n,len(rows)):growth[i]=(ratio[i]-ratio[i-config.change_n])*100
    out={};rank=ceil(config.quantile*config.rank_n)-1;first=config.change_n+config.rank_n
    for i in range(first,len(rows)):
        hist=sorted(growth[i-config.rank_n:i]);threshold=hist[rank]
        if growth[i]<=threshold:out[rows[i]['timestamp']+2*DAY]=dict(metric_timestamp=rows[i]['timestamp'],float_ratio=ratio[i],change_30pp=growth[i],threshold=threshold)
    return out
def atr(rows,i,n):
    if i<n+1:return None
    if any(rows[j]['timestamp']-rows[j-1]['timestamp']!=DAY for j in range(i-n,i)):return None
    v=[]
    for j in range(i-n,i):
        p=rows[j-1]['close'];v.append(max(rows[j]['high']-rows[j]['low'],abs(rows[j]['high']-p),abs(rows[j]['low']-p)))
    return sum(v)/n
def backtest(rows,start,end,config=Config(),initial=10000.):
    validate_prices(rows);equity=initial;trades=[];curve=[dict(timestamp=start,equity=initial)];i=0
    while i<len(rows):
        b=rows[i];s=b.get('float_signal');a=atr(rows,i,config.atr_n)
        if not s or not(start<=b['timestamp']<end) or a is None or s['metric_timestamp']+2*DAY!=b['timestamp']:i+=1;continue
        raw_entry=b['open'];entry=raw_entry*(1+config.slippage);stop=entry-config.stop_atr*a
        if stop<=0:i+=1;continue
        qty=min(equity*config.risk_fraction/(entry-stop),equity*config.notional_cap/entry);target=entry+config.reward_r*(entry-stop);entry_fee=qty*entry*config.fee;entry_equity=equity;j=i
        while j<len(rows) and rows[j]['timestamp']<end:
            x=rows[j]
            if j>i and x['timestamp']-rows[j-1]['timestamp']!=DAY:raw_exit,reason,exit_i,exit_time=rows[j-1]['close'],'DATA_GAP',j-1,rows[j-1]['timestamp']
            elif x['open']<=stop:raw_exit,reason,exit_i,exit_time=x['open'],'GAP_STOP',j,x['timestamp']
            elif x['low']<=stop:raw_exit,reason,exit_i,exit_time=stop,'STOP',j,x['timestamp']
            elif x['open']>=target or x['high']>=target:raw_exit,reason,exit_i,exit_time=target,'TARGET',j,x['timestamp']
            elif j-i+1>=config.max_hold:raw_exit,reason,exit_i,exit_time=x['close'],'TIME',j,x['timestamp']
            else:
                mark=x['low']*(1-config.slippage);curve.append(dict(timestamp=x['timestamp'],equity=entry_equity+qty*(mark-entry)-entry_fee-qty*mark*config.fee));j+=1;continue
            exit_fill=raw_exit*(1-config.slippage);exit_fee=qty*exit_fill*config.fee;gross=qty*(raw_exit-raw_entry);fill_pnl=qty*(exit_fill-entry);fees=entry_fee+exit_fee;pnl=fill_pnl-fees;equity+=pnl
            trades.append(dict(metric_timestamp=s['metric_timestamp'],entry_timestamp=b['timestamp'],exit_timestamp=exit_time,entry_index=i,exit_index=exit_i,entry_equity=entry_equity,raw_entry=raw_entry,raw_exit=raw_exit,entry=entry,exit=exit_fill,qty=qty,atr=a,stop=stop,target=target,float_ratio=s['float_ratio'],change_30pp=s['change_30pp'],threshold=s['threshold'],leg_notional=qty*entry,gross=gross,slippage_cost=gross-fill_pnl,fees=fees,pnl=pnl,equity=equity,reason=reason));curve.append(dict(timestamp=exit_time,equity=equity));i=exit_i+1;break
        else:i+=1
    return trades,curve
