"""Frozen stablecoin-supply liquidity impulse simulator (offline only)."""
from dataclasses import dataclass
from math import ceil,isfinite
DAY=86_400_000
@dataclass(frozen=True)
class Config:
 lookback:int=180;growth_days:int=7;percentile:float=.80;min_growth:float=.005;atr_n:int=14;stop_atr:float=2.;reward_r:float=3.;max_hold:int=14;risk_fraction:float=.005;notional_cap:float=.20;fee:float=.00095;slippage:float=.00020
def validate(r):
 ts=[x['timestamp']for x in r]
 if any(t%DAY for t in ts)or any(b<=a for a,b in zip(ts,ts[1:])):raise ValueError('timestamp')
 for x in r:
  o,h,l,c=(float(x[k])for k in('open','high','low','close'))
  if not all(isfinite(v)for v in(o,h,l,c))or not 0<l<=min(o,c)<=max(o,c)<=h:raise ValueError('OHLC')
  if not isfinite(x['stable_supply'])or x['stable_supply']<=0:raise ValueError('supply')
def rank(v,p):
 s=sorted(v);return s[ceil(p*len(s))-1]
def growth(r,j,d):return r[j]['stable_supply']/r[j-d]['stable_supply']-1
def signal_at(r,i,c=Config()):
 k=i-1;first=k-c.lookback-c.growth_days
 if first<0:return False
 seq=r[first:i+1]
 if any(b['timestamp']-a['timestamp']!=DAY for a,b in zip(seq,seq[1:])):return False
 candidate=growth(r,k,c.growth_days);ref=[growth(r,j,c.growth_days)for j in range(k-c.lookback,k)]
 return candidate>=c.min_growth and candidate>=rank(ref,c.percentile)
def atr(r,i,n):
 if i<n:return None
 v=[]
 for j in range(i-n+1,i+1):
  p=r[j-1]['close'];v.append(max(r[j]['high']-r[j]['low'],abs(r[j]['high']-p),abs(r[j]['low']-p)))
 return sum(v)/n
def backtest(r,start,end,c=Config(),initial=10000.):
 validate(r);eq=initial;ts=[];curve=[{'timestamp':start,'equity':initial}];i=0
 while i+1<len(r):
  s,e=r[i],r[i+1];a=atr(r,i,c.atr_n)
  if s['timestamp']<start or e['timestamp']>=end or e['timestamp']-s['timestamp']!=DAY or a is None or not signal_at(r,i,c):i+=1;continue
  re=e['open'];en=re*(1+c.slippage);stop=en-c.stop_atr*a
  if stop<=0:i+=1;continue
  q=min(eq*c.risk_fraction/(en-stop),eq*c.notional_cap/en);target=en+c.reward_r*(en-stop);ef=q*en*c.fee;ee=eq;j=i+1;closed=False
  while j<len(r)and r[j]['timestamp']<end:
   b=r[j]
   if j>i+1 and b['timestamp']-r[j-1]['timestamp']!=DAY:rx=r[j-1]['close'];why='DATA_GAP';xi=j-1;xt=r[j-1]['timestamp']
   elif b['open']<=stop:rx=b['open'];why='GAP_STOP';xi=j;xt=b['timestamp']
   elif b['low']<=stop:rx=stop;why='STOP';xi=j;xt=b['timestamp']
   elif b['high']>=target:rx=target;why='TARGET';xi=j;xt=b['timestamp']
   elif j-(i+1)>=c.max_hold:rx=b['open'];why='TIME';xi=j;xt=b['timestamp']
   else:
    m=b['low']*(1-c.slippage);curve.append({'timestamp':b['timestamp'],'equity':ee+q*(m-en)-ef-q*m*c.fee});j+=1;continue
   ex=rx*(1-c.slippage);xf=q*ex*c.fee;gross=q*(rx-re);fill=q*(ex-en);fees=ef+xf;pnl=fill-fees;eq+=pnl;ts.append(dict(signal_timestamp=s['timestamp'],metric_timestamp=r[i-1]['timestamp'],entry_timestamp=e['timestamp'],exit_timestamp=xt,entry_index=i+1,exit_index=xi,entry_equity=ee,raw_entry=re,raw_exit=rx,entry=en,exit=ex,qty=q,atr=a,stop=stop,target=target,signal_growth=growth(r,i-1,c.growth_days),leg_notional=q*en,gross=gross,slippage_cost=gross-fill,fees=fees,pnl=pnl,equity=eq,reason=why));curve.append({'timestamp':xt,'equity':eq});i=xi;closed=True;break
  if not closed:
   xi=min(j-1,len(r)-1);b=r[xi];rx=b['close'];ex=rx*(1-c.slippage);xf=q*ex*c.fee;gross=q*(rx-re);fill=q*(ex-en);fees=ef+xf;pnl=fill-fees;eq+=pnl;ts.append(dict(signal_timestamp=s['timestamp'],metric_timestamp=r[i-1]['timestamp'],entry_timestamp=e['timestamp'],exit_timestamp=b['timestamp'],entry_index=i+1,exit_index=xi,entry_equity=ee,raw_entry=re,raw_exit=rx,entry=en,exit=ex,qty=q,atr=a,stop=stop,target=target,signal_growth=growth(r,i-1,c.growth_days),leg_notional=q*en,gross=gross,slippage_cost=gross-fill,fees=fees,pnl=pnl,equity=eq,reason='END'));curve.append({'timestamp':b['timestamp'],'equity':eq});i=xi
  i+=1
 return ts,curve
