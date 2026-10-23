"""Long-only BTC resting-limit range-harvest backtest."""
from bisect import bisect_left
from dataclasses import dataclass, replace
from math import isfinite, log

HOUR_MS=3_600_000; DAY_MS=86_400_000

@dataclass(frozen=True)
class Config:
    regime_days:int=20
    maximum_efficiency:float=0.35
    entry_atr:float=0.50
    stop_atr:float=1.00
    maximum_hold_hours:int=24
    position_fraction:float=0.25
    entry_fee:float=0.00020
    exit_fee:float=0.00095
    entry_slippage:float=0.0
    exit_slippage:float=0.00020
    initial_equity:float=10_000.0

def validate(bars):
    stamps=[]
    for bar in bars:
        vals=[bar[k] for k in ('open','high','low','close','volume')]
        if not all(isfinite(v) for v in vals): raise ValueError('Non-finite input')
        if not (0<bar['low']<=min(bar['open'],bar['close'])<=max(bar['open'],bar['close'])<=bar['high']):
            raise ValueError('Invalid OHLC')
        if bar['volume']<0 or bar['timestamp']%HOUR_MS: raise ValueError('Invalid timestamp or volume')
        stamps.append(bar['timestamp'])
    if any(stamps[i]<=stamps[i-1] or (stamps[i]-stamps[i-1])%HOUR_MS for i in range(1,len(stamps))):
        raise ValueError('Unordered timestamps')

def daily_bars(bars):
    grouped={}
    for bar in bars: grouped.setdefault(bar['timestamp']//DAY_MS*DAY_MS,[]).append(bar)
    result=[]
    for day in sorted(grouped):
        part=grouped[day]
        if [b['timestamp'] for b in part]!=list(range(day,day+DAY_MS,HOUR_MS)): continue
        result.append({'timestamp':day,'open':part[0]['open'],'high':max(b['high'] for b in part),
                       'low':min(b['low'] for b in part),'close':part[-1]['close']})
    return result

def setup(days,completed,config=Config()):
    first=completed-config.regime_days+1
    if first<1: return None
    if days[completed]['timestamp']-days[first-1]['timestamp']!=config.regime_days*DAY_MS: return None
    returns=[log(days[i]['close']/days[i-1]['close']) for i in range(first,completed+1)]
    path=sum(abs(v) for v in returns)
    efficiency=abs(sum(returns))/path if path else 1.0
    if efficiency>config.maximum_efficiency: return None
    true_ranges=[]
    for i in range(first,completed+1):
        previous=days[i-1]['close']; day=days[i]
        true_ranges.append(max(day['high']-day['low'],abs(day['high']-previous),abs(day['low']-previous)))
    atr=sum(true_ranges)/len(true_ranges)
    fair=days[completed]['close']; entry=fair-config.entry_atr*atr
    if entry<=0 or atr<=0: return None
    return {'fair':fair,'atr':atr,'entry':entry,'stop':entry-config.stop_atr*atr,
            'target':fair,'efficiency':efficiency}

def backtest(bars,start_ts,end_ts,config=Config()):
    validate(bars); days=daily_bars(bars); day_stamps=[d['timestamp'] for d in days]
    equity=config.initial_equity; peak=equity; max_drawdown=0.0
    pending=None; position=None; trades=[]; last_index=None

    def close(raw,timestamp,reason):
        nonlocal equity,position
        fill=raw*(1-config.exit_slippage); gross=position['quantity']*(fill-position['entry'])
        exit_fee=position['quantity']*fill*config.exit_fee; equity+=gross-exit_fee
        net=gross-position['entry_fee']-exit_fee
        trades.append({'entry_ts':position['entry_ts'],'exit_ts':timestamp,'entry':position['entry'],
                       'exit':fill,'stop':position['stop'],'target':position['target'],'reason':reason,
                       'gross_pnl':gross,'fees':position['entry_fee']+exit_fee,'net_pnl':net,
                       'return_on_equity':net/position['equity_before']})
        position=None

    def mark(i):
        nonlocal peak,max_drawdown
        marked=equity+(position['quantity']*(bars[i]['close']-position['entry']) if position else 0)
        peak=max(peak,marked); max_drawdown=max(max_drawdown,(peak-marked)/peak)

    for i,bar in enumerate(bars):
        ts=bar['timestamp']
        if ts<start_ts: continue
        if ts>=end_ts: break
        last_index=i
        if position:
            if bar['open']<=position['stop']: close(bar['open'],ts,'GAP_STOP')
            elif bar['open']>=position['target']: close(position['target'],ts,'GAP_TARGET')
        if position and ts-position['entry_ts']>=config.maximum_hold_hours*HOUR_MS: close(bar['open'],ts,'TIME')
        if position:
            if bar['low']<=position['stop']: close(position['stop'],ts,'STOP')
            elif bar['high']>=position['target']: close(position['target'],ts,'TARGET')
        if pending and ts>=pending['expires']: pending=None
        if not position and not pending and ts%DAY_MS==0:
            completed=bisect_left(day_stamps,ts)-1
            candidate=setup(days,completed,config) if completed>=0 else None
            if candidate: pending={**candidate,'expires':ts+DAY_MS}
        if not position and pending and bar['low']<=pending['entry']:
            fill=pending['entry']*(1+config.entry_slippage); notional=equity*config.position_fraction
            fee=notional*config.entry_fee; before=equity; equity-=fee
            position={'entry_ts':ts,'entry':fill,'quantity':notional/fill,
                      'stop':pending['stop'],'target':pending['target'],
                      'entry_fee':fee,'equity_before':before}
            pending=None
            # A target on the fill bar is ignored because its high may precede the limit fill.
            if bar['low']<=position['stop']: close(position['stop'],ts,'STOP')
        mark(i)
    if last_index is not None and position:
        close(bars[last_index]['close'],bars[last_index]['timestamp'],'END'); mark(last_index)
    return {'trades':trades,'ending_equity':equity,
            'net_return':equity/config.initial_equity-1,'max_drawdown':max_drawdown}

def with_taker_stress(config=Config()):
    return replace(config,entry_fee=0.00190,exit_fee=0.00190,
                   entry_slippage=0.00040,exit_slippage=0.00040)
