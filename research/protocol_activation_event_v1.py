"""Frozen XRP_PROTOCOL_ACTIVATION_EVENT_V1 simulator; offline research only."""
from dataclasses import dataclass
from math import isfinite

DAY=86_400_000

@dataclass(frozen=True)
class Config:
    atr_n:int=14; stop_atr:float=2.; reward_r:float=3.; max_hold:int=14
    risk_fraction:float=.005; notional_cap:float=.20; fee:float=.00095; slippage:float=.00020

def validate_prices(rows):
    ts=[x['timestamp'] for x in rows]
    if any(t%DAY for t in ts) or any(b<=a for a,b in zip(ts,ts[1:])): raise ValueError('timestamp')
    for x in rows:
        o,h,l,c=(float(x[k]) for k in ('open','high','low','close'))
        if not all(isfinite(v) for v in (o,h,l,c)) or not 0<l<=min(o,c)<=max(o,c)<=h: raise ValueError('value')

def event_signals(records):
    ids={}; grouped={}
    for x in records:
        if not all(x.get(k) is not None for k in ('id','date','ledger_index','tx_hash')): continue
        item=(x['date'],int(x['ledger_index']),x['tx_hash'],x.get('name'))
        if x['id'] in ids and ids[x['id']]!=item: raise ValueError('conflicting amendment id')
        ids[x['id']]=item
    for ident,(date,ledger,tx,name) in ids.items():
        import datetime as dt
        ts=int(dt.datetime.fromisoformat(date.replace('Z','+00:00')).timestamp()*1000)
        day=ts//DAY*DAY; entry=(ts//DAY+1)*DAY
        g=grouped.setdefault(entry,dict(activation_day=day,latest_activation_timestamp=ts,names=[],ids=[],ledger_indices=[],tx_hashes=[]))
        g['latest_activation_timestamp']=max(g['latest_activation_timestamp'],ts);g['names'].append(name);g['ids'].append(ident);g['ledger_indices'].append(ledger);g['tx_hashes'].append(tx)
    for g in grouped.values():
        for k in ('names','ids','ledger_indices','tx_hashes'):g[k]=sorted(g[k])
    return grouped

def atr(rows,i,n):
    if i<n+1:return None
    if any(rows[j]['timestamp']-rows[j-1]['timestamp']!=DAY for j in range(i-n,i)):return None
    vals=[]
    for j in range(i-n,i):
        p=rows[j-1]['close'];vals.append(max(rows[j]['high']-rows[j]['low'],abs(rows[j]['high']-p),abs(rows[j]['low']-p)))
    return sum(vals)/n

def backtest(rows,start,end,config=Config(),initial=10000.):
    validate_prices(rows);equity=initial;trades=[];curve=[dict(timestamp=start,equity=initial)];i=0
    while i<len(rows):
        b=rows[i];sig=b.get('activation_signal');a=atr(rows,i,config.atr_n)
        if not sig or not(start<=b['timestamp']<end) or a is None or not sig['latest_activation_timestamp']<b['timestamp']:
            i+=1;continue
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
            trades.append(dict(activation_day=sig['activation_day'],latest_activation_timestamp=sig['latest_activation_timestamp'],names=sig['names'],ids=sig['ids'],ledger_indices=sig['ledger_indices'],tx_hashes=sig['tx_hashes'],entry_timestamp=b['timestamp'],exit_timestamp=exit_time,entry_index=i,exit_index=exit_i,entry_equity=entry_equity,raw_entry=raw_entry,raw_exit=raw_exit,entry=entry,exit=exit_fill,qty=qty,atr=a,stop=stop,target=target,leg_notional=qty*entry,gross=gross,slippage_cost=gross-fill_pnl,fees=fees,pnl=pnl,equity=equity,reason=reason));curve.append(dict(timestamp=exit_time,equity=equity));i=exit_i+1;break
        else:i+=1
    return trades,curve
