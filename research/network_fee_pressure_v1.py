"""Frozen XRP ledger fee-pressure simulator (offline only)."""
from dataclasses import dataclass
from math import ceil,isfinite
DAY=86_400_000
@dataclass(frozen=True)
class Config:
 lookback:int=90;percentile:float=.85;atr_n:int=14;stop_atr:float=1.5;reward_r:float=2.;max_hold:int=5;risk_fraction:float=.005;notional_cap:float=.20;fee:float=.00095;slippage:float=.00020
def validate(rows):
 ts=[x['timestamp'] for x in rows]
 if any(t%DAY for t in ts) or any(b<=a for a,b in zip(ts,ts[1:])):raise ValueError('timestamp')
 for x in rows:
  o,h,l,c=(float(x[k]) for k in ('open','high','low','close'))
  if not all(isfinite(v) for v in (o,h,l,c)) or not 0<l<=min(o,c)<=max(o,c)<=h:raise ValueError('OHLC')
  if x['fee_total']<=0 or x['transfer_count']<=0:raise ValueError('metric')
def rank(v,p):
 s=sorted(v);return s[ceil(p*len(s))-1]
def pressure(x):return x['fee_total']/x['transfer_count']
def signal_at(rows,i,c=Config()):
 k=i-1
 if k-c.lookback<0:return False
 seq=rows[k-c.lookback:i+1]
 if any(b['timestamp']-a['timestamp']!=DAY for a,b in zip(seq,seq[1:])):return False
 return pressure(rows[k])>=rank([pressure(x) for x in rows[k-c.lookback:k]],c.percentile)
def atr(rows,i,n):
 if i<n:return None
 v=[]
 for j in range(i-n+1,i+1):
  pc=rows[j-1]['close'];v.append(max(rows[j]['high']-rows[j]['low'],abs(rows[j]['high']-pc),abs(rows[j]['low']-pc)))
 return sum(v)/n
def backtest(rows,start,end,c=Config(),initial=10000.):
 validate(rows);equity=initial;trades=[];curve=[{'timestamp':start,'equity':initial}];i=0
 while i+1<len(rows):
  s,e=rows[i],rows[i+1];a=atr(rows,i,c.atr_n)
  if s['timestamp']<start or e['timestamp']>=end or e['timestamp']-s['timestamp']!=DAY or a is None or not signal_at(rows,i,c):i+=1;continue
  re=e['open'];entry=re*(1+c.slippage);stop=entry-c.stop_atr*a
  if stop<=0:i+=1;continue
  risk=entry-stop;qty=min(equity*c.risk_fraction/risk,equity*c.notional_cap/entry);target=entry+c.reward_r*risk;ef=qty*entry*c.fee;ee=equity;j=i+1;closed=False
  while j<len(rows) and rows[j]['timestamp']<end:
   b=rows[j]
   if j>i+1 and b['timestamp']-rows[j-1]['timestamp']!=DAY:rx=rows[j-1]['close'];reason='DATA_GAP';xi=j-1;xt=rows[j-1]['timestamp']
   elif b['open']<=stop:rx=b['open'];reason='GAP_STOP';xi=j;xt=b['timestamp']
   elif b['low']<=stop:rx=stop;reason='STOP';xi=j;xt=b['timestamp']
   elif b['high']>=target:rx=target;reason='TARGET';xi=j;xt=b['timestamp']
   elif j-(i+1)>=c.max_hold:rx=b['open'];reason='TIME';xi=j;xt=b['timestamp']
   else:
    mark=b['low']*(1-c.slippage);curve.append({'timestamp':b['timestamp'],'equity':ee+qty*(mark-entry)-ef-qty*mark*c.fee});j+=1;continue
   exit=rx*(1-c.slippage);xf=qty*exit*c.fee;gross=qty*(rx-re);fill=qty*(exit-entry);fees=ef+xf;pnl=fill-fees;equity+=pnl
   trades.append(dict(signal_timestamp=s['timestamp'],metric_timestamp=rows[i-1]['timestamp'],entry_timestamp=e['timestamp'],exit_timestamp=xt,entry_index=i+1,exit_index=xi,entry_equity=ee,raw_entry=re,raw_exit=rx,entry=entry,exit=exit,qty=qty,atr=a,stop=stop,target=target,signal_pressure=pressure(rows[i-1]),leg_notional=qty*entry,gross=gross,slippage_cost=gross-fill,fees=fees,pnl=pnl,equity=equity,reason=reason));curve.append({'timestamp':xt,'equity':equity});i=xi;closed=True;break
  if not closed:
   xi=min(j-1,len(rows)-1);b=rows[xi];rx=b['close'];exit=rx*(1-c.slippage);xf=qty*exit*c.fee;gross=qty*(rx-re);fill=qty*(exit-entry);fees=ef+xf;pnl=fill-fees;equity+=pnl
   trades.append(dict(signal_timestamp=s['timestamp'],metric_timestamp=rows[i-1]['timestamp'],entry_timestamp=e['timestamp'],exit_timestamp=b['timestamp'],entry_index=i+1,exit_index=xi,entry_equity=ee,raw_entry=re,raw_exit=rx,entry=entry,exit=exit,qty=qty,atr=a,stop=stop,target=target,signal_pressure=pressure(rows[i-1]),leg_notional=qty*entry,gross=gross,slippage_cost=gross-fill,fees=fees,pnl=pnl,equity=equity,reason='END'));curve.append({'timestamp':b['timestamp'],'equity':equity});i=xi
  i+=1
 return trades,curve
