"""Frozen policy-uncertainty easing signal with shared daily execution."""
from dataclasses import dataclass,replace
from math import isfinite
from statistics import median
from research.xrp_bank_credit_expansion_v1 import Config as ExecutionConfig,DAY,backtest as _base_backtest,validate_prices
@dataclass(frozen=True)
class SignalConfig:
    median_lookback:int=90
    trend_window:int=5
    release_lag:int=2
def make_signals(macro,config=SignalConfig()):
    times=[x['timestamp'] for x in macro]
    if any(b<=a for a,b in zip(times,times[1:])): raise ValueError('macro timestamp')
    if any(not isfinite(float(x['value'])) or float(x['value'])<0 for x in macro): raise ValueError('macro value')
    out={}; first=config.release_lag+config.median_lookback
    for eligible_i in range(first,len(macro)):
        li=eligible_i-config.release_lag; latest=float(macro[li]['value']); hist=[float(x['value']) for x in macro[li-config.median_lookback:li]]; recent=[float(x['value']) for x in macro[li-config.trend_window+1:li+1]]; previous=[float(x['value']) for x in macro[li-2*config.trend_window+1:li-config.trend_window+1]]; threshold=median(hist); rm=sum(recent)/len(recent); pm=sum(previous)/len(previous)
        if latest<=threshold and rm<pm:
            out[macro[eligible_i]['timestamp']]={'metric_timestamp':macro[li]['timestamp'],'window_start_timestamp':macro[li-config.median_lookback]['timestamp'],'prior_median':threshold,'latest_epu':latest,'recent5_mean':rm,'previous5_mean':pm,'earlier_timestamp':macro[li-config.trend_window]['timestamp'],'earlier_credit':pm,'latest_credit':latest,'credit_growth':(pm-rm)/(pm or 1)}
    return out
def execution_config(multiplier=1):
    b=ExecutionConfig(max_hold=5); return replace(b,fee=b.fee*multiplier,slippage=b.slippage*multiplier)
def backtest(rows,start,end,config,initial=10000.):
    normalized=[]
    for original in rows:
        row=dict(original)
        if row.get('macro_signal'):
            row.setdefault('earlier_timestamp',row['metric_timestamp']); row.setdefault('earlier_credit',row['previous5_mean']); row.setdefault('latest_credit',row['latest_epu']); row.setdefault('credit_growth',(row['previous5_mean']-row['recent5_mean'])/(row['previous5_mean'] or 1))
        normalized.append(row)
    trades,curve=_base_backtest(normalized,start,end,config,initial); signals={x['timestamp']:x for x in normalized if x.get('macro_signal')}
    for trade in trades:
        source=signals[trade['signal_timestamp']]
        for key in ('window_start_timestamp','prior_median','latest_epu','recent5_mean','previous5_mean'): trade[key]=source[key]
    return trades,curve
