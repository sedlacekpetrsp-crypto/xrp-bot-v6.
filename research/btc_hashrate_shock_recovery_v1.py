"""Frozen BTC hashrate recovery signal and XRP simulator."""
from dataclasses import dataclass
import math,statistics
DAY=86_400_000
@dataclass(frozen=True)
class Config:
    lookback:int=30;z_limit:float=-1.;atr_n:int=14;stop_atr:float=2.;reward_r:float=3.;max_hold:int=7;risk_fraction:float=.005;notional_cap:float=.20;fee:float=.00095;slippage:float=.00020
def make_signals(metric,c=Config()):
    for a,b in zip(metric,metric[1:]):
        if b['timestamp']-a['timestamp']!=DAY:raise ValueError('metric gap')
    out={}
    for i in range(c.lookback+1,len(metric)):
        w=[float(x['hashrate']) for x in metric[i-c.lookback-1:i-1]];mean=statistics.mean(w);sd=statistics.pstdev(w);shock=float(metric[i-1]['hashrate']);current=float(metric[i]['hashrate'])
        if sd>0 and (shock-mean)/sd<=c.z_limit and current>shock:
            t=metric[i]['timestamp'];out[t+2*DAY]=dict(metric_timestamp=t,prior_timestamp=metric[i-1]['timestamp'],hashrate=current,shock_hashrate=shock,mean30=mean,sd30=sd,zscore=(shock-mean)/sd)
    return out
def validate(rows):
    for i,x in enumerate(rows):
        if i and x['timestamp']-rows[i-1]['timestamp']!=DAY:raise ValueError('price gap')
        if not 0<x['low']<=min(x['open'],x['close'])<=max(x['open'],x['close'])<=x['high']:raise ValueError('OHLC')
def atr(rows,i,n):
    if i<n+1:return None
    return sum(max(rows[j]['high']-rows[j]['low'],abs(rows[j]['high']-rows[j-1]['close']),abs(rows[j]['low']-rows[j-1]['close'])) for j in range(i-n,i))/n
def backtest(rows,start,end,c=Config(),initial=10000.):
    validate(rows);equity=initial;trades=[];curve=[dict(timestamp=start,equity=initial)];i=0
    while i<len(rows):
        b=rows[i];s=b.get('hashrate_signal');a=atr(rows,i,c.atr_n)
        if not s or not(start<=b['timestamp']<end) or a is None or s['metric_timestamp']+2*DAY!=b['timestamp']:i+=1;continue
        raw=b['open'];entry=raw*(1+c.slippage);stop=entry-c.stop_atr*a
        if stop<=0:i+=1;continue
        qty=min(equity*c.risk_fraction/(entry-stop),equity*c.notional_cap/entry);target=entry+c.reward_r*(entry-stop);entry_fee=qty*entry*c.fee;before=equity;j=i
        while j<len(rows) and rows[j]['timestamp']<end:
            x=rows[j]
            if j>i and x['timestamp']-rows[j-1]['timestamp']!=DAY:raw_exit,reason,ei,et=rows[j-1]['close'],'DATA_GAP',j-1,rows[j-1]['timestamp']
            elif x['open']<=stop:raw_exit,reason,ei,et=x['open'],'GAP_STOP',j,x['timestamp']
            elif x['low']<=stop:raw_exit,reason,ei,et=stop,'STOP',j,x['timestamp']
            elif x['open']>=target or x['high']>=target:raw_exit,reason,ei,et=target,'TARGET',j,x['timestamp']
            elif j-i+1>=c.max_hold:raw_exit,reason,ei,et=x['close'],'TIME',j,x['timestamp']
            else:
                mark=x['low']*(1-c.slippage);curve.append(dict(timestamp=x['timestamp'],equity=before+qty*(mark-entry)-entry_fee-qty*mark*c.fee));j+=1;continue
            fill=raw_exit*(1-c.slippage);exit_fee=qty*fill*c.fee;gross=qty*(raw_exit-raw);fill_pnl=qty*(fill-entry);fees=entry_fee+exit_fee;pnl=fill_pnl-fees;equity+=pnl
            trades.append(dict(metric_timestamp=s['metric_timestamp'],prior_timestamp=s['prior_timestamp'],entry_timestamp=b['timestamp'],exit_timestamp=et,entry_index=i,exit_index=ei,entry_equity=before,hashrate=s['hashrate'],shock_hashrate=s['shock_hashrate'],mean30=s['mean30'],sd30=s['sd30'],zscore=s['zscore'],raw_entry=raw,raw_exit=raw_exit,entry=entry,exit=fill,qty=qty,atr=a,stop=stop,target=target,leg_notional=qty*entry,gross=gross,slippage_cost=gross-fill_pnl,fees=fees,pnl=pnl,equity=equity,reason=reason,cost_fee=c.fee,cost_slippage=c.slippage));curve.append(dict(timestamp=et,equity=equity));i=ei+1;break
        else:i+=1
    return trades,curve
