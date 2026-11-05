"""Frozen bank-credit/XRP PAPER simulator."""
from dataclasses import dataclass
from math import isfinite

DAY = 86_400_000

@dataclass(frozen=True)
class Config:
    macro_lookback: int = 13
    release_lag: int = 2
    minimum_growth: float = 0.015
    atr_n: int = 14
    stop_atr: float = 2.0
    reward_r: float = 3.0
    max_hold: int = 7
    risk_fraction: float = .005
    notional_cap: float = .20
    fee: float = .00095
    slippage: float = .00020

def validate_prices(rows):
    times = [x['timestamp'] for x in rows]
    if any(t % DAY for t in times) or any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError('timestamp')
    for row in rows:
        o,h,l,c = (float(row[k]) for k in ('open','high','low','close'))
        if not all(isfinite(v) for v in (o,h,l,c)) or not 0 < l <= min(o,c) <= max(o,c) <= h:
            raise ValueError('price')

def make_signals(macro, config=Config()):
    times = [x['timestamp'] for x in macro]
    if any(b <= a for a,b in zip(times,times[1:])): raise ValueError('macro timestamp')
    if any(not isfinite(float(x['value'])) or float(x['value']) <= 0 for x in macro): raise ValueError('macro value')
    out = {}
    for eligible_i in range(config.release_lag + config.macro_lookback, len(macro)):
        latest_i = eligible_i - config.release_lag; earlier_i = latest_i - config.macro_lookback
        latest = float(macro[latest_i]['value']); earlier = float(macro[earlier_i]['value'])
        growth = latest / earlier - 1
        if growth >= config.minimum_growth:
            out[macro[eligible_i]['timestamp']] = dict(metric_timestamp=macro[latest_i]['timestamp'], earlier_timestamp=macro[earlier_i]['timestamp'], latest_credit=latest, earlier_credit=earlier, credit_growth=growth)
    return out

def atr(rows, index, length):
    if index < length: return None
    if any(rows[j]['timestamp'] - rows[j-1]['timestamp'] != DAY for j in range(index-length+1,index+1)): return None
    values=[]
    for j in range(index-length+1,index+1):
        p=rows[j-1]['close']; values.append(max(rows[j]['high']-rows[j]['low'],abs(rows[j]['high']-p),abs(rows[j]['low']-p)))
    return sum(values)/length

def _trade(signal, entry_bar, rows, i, end, equity, config, volatility):
    raw_entry=entry_bar['open']; entry=raw_entry*(1+config.slippage); stop=entry-config.stop_atr*volatility
    if stop <= 0: return None
    qty=min(equity*config.risk_fraction/(entry-stop),equity*config.notional_cap/entry); target=entry+config.reward_r*(entry-stop)
    entry_fee=qty*entry*config.fee; j=i+1
    while j < len(rows) and rows[j]['timestamp'] < end:
        bar=rows[j]
        if j>i+1 and bar['timestamp']-rows[j-1]['timestamp']!=DAY: raw_exit,reason,exit_i,exit_time=rows[j-1]['close'],'DATA_GAP',j-1,rows[j-1]['timestamp']
        elif bar['open']<=stop: raw_exit,reason,exit_i,exit_time=bar['open'],'GAP_STOP',j,bar['timestamp']
        elif bar['low']<=stop: raw_exit,reason,exit_i,exit_time=stop,'STOP',j,bar['timestamp']
        elif bar['open']>=target or bar['high']>=target: raw_exit,reason,exit_i,exit_time=target,'TARGET',j,bar['timestamp']
        elif j-(i+1)>=config.max_hold: raw_exit,reason,exit_i,exit_time=bar['open'],'TIME',j,bar['timestamp']
        else: j+=1; continue
        break
    else:
        exit_i=min(j-1,len(rows)-1); bar=rows[exit_i]; raw_exit,reason,exit_time=bar['close'],'FOLD_END',bar['timestamp']
    exit_fill=raw_exit*(1-config.slippage); exit_fee=qty*exit_fill*config.fee
    gross=qty*(raw_exit-raw_entry); fill=qty*(exit_fill-entry); fees=entry_fee+exit_fee; pnl=fill-fees
    return dict(signal_timestamp=signal['timestamp'],metric_timestamp=signal['metric_timestamp'],earlier_timestamp=signal['earlier_timestamp'],entry_timestamp=entry_bar['timestamp'],exit_timestamp=exit_time,entry_index=i+1,exit_index=exit_i,entry_equity=equity,raw_entry=raw_entry,raw_exit=raw_exit,entry=entry,exit=exit_fill,qty=qty,atr=volatility,stop=stop,target=target,earlier_credit=signal['earlier_credit'],latest_credit=signal['latest_credit'],credit_growth=signal['credit_growth'],leg_notional=qty*entry,gross=gross,slippage_cost=gross-fill,fees=fees,pnl=pnl,equity=equity+pnl,reason=reason)

def backtest(rows,start,end,config=Config(),initial=10_000.):
    validate_prices(rows); equity=initial; trades=[]; curve=[{'timestamp':start,'equity':initial}]; i=0
    while i+1<len(rows):
        signal,entry=rows[i],rows[i+1]; volatility=atr(rows,i,config.atr_n)
        eligible=(start<=signal['timestamp'] and entry['timestamp']<end and entry['timestamp']-signal['timestamp']==DAY and signal.get('macro_signal') and volatility is not None)
        if not eligible: i+=1; continue
        trade=_trade(signal,entry,rows,i,end,equity,config,volatility)
        if trade:
            trades.append(trade); equity=trade['equity']; curve.append({'timestamp':trade['exit_timestamp'],'equity':equity}); i=trade['exit_index']
        i+=1
    return trades,curve
