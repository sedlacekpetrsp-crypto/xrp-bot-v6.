"""Frozen XRP Asia-to-Europe session handoff reversal."""
from dataclasses import dataclass
import datetime as dt, math
STEP=3_600_000; UTC=dt.timezone.utc
@dataclass(frozen=True)
class Config:
    session_threshold: float=-0.015
    atr_n: int=24
    stop_atr: float=1.5
    reward_r: float=2.0
    max_hold: int=8
    risk_fraction: float=.005
    notional_cap: float=.20
    fee: float=.00095
    slippage: float=.00020
def validate(bars):
    last=None
    for b in bars:
        ts=int(b['timestamp']); vals=[float(b[k]) for k in ('open','high','low','close')]
        if ts%STEP or (last is not None and ts<=last): raise ValueError('timestamps')
        if not all(math.isfinite(x) for x in vals) or not 0<vals[2]<=min(vals[0],vals[3])<=max(vals[0],vals[3])<=vals[1]: raise ValueError('OHLC')
        last=ts
def make_signals(bars,c=Config()):
    validate(bars); by={b['timestamp']:b for b in bars}; out={}
    for b in bars:
        d=dt.datetime.fromtimestamp(b['timestamp']/1000,UTC)
        if d.hour!=0: continue
        session=[by.get(b['timestamp']+h*STEP) for h in range(8)]
        if any(x is None for x in session): continue
        ret=session[-1]['close']/session[0]['open']-1
        if ret<=c.session_threshold:
            entry=b['timestamp']+8*STEP
            if entry in by: out[entry]=dict(session_start=b['timestamp'],session_end=b['timestamp']+8*STEP,session_open=session[0]['open'],session_close=session[-1]['close'],session_return=ret)
    return out
def atr(bars,i,n):
    if i<n+1 or bars[i-1]['timestamp']-bars[i-n]['timestamp']!=(n-1)*STEP: return None
    return sum(max(bars[j]['high']-bars[j]['low'],abs(bars[j]['high']-bars[j-1]['close']),abs(bars[j]['low']-bars[j-1]['close'])) for j in range(i-n,i))/n
def backtest(bars,signals,start,end,c=Config(),initial=10_000.):
    validate(bars); equity=initial; trades=[]; curve=[dict(timestamp=start,equity=initial)]; i=0
    while i<len(bars):
        b=bars[i]; s=signals.get(b['timestamp']); av=atr(bars,i,c.atr_n)
        if not s or not(start<=b['timestamp']<end) or av is None: i+=1; continue
        if dt.datetime.fromtimestamp(b['timestamp']/1000,UTC).hour!=8 or s['session_end']!=b['timestamp']: raise ValueError('entry timing')
        raw_entry=b['open']; entry=raw_entry*(1+c.slippage); stop=entry-c.stop_atr*av
        if stop<=0: i+=1; continue
        qty=min(equity*c.risk_fraction/(entry-stop),equity*c.notional_cap/entry); target=entry+c.reward_r*(entry-stop); before=equity; entry_fee=qty*entry*c.fee; j=i
        while j<len(bars) and bars[j]['timestamp']<end:
            x=bars[j]
            if j>i and x['timestamp']-bars[j-1]['timestamp']!=STEP: raw_exit,reason,ei,et=bars[j-1]['close'],'DATA_GAP',j-1,bars[j-1]['timestamp']
            elif x['open']<=stop: raw_exit,reason,ei,et=x['open'],'GAP_STOP',j,x['timestamp']
            elif x['low']<=stop: raw_exit,reason,ei,et=stop,'STOP',j,x['timestamp']
            elif x['open']>=target or x['high']>=target: raw_exit,reason,ei,et=target,'TARGET',j,x['timestamp']
            elif j-i+1>=c.max_hold: raw_exit,reason,ei,et=x['close'],'TIME',j,x['timestamp']
            else:
                mark=x['low']*(1-c.slippage); curve.append(dict(timestamp=x['timestamp'],equity=before+qty*(mark-entry)-entry_fee-qty*mark*c.fee)); j+=1; continue
            break
        else:
            ei=min(j-1,len(bars)-1)
            if ei<i: i+=1; continue
            et,raw_exit,reason=bars[ei]['timestamp'],bars[ei]['close'],'FOLD_END'
        fill=raw_exit*(1-c.slippage); exit_fee=qty*fill*c.fee; gross=qty*(raw_exit-raw_entry); fill_pnl=qty*(fill-entry); fees=entry_fee+exit_fee; pnl=fill_pnl-fees; equity+=pnl
        trades.append(dict(**s,entry_timestamp=b['timestamp'],exit_timestamp=et,entry_index=i,exit_index=ei,entry_equity=before,raw_entry=raw_entry,raw_exit=raw_exit,entry=entry,exit=fill,qty=qty,atr=av,stop=stop,target=target,leg_notional=qty*entry,gross=gross,slippage_cost=gross-fill_pnl,fees=fees,pnl=pnl,equity=equity,reason=reason,cost_fee=c.fee,cost_slippage=c.slippage)); curve.append(dict(timestamp=et,equity=equity)); i=ei+1
    return trades,curve
