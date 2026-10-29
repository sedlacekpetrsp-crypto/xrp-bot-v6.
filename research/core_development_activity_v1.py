"""Frozen XRP_CORE_DEVELOPMENT_ACTIVITY_V1 simulator; offline research only."""
from dataclasses import dataclass
from math import isfinite

DAY=86_400_000

@dataclass(frozen=True)
class Config:
    short_days:int=7
    min_short:int=5
    long_days:int=30
    min_long:int=15
    atr_n:int=14
    stop_atr:float=2.0
    reward_r:float=3.0
    max_hold:int=10
    risk_fraction:float=.005
    notional_cap:float=.20
    fee:float=.00095
    slippage:float=.00020

def validate_prices(rows):
    times=[x['timestamp'] for x in rows]
    if any(t%DAY for t in times) or any(b<=a for a,b in zip(times,times[1:])): raise ValueError('timestamp')
    for x in rows:
        o,h,l,c=(float(x[k]) for k in ('open','high','low','close'))
        if not all(isfinite(v) for v in (o,h,l,c)) or not 0<l<=min(o,c)<=max(o,c)<=h: raise ValueError('value')

def daily_signals(events,start_day,end_day,config=Config()):
    """Count merged PR events in trailing calendar windows using only each day prefix."""
    if any(b<a for a,b in zip(events,events[1:])): raise ValueError('event timestamp')
    out={}; left7=left30=0
    for day in range(start_day,end_day,DAY):
        close=day+DAY
        while left7<len(events) and events[left7]<close-config.short_days*DAY: left7+=1
        while left30<len(events) and events[left30]<close-config.long_days*DAY: left30+=1
        right=left30
        while right<len(events) and events[right]<close: right+=1
        short_start=right
        while short_start>0 and events[short_start-1]>=close-config.short_days*DAY: short_start-=1
        n7=right-short_start; n30=right-left30
        if n7>=config.min_short and n30>=config.min_long:
            out[day+DAY]=dict(signal_day=day,merge_count_7=n7,merge_count_30=n30)
    return out

def atr(rows,entry_i,n):
    if entry_i<n+1:return None
    start=entry_i-n
    if any(rows[j]['timestamp']-rows[j-1]['timestamp']!=DAY for j in range(start,entry_i)):return None
    vals=[]
    for j in range(start,entry_i):
        p=rows[j-1]['close']; vals.append(max(rows[j]['high']-rows[j]['low'],abs(rows[j]['high']-p),abs(rows[j]['low']-p)))
    return sum(vals)/n

def backtest(rows,start,end,config=Config(),initial=10_000.0):
    validate_prices(rows); equity=initial; trades=[]; curve=[dict(timestamp=start,equity=initial)]; i=0
    while i<len(rows):
        b=rows[i]; sig=b.get('development_signal'); a=atr(rows,i,config.atr_n)
        if not sig or not(start<=b['timestamp']<end) or a is None or sig['signal_day']+DAY!=b['timestamp']:
            i+=1; continue
        raw_entry=b['open']; entry=raw_entry*(1+config.slippage); stop=entry-config.stop_atr*a
        if stop<=0:i+=1;continue
        qty=min(equity*config.risk_fraction/(entry-stop),equity*config.notional_cap/entry)
        target=entry+config.reward_r*(entry-stop); entry_fee=qty*entry*config.fee; entry_equity=equity; j=i
        while j<len(rows) and rows[j]['timestamp']<end:
            x=rows[j]
            if j>i and x['timestamp']-rows[j-1]['timestamp']!=DAY:
                raw_exit,reason,exit_i,exit_time=rows[j-1]['close'],'DATA_GAP',j-1,rows[j-1]['timestamp']
            elif x['open']<=stop: raw_exit,reason,exit_i,exit_time=x['open'],'GAP_STOP',j,x['timestamp']
            elif x['low']<=stop: raw_exit,reason,exit_i,exit_time=stop,'STOP',j,x['timestamp']
            elif x['open']>=target or x['high']>=target: raw_exit,reason,exit_i,exit_time=target,'TARGET',j,x['timestamp']
            elif j-i+1>=config.max_hold: raw_exit,reason,exit_i,exit_time=x['close'],'TIME',j,x['timestamp']
            else:
                mark=x['low']*(1-config.slippage)
                curve.append(dict(timestamp=x['timestamp'],equity=entry_equity+qty*(mark-entry)-entry_fee-qty*mark*config.fee)); j+=1; continue
            exit_fill=raw_exit*(1-config.slippage); exit_fee=qty*exit_fill*config.fee
            gross=qty*(raw_exit-raw_entry); fill_pnl=qty*(exit_fill-entry); fees=entry_fee+exit_fee; pnl=fill_pnl-fees; equity+=pnl
            trades.append(dict(signal_timestamp=sig['signal_day']+DAY-1,signal_day=sig['signal_day'],entry_timestamp=b['timestamp'],exit_timestamp=exit_time,
                entry_index=i,exit_index=exit_i,entry_equity=entry_equity,raw_entry=raw_entry,raw_exit=raw_exit,entry=entry,exit=exit_fill,
                qty=qty,atr=a,stop=stop,target=target,merge_count_7=sig['merge_count_7'],merge_count_30=sig['merge_count_30'],
                leg_notional=qty*entry,gross=gross,slippage_cost=gross-fill_pnl,fees=fees,pnl=pnl,equity=equity,reason=reason))
            curve.append(dict(timestamp=exit_time,equity=equity));i=exit_i+1;break
        else:i+=1
    return trades,curve
