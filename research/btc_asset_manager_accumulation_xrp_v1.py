"""Frozen CFTC Bitcoin asset-manager accumulation signal and XRP simulator."""
from dataclasses import dataclass
import datetime as dt
import math
import statistics

DAY = 86_400_000
UTC = dt.timezone.utc

@dataclass(frozen=True)
class Config:
    lookback: int = 52
    momentum_lag: int = 4
    atr_n: int = 14
    stop_atr: float = 2.0
    reward_r: float = 2.5
    max_hold: int = 7
    risk_fraction: float = 0.005
    notional_cap: float = 0.20
    fee: float = 0.00095
    slippage: float = 0.00020

def next_monday(timestamp):
    date = dt.datetime.fromtimestamp(timestamp / 1000, UTC)
    days = (7 - date.weekday()) % 7
    return timestamp + (7 if days == 0 else days) * DAY

def validate_reports(rows):
    last = None
    for row in rows:
        ts = int(row["timestamp"])
        values = (float(row["open_interest"]), float(row["asset_manager_long"]), float(row["asset_manager_short"]))
        if last is not None and ts <= last:
            raise ValueError("CFTC report dates not strictly increasing")
        if not all(math.isfinite(x) for x in values) or values[0] <= 0 or min(values[1:]) < 0:
            raise ValueError("invalid CFTC position row")
        last = ts

def make_signals(reports, c=Config()):
    validate_reports(reports)
    shares = [(float(x["asset_manager_long"])-float(x["asset_manager_short"]))/float(x["open_interest"]) for x in reports]
    out = {}
    for i in range(c.lookback, len(reports)):
        row, current = reports[i], shares[i]
        cutoff = statistics.median(shares[i-c.lookback:i])
        if current <= cutoff or current <= shares[i-c.momentum_lag]:
            continue
        entry = next_monday(int(row["timestamp"]))
        if entry - int(row["timestamp"]) < 4*DAY:
            continue
        if entry in out:
            raise ValueError("multiple reports map to one entry")
        out[entry] = dict(report_timestamp=int(row["timestamp"]), net_share=current, median52=cutoff,
            share_four_reports_ago=shares[i-c.momentum_lag], open_interest=float(row["open_interest"]),
            asset_manager_long=float(row["asset_manager_long"]), asset_manager_short=float(row["asset_manager_short"]))
    return out

def validate_prices(rows):
    for i,row in enumerate(rows):
        if i and row["timestamp"]-rows[i-1]["timestamp"] != DAY: raise ValueError("price gap")
        if not 0 < row["low"] <= min(row["open"],row["close"]) <= max(row["open"],row["close"]) <= row["high"]: raise ValueError("OHLC")

def atr(rows, i, n):
    if i < n+1: return None
    return sum(max(rows[j]["high"]-rows[j]["low"],abs(rows[j]["high"]-rows[j-1]["close"]),abs(rows[j]["low"]-rows[j-1]["close"])) for j in range(i-n,i))/n

def backtest(rows, signals, start, end, c=Config(), initial=10_000.0):
    validate_prices(rows)
    equity, trades, curve, i = initial, [], [dict(timestamp=start,equity=initial)], 0
    while i < len(rows):
        bar, signal, av = rows[i], signals.get(rows[i]["timestamp"]), atr(rows,i,c.atr_n)
        if not signal or not(start <= bar["timestamp"] < end) or av is None: i += 1; continue
        if dt.datetime.fromtimestamp(bar["timestamp"]/1000,UTC).weekday()!=0 or bar["timestamp"]-signal["report_timestamp"]<4*DAY: raise ValueError("unsafe report-to-entry timing")
        raw_entry=bar["open"]; entry=raw_entry*(1+c.slippage); stop=entry-c.stop_atr*av
        if stop<=0: i+=1; continue
        qty=min(equity*c.risk_fraction/(entry-stop),equity*c.notional_cap/entry); target=entry+c.reward_r*(entry-stop)
        entry_fee=qty*entry*c.fee; before=equity; j=i
        while j<len(rows) and rows[j]["timestamp"]<end:
            x=rows[j]
            if j>i and x["timestamp"]-rows[j-1]["timestamp"]!=DAY: raw_exit,reason,ei,et=rows[j-1]["close"],"DATA_GAP",j-1,rows[j-1]["timestamp"]
            elif x["open"]<=stop: raw_exit,reason,ei,et=x["open"],"GAP_STOP",j,x["timestamp"]
            elif x["low"]<=stop: raw_exit,reason,ei,et=stop,"STOP",j,x["timestamp"]
            elif x["open"]>=target or x["high"]>=target: raw_exit,reason,ei,et=target,"TARGET",j,x["timestamp"]
            elif j-i+1>=c.max_hold: raw_exit,reason,ei,et=x["close"],"TIME",j,x["timestamp"]
            else:
                mark=x["low"]*(1-c.slippage); curve.append(dict(timestamp=x["timestamp"],equity=before+qty*(mark-entry)-entry_fee-qty*mark*c.fee)); j+=1; continue
            break
        else:
            ei=min(j-1,len(rows)-1)
            if ei<i: i+=1; continue
            et,raw_exit,reason=rows[ei]["timestamp"],rows[ei]["close"],"FOLD_END"
        fill=raw_exit*(1-c.slippage); exit_fee=qty*fill*c.fee; gross=qty*(raw_exit-raw_entry); fill_pnl=qty*(fill-entry); fees=entry_fee+exit_fee; pnl=fill_pnl-fees; equity+=pnl
        trades.append(dict(**signal,entry_timestamp=bar["timestamp"],exit_timestamp=et,entry_index=i,exit_index=ei,entry_equity=before,
            raw_entry=raw_entry,raw_exit=raw_exit,entry=entry,exit=fill,qty=qty,atr=av,stop=stop,target=target,leg_notional=qty*entry,
            gross=gross,slippage_cost=gross-fill_pnl,fees=fees,pnl=pnl,equity=equity,reason=reason,cost_fee=c.fee,cost_slippage=c.slippage))
        curve.append(dict(timestamp=et,equity=equity)); i=ei+1
    return trades,curve
