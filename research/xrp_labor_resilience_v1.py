"""Frozen labor-resilience signal; shared audited daily execution primitive."""
from dataclasses import dataclass
from math import isfinite
from statistics import median
from research.xrp_bank_credit_expansion_v1 import Config as ExecutionConfig, DAY, atr, backtest as _base_backtest, validate_prices

@dataclass(frozen=True)
class SignalConfig:
    median_lookback: int = 52
    trend_window: int = 4
    release_lag: int = 2

def make_signals(macro, config=SignalConfig()):
    times=[x['timestamp'] for x in macro]
    if any(b<=a for a,b in zip(times,times[1:])): raise ValueError('macro timestamp')
    if any(not isfinite(float(x['value'])) or float(x['value'])<=0 for x in macro): raise ValueError('macro value')
    out={}; first=config.release_lag+config.median_lookback
    for eligible_i in range(first,len(macro)):
        latest_i=eligible_i-config.release_lag; latest=float(macro[latest_i]['value'])
        history=[float(x['value']) for x in macro[latest_i-config.median_lookback:latest_i]]
        recent=[float(x['value']) for x in macro[latest_i-config.trend_window+1:latest_i+1]]
        previous=[float(x['value']) for x in macro[latest_i-2*config.trend_window+1:latest_i-config.trend_window+1]]
        threshold=median(history); recent_mean=sum(recent)/len(recent); previous_mean=sum(previous)/len(previous)
        if latest<=threshold and recent_mean<previous_mean:
            out[macro[eligible_i]['timestamp']]={'metric_timestamp':macro[latest_i]['timestamp'],'median_start_timestamp':macro[latest_i-config.median_lookback]['timestamp'],'prior_median':threshold,'latest_claims':latest,'recent4_mean':recent_mean,'previous4_mean':previous_mean,'earlier_timestamp':macro[latest_i-config.trend_window]['timestamp'],'earlier_credit':previous_mean,'latest_credit':latest,'credit_growth':(previous_mean-recent_mean)/previous_mean}
    return out

def execution_config(multiplier=1):
    base=ExecutionConfig(max_hold=5)
    from dataclasses import replace
    return replace(base,fee=base.fee*multiplier,slippage=base.slippage*multiplier)

def backtest(rows,start,end,config,initial=10000.):
    normalized=[]
    for original in rows:
        row=dict(original)
        if row.get('macro_signal'):
            row.setdefault('earlier_timestamp',row['metric_timestamp'])
            row.setdefault('earlier_credit',row['previous4_mean'])
            row.setdefault('latest_credit',row['latest_claims'])
            row.setdefault('credit_growth',(row['previous4_mean']-row['recent4_mean'])/row['previous4_mean'])
        normalized.append(row)
    trades,curve=_base_backtest(normalized,start,end,config,initial)
    signals={x['timestamp']:x for x in normalized if x.get('macro_signal')}
    for trade in trades:
        source=signals[trade['signal_timestamp']]
        for key in ('median_start_timestamp','prior_median','latest_claims','recent4_mean','previous4_mean'):
            trade[key]=source[key]
    return trades,curve
