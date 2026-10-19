"""Offline candle research engine. No exchange, DB, service or order interfaces."""
import math


def ema(values,n):
 out=[];v=None;a=2/(n+1)
 for x in values:
  v=x if v is None else a*x+(1-a)*v;out.append(v)
 return out


def features(rows):
 c=[float(r[4]) for r in rows];h=[float(r[2]) for r in rows];l=[float(r[3]) for r in rows]
 e20,e50=ema(c,20),ema(c,50);atr=[];v=None
 for i in range(len(rows)):
  tr=max(h[i]-l[i],abs(h[i]-c[i-1]) if i else 0,abs(l[i]-c[i-1]) if i else 0)
  v=tr if v is None else (v*13+tr)/14;atr.append(v)
 # Hourly EMA only changes at the close of the last 15m candle in an hour.
 trend=[];hours=0;v20=v50=None;direction=0
 for i,r in enumerate(rows):
  if (int(r[6])+1)%3600000==0:
   hours+=1;x=c[i];v20=x if v20 is None else 2/21*x+19/21*v20;v50=x if v50 is None else 2/51*x+49/51*v50
   direction=(1 if x>v20>v50 else -1 if x<v20<v50 else 0) if hours>=50 else 0
  trend.append(direction)
 return dict(close=c,high=h,low=l,ema20=e20,ema50=e50,atr=atr,trend=trend)


def signals(rows,kind,p):
 f=features(rows);out=[0]*len(rows);armed=None
 for i in range(max(200,p['lookback']),len(rows)):
  c=f['close'][i];o=float(rows[i][1]);atr=f['atr'][i];side=f['trend'][i]
  hi=max(f['high'][i-p['lookback']:i]);lo=min(f['low'][i-p['lookback']:i])
  breakout=1 if c>hi and side==1 else -1 if c<lo and side==-1 else 0
  if kind=='breakout_reference':out[i]=breakout
  elif kind=='breakout_retest':
   if armed and (i>armed['expires'] or side!=armed['side']):armed=None
   if armed:
    d=armed['side'];level=armed['level'];tol=p['retest_tolerance_atr']*atr
    valid=(f['low'][i]<=level+tol and level<c<=level+atr and c>o) if d==1 else (f['high'][i]>=level-tol and level-atr<=c<level and c<o)
    if valid:out[i]=d;armed=None
   elif breakout:armed=dict(side=breakout,level=hi if breakout==1 else lo,expires=i+p['retest_expiry_bars'])
  elif kind=='ema_cross_reference':
   if side==1 and f['ema20'][i]>f['ema50'][i] and f['ema20'][i-1]<=f['ema50'][i-1]:out[i]=1
   if side==-1 and f['ema20'][i]<f['ema50'][i] and f['ema20'][i-1]>=f['ema50'][i-1]:out[i]=-1
  elif kind=='ema_pullback':
   if side==1 and f['ema20'][i]>f['ema50'][i] and c>f['high'][i-1] and c>f['ema20'][i] and any(f['low'][j]<=f['ema20'][j] for j in range(i-2,i+1)):out[i]=1
   if side==-1 and f['ema20'][i]<f['ema50'][i] and c<f['low'][i-1] and c<f['ema20'][i] and any(f['high'][j]>=f['ema20'][j] for j in range(i-2,i+1)):out[i]=-1
  else:raise ValueError('Unknown strategy')
 return out,f['atr']


def open_position(side,price,atr,p,slip):
 entry=price*(1+side*slip);distance=atr*p['stop_atr']
 if distance<=0 or entry-distance*p['stop_multiplier']<=0:return None
 return dict(side=side,entry=entry,qty=p['notional']/entry,
             stop=entry-side*distance*p['stop_multiplier'],target=entry+side*distance*p['gross_reward_multiple'])


def pnl(position,market,fee,slip):
 x=market*(1-position['side']*slip);q=position['qty'];e=position['entry']
 gross=position['side']*(x-e)*q;fees=(e+x)*q*fee
 return gross-fees,fees,gross


def exit_price(pos,bar):
 o,h,l=map(float,bar[1:4]);s,t=pos['stop'],pos['target'];long=pos['side']==1
 if (o<=s if long else o>=s):return o,'STOP_GAP'
 if (l<=s if long else h>=s):return s,'STOP'
 if (h>=t if long else l<=t):return t,'TARGET'
 return None,None


def replay(rows,signal,atr,start,end,p,slip):
 cash=p['starting_balance'];peak=cash;max_dd=0.;position=None;trades=[];last=None
 def close(price,reason,stamp):
  nonlocal position,cash
  net,fees,gross=pnl(position,price,p['fee_per_side'],slip)
  cash+=net+position['entry_fee']
  trades.append(dict(**position,exit_market=price,closed_at=stamp,reason=reason,net_pnl=net,fees=fees,gross_pnl=gross))
  position=None
 for i,bar in enumerate(rows):
  now=int(bar[0])
  if now<start or now>=end:continue
  last=bar;had=position is not None
  # Prior CLOSED bar signal only; no same-bar high/low leaks into the entry.
  if not had and i>0 and signal[i-1] and cash>=p['notional']:
   position=open_position(signal[i-1],float(bar[1]),atr[i-1],p,slip)
   if position:
    position.update(opened_at=now,entry_fee=p['notional']*p['fee_per_side']);cash-=position['entry_fee']
  if position:
   price,reason=exit_price(position,bar)
   if price is not None:close(price,reason,int(bar[6]))
  equity=cash
  if position:equity+=pnl(position,float(bar[4]),p['fee_per_side'],slip)[0]+position['entry_fee']
  peak=max(peak,equity);max_dd=max(max_dd,(peak-equity)/peak*100)
 if position:
  close(float(last[4]),'PERIOD_END',end)
  peak=max(peak,cash);max_dd=max(max_dd,(peak-cash)/peak*100)
 net=cash-p['starting_balance'];assert abs(net-sum(t['net_pnl'] for t in trades))<1e-7
 gp=sum(max(t['net_pnl'],0) for t in trades);gl=-sum(min(t['net_pnl'],0) for t in trades)
 return dict(trades=len(trades),net_pnl=net,fees=sum(t['fees'] for t in trades),profit_factor=gp/gl if gl else None,
             win_rate=sum(t['net_pnl']>0 for t in trades)/len(trades) if trades else 0,
             max_close_marked_drawdown_pct=max_dd,period_end_exits=sum(t['reason']=='PERIOD_END' for t in trades)),trades
