"""Frozen weekly inverse-volatility basket mechanics."""
from dataclasses import dataclass
import math

DAY=86_400_000

@dataclass(frozen=True)
class Config:
    lookback:int=30
    atr_period:int=14
    stop_atr:float=3.0
    max_weight:float=0.50
    fee:float=0.00095
    slippage:float=0.00020

def validate_markets(markets):
    if len(markets)!=3: raise ValueError('exactly three markets required')
    calendars=[]
    for symbol,rows in markets.items():
        ts=[]
        for i,b in enumerate(rows):
            if not (b['low']<=min(b['open'],b['close'])<=max(b['open'],b['close'])<=b['high']): raise ValueError(symbol+' invalid OHLC')
            if b['low']<=0: raise ValueError(symbol+' nonpositive price')
            if i and b['timestamp']-rows[i-1]['timestamp']!=DAY: raise ValueError(symbol+' daily gap or duplicate')
            ts.append(b['timestamp'])
        calendars.append(ts)
    if any(x!=calendars[0] for x in calendars[1:]): raise ValueError('unaligned market calendars')

def _vol(rows,i,n):
    if i<n+1:return None
    closes=[x['close'] for x in rows[i-n-1:i]]
    r=[math.log(b/a) for a,b in zip(closes,closes[1:])]
    mean=sum(r)/len(r)
    var=sum((x-mean)**2 for x in r)/(len(r)-1)
    return math.sqrt(var)*math.sqrt(365)

def _atr(rows,i,n):
    if i<n+1:return None
    tr=[]
    for j in range(i-n,i):
        b=rows[j];p=rows[j-1]['close'];tr.append(max(b['high']-b['low'],abs(b['high']-p),abs(b['low']-p)))
    return sum(tr)/n

def capped_inverse_vol_weights(vols,cap=.5):
    if not vols or any((not math.isfinite(v) or v<=0) for v in vols.values()): raise ValueError('positive finite vol required')
    if cap*len(vols)<1-1e-12: raise ValueError('infeasible cap')
    inv={k:1/v for k,v in vols.items()};weights={};free=set(inv);remaining=1.0
    while free:
        denom=sum(inv[k] for k in free);trial={k:remaining*inv[k]/denom for k in free};over={k for k,v in trial.items() if v>cap+1e-15}
        if not over:
            weights.update(trial);break
        for k in sorted(over): weights[k]=cap;free.remove(k);remaining-=cap
    return weights

def features(markets,i,c=Config()):
    vols={s:_vol(rows,i,c.lookback) for s,rows in markets.items()}
    atrs={s:_atr(rows,i,c.atr_period) for s,rows in markets.items()}
    if any(v is None for v in vols.values()) or any(v is None for v in atrs.values()):return None
    return capped_inverse_vol_weights(vols,c.max_weight),vols,atrs

def backtest(markets,start,end,c=Config(),initial=10_000.0):
    validate_markets(markets);symbols=sorted(markets);rows=markets[symbols[0]];cash=initial;positions={};trades=[];curve=[]
    idx=[i for i,b in enumerate(rows) if start<=b['timestamp']<end]
    if not idx:return trades,curve,[]
    last=idx[-1];events=[]
    def exit_pos(symbol,raw,ts,reason):
        nonlocal cash
        p=positions.pop(symbol);fill=raw*(1-c.slippage);notional=p['qty']*fill;exit_fee=notional*c.fee;cash+=notional-exit_fee
        pnl=p['qty']*(fill-p['entry_fill'])-p['entry_fee']-exit_fee
        t=dict(symbol=symbol,entry_timestamp=p['entry_timestamp'],exit_timestamp=ts,entry_raw=p['entry_raw'],entry_fill=p['entry_fill'],exit_raw=raw,exit_fill=fill,qty=p['qty'],target_weight=p['target_weight'],realized_vol=p['realized_vol'],atr=p['atr'],stop=p['stop'],entry_fee=p['entry_fee'],exit_fee=exit_fee,fees=p['entry_fee']+exit_fee,slippage_cost=p['qty']*((p['entry_fill']-p['entry_raw'])+(raw-fill)),pnl=pnl,exit_reason=reason,cost_fee=c.fee,cost_slippage=c.slippage)
        trades.append(t);events.append(dict(timestamp=ts,kind='exit',symbol=symbol,cash=cash));return t
    for i in idx:
        ts=rows[i]['timestamp'];day={s:markets[s][i] for s in symbols}
        # Existing gap stops execute before a scheduled rebalance at the same open.
        for s in list(positions):
            if day[s]['open']<=positions[s]['stop']:exit_pos(s,day[s]['open'],ts,'gap_stop')
        monday=(ts//DAY+3)%7==0  # 1970-01-01 was Thursday
        f=features(markets,i,c) if monday else None
        if monday and f:
            for s in list(positions):exit_pos(s,day[s]['open'],ts,'weekly_rebalance')
            weights,vols,atrs=f;available=cash;investable=available/(1+c.fee)
            for s in symbols:
                raw=day[s]['open'];fill=raw*(1+c.slippage);budget=investable*weights[s];qty=budget/fill;entry_fee=budget*c.fee;cash-=budget+entry_fee
                positions[s]=dict(entry_timestamp=ts,entry_raw=raw,entry_fill=fill,qty=qty,target_weight=weights[s],realized_vol=vols[s],atr=atrs[s],stop=fill-c.stop_atr*atrs[s],entry_fee=entry_fee)
                events.append(dict(timestamp=ts,kind='entry',symbol=s,cash=cash,target_weight=weights[s]))
        # Intraday stop after any Monday entries; stop price is known at entry.
        for s in list(positions):
            p=positions[s]
            if day[s]['low']<=p['stop']:exit_pos(s,p['stop'],ts,'stop')
        low_equity=cash;close_equity=cash
        for s,p in positions.items():
            low=day[s]['low']*(1-c.slippage);close=day[s]['close']*(1-c.slippage)
            low_equity+=p['qty']*low*(1-c.fee);close_equity+=p['qty']*close*(1-c.fee)
        curve.append(dict(timestamp=ts,equity=close_equity,conservative_equity=low_equity,cash=cash,positions=len(positions)))
        if i==last:
            for s in list(positions):exit_pos(s,day[s]['close'],ts,'segment_end')
            curve.append(dict(timestamp=ts,equity=cash,conservative_equity=cash,cash=cash,positions=0))
    return trades,curve,events
