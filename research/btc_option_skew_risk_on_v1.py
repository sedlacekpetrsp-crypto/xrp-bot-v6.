"""Frozen option-skew signal and XRP execution mechanics."""
from dataclasses import dataclass
import datetime as dt,math,re,statistics
DAY=86_400_000;UTC=dt.timezone.utc
PATTERN=re.compile(r'^BTC-(\d{1,2}[A-Z]{3}\d{2})-(\d+(?:\.\d+)?)-([CP])$')

@dataclass(frozen=True)
class Config:
    maturity_min:int=14;maturity_max:int=60;delta_min:float=.15;delta_max:float=.35;min_trades:int=5;min_amount:float=1.;atr_n:int=14;stop_atr:float=2.;reward_r:float=3.;max_hold:int=7;risk_fraction:float=.005;notional_cap:float=.20;fee:float=.00095;slippage:float=.00020

def option_trade(x,c=Config()):
    m=PATTERN.match(str(x.get('instrument_name','')));iv=float(x.get('iv') or 0);spot=float(x.get('index_price') or 0)
    if not m or iv<=0 or spot<=0:return None
    expiry=dt.datetime.strptime(m.group(1),'%d%b%y').replace(tzinfo=UTC,hour=8);tau=(expiry.timestamp()*1000-int(x['timestamp']))/(365*DAY)
    if not c.maturity_min/365<=tau<=c.maturity_max/365:return None
    sigma=iv/100;strike=float(m.group(2));d1=(math.log(spot/strike)+.5*sigma*sigma*tau)/(sigma*math.sqrt(tau));n=.5*(1+math.erf(d1/math.sqrt(2)));side=m.group(3);delta=n if side=='C' else n-1
    if not c.delta_min<=abs(delta)<=c.delta_max:return None
    return dict(trade_id=str(x['trade_id']),timestamp=int(x['timestamp']),side=side,iv=iv,delta=delta,maturity_days=tau*365,amount=float(x.get('amount') or 0),instrument_name=x['instrument_name'])

def skew_observation(trades,friday_midnight,c=Config()):
    unique={str(x['trade_id']):x for x in trades};valid=[z for x in unique.values() if (z:=option_trade(x,c))];calls=[x for x in valid if x['side']=='C'];puts=[x for x in valid if x['side']=='P']
    base=dict(friday_timestamp=friday_midnight,window_start=friday_midnight+12*3_600_000,window_end=friday_midnight+13*3_600_000-1,raw_trades=len(unique),eligible_calls=len(calls),eligible_puts=len(puts),call_amount=sum(x['amount'] for x in calls),put_amount=sum(x['amount'] for x in puts))
    if len(calls)<c.min_trades or len(puts)<c.min_trades or base['call_amount']<c.min_amount or base['put_amount']<c.min_amount:return dict(base,eligible=False,reason='insufficient_sides')
    call=statistics.median(x['iv'] for x in calls);put=statistics.median(x['iv'] for x in puts);rr=call-put
    return dict(base,eligible=True,reason='ok',call_median_iv=call,put_median_iv=put,risk_reversal=rr,signal=rr>0,entry_timestamp=friday_midnight+3*DAY)

def validate_prices(rows):
    for i,x in enumerate(rows):
        if i and x['timestamp']-rows[i-1]['timestamp']!=DAY:raise ValueError('daily gap or duplicate')
        if not 0<x['low']<=min(x['open'],x['close'])<=max(x['open'],x['close'])<=x['high']:raise ValueError('invalid OHLC')
def atr(rows,i,n):
    if i<n+1:return None
    return sum(max(rows[j]['high']-rows[j]['low'],abs(rows[j]['high']-rows[j-1]['close']),abs(rows[j]['low']-rows[j-1]['close'])) for j in range(i-n,i))/n
def backtest(rows,start,end,c=Config(),initial=10_000.):
    validate_prices(rows);equity=initial;trades=[];curve=[dict(timestamp=start,equity=initial)];i=0
    while i<len(rows):
        b=rows[i];s=b.get('skew_signal');a=atr(rows,i,c.atr_n)
        if not s or not s.get('signal') or not(start<=b['timestamp']<end) or a is None or s['entry_timestamp']!=b['timestamp'] or s['window_end']>=b['timestamp']:i+=1;continue
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
            trades.append(dict(friday_timestamp=s['friday_timestamp'],window_end=s['window_end'],risk_reversal=s['risk_reversal'],call_median_iv=s['call_median_iv'],put_median_iv=s['put_median_iv'],eligible_calls=s['eligible_calls'],eligible_puts=s['eligible_puts'],entry_timestamp=b['timestamp'],exit_timestamp=et,entry_index=i,exit_index=ei,entry_equity=before,raw_entry=raw,raw_exit=raw_exit,entry=entry,exit=fill,qty=qty,atr=a,stop=stop,target=target,leg_notional=qty*entry,gross=gross,slippage_cost=gross-fill_pnl,fees=fees,pnl=pnl,equity=equity,reason=reason,cost_fee=c.fee,cost_slippage=c.slippage));curve.append(dict(timestamp=et,equity=equity));i=ei+1;break
        else:i+=1
    return trades,curve
