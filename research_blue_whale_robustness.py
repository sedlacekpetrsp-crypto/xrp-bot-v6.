#!/usr/bin/env python3
"""
Robustness audit for the public Blue Whale-style approximation.

Purpose: stop optimizing and test whether any individual public-style setup
(reclaim, rejection, breakout, breakdown) is stable across time.

No parameter fitting is done here. We use two fixed, reasonable parameter sets
and eight sequential ~90-day windows. A setup is considered research-worthy
only if it is profitable in >= 5/8 windows, pooled PF >= 1.10, pooled net PnL > 0,
and has >= 40 trades total, after fees + slippage.

This is not a reconstruction of VIP entries.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone, timedelta

import research_blue_whale_backtest_v3 as v3

PARAM_SETS = [
    {"name":"balanced", "lb4":20, "zone":0.0010, "confirm":2, "retest":4, "rr":1.5},
    {"name":"selective", "lb4":30, "zone":0.0005, "confirm":2, "retest":2, "rr":2.0},
]
SETUPS = ["RECLAIM", "REJECT", "BREAKOUT", "BREAKDOWN"]

def bt_filtered(h1,h4,d1,start_i,end_i,p,setup_prefix):
    sig=v3.setup_signals(h1,h4,d1,p["lb4"],p["zone"],p["confirm"],p["retest"])
    sig=[s for s in sig if start_i<=s[0]<end_i and s[3].startswith(setup_prefix+"_")]
    eq=v3.START_EQUITY
    peak=eq
    dd=0.0
    gp=0.0
    gl=0.0
    next_free=start_i
    trades=[]

    for ei,side,si,setup,level in sig:
        if ei<next_free or ei>=end_i-1:
            continue
        e=h1[ei]
        trigger=h1[si]
        em=e.c
        entry=em*(1+v3.SLIPPAGE if side=="LONG" else 1-v3.SLIPPAGE)

        if "RECLAIM" in setup or "REJECT" in setup:
            stop=trigger.l*(1-v3.STOP_BUFFER) if side=="LONG" else trigger.h*(1+v3.STOP_BUFFER)
        else:
            stop=min(h1[ei].l,level*(1-v3.STOP_BUFFER)) if side=="LONG" else max(h1[ei].h,level*(1+v3.STOP_BUFFER))

        sr=(entry-stop)/entry if side=="LONG" else (stop-entry)/entry
        if not(v3.MIN_STOP<=sr<=v3.MAX_STOP):
            continue

        eff=sr+v3.ROUND_TRIP_COST
        risk=eq*v3.RISK_FRACTION
        notional=risk/eff
        qty=notional/entry
        td=p["rr"]*eff
        target=entry*(1+td) if side=="LONG" else entry*(1-td)

        xi=min(ei+v3.MAX_HOLD,end_i-1)
        xm=h1[xi].c
        reason="TIME"
        for k in range(ei+1,xi+1):
            x=h1[k]
            sl=(x.l<=stop) if side=="LONG" else (x.h>=stop)
            tp=(x.h>=target) if side=="LONG" else (x.l<=target)
            if sl:
                xi=k; xm=stop; reason="SL"; break
            if tp:
                xi=k; xm=target; reason="TP"; break

        xp=xm*(1-v3.SLIPPAGE if side=="LONG" else 1+v3.SLIPPAGE)
        gross=(xp-entry)*qty if side=="LONG" else (entry-xp)*qty
        fees=(entry+xp)*qty*v3.FEE
        pnl=gross-fees
        eq+=pnl
        peak=max(peak,eq)
        dd=max(dd,(peak-eq)/peak)
        if pnl>=0: gp+=pnl
        else: gl+=-pnl
        trades.append({"pnl":pnl,"reason":reason})
        next_free=xi+1

    wins=sum(1 for t in trades if t["pnl"]>0)
    pf=gp/gl if gl>0 else (999.0 if gp>0 else 0.0)
    return {
        "trades":len(trades),
        "wins":wins,
        "winrate":wins/len(trades) if trades else 0.0,
        "net_pnl":eq-v3.START_EQUITY,
        "return_pct":(eq/v3.START_EQUITY-1)*100,
        "profit_factor":pf,
        "max_drawdown_pct":dd*100,
        "gross_profit":gp,
        "gross_loss":gl,
    }

def main():
    now=datetime.now(timezone.utc)
    start=now-timedelta(days=720)
    print("Fetching BTC data for robustness audit", flush=True)
    h1=v3.fetch("1h",v3.ms(start),v3.ms(now))
    h4=v3.fetch("4h",v3.ms(start-timedelta(days=30)),v3.ms(now))
    d1=v3.fetch("1d",v3.ms(start-timedelta(days=30)),v3.ms(now))

    # Eight sequential windows; keep a warm-up before window 1.
    warmup=200
    usable=len(h1)-warmup
    step=usable//8
    windows=[]
    for w in range(8):
        a=warmup+w*step
        b=warmup+(w+1)*step if w<7 else len(h1)
        windows.append((a,b))

    audits=[]
    any_pass=False
    for p in PARAM_SETS:
        for setup in SETUPS:
            pieces=[]
            pooled_gp=0.0
            pooled_gl=0.0
            total_trades=0
            total_pnl=0.0
            max_dd=0.0
            positive=0
            for idx,(a,b) in enumerate(windows,1):
                r=bt_filtered(h1,h4,d1,a,b,p,setup)
                pieces.append({"window":idx, **r})
                total_trades += r["trades"]
                total_pnl += r["net_pnl"]
                pooled_gp += r["gross_profit"]
                pooled_gl += r["gross_loss"]
                max_dd=max(max_dd,r["max_drawdown_pct"])
                positive += 1 if r["net_pnl"]>0 else 0
            pooled_pf=pooled_gp/pooled_gl if pooled_gl>0 else (999.0 if pooled_gp>0 else 0.0)
            passed=(positive>=5 and pooled_pf>=1.10 and total_pnl>0 and total_trades>=40)
            any_pass = any_pass or passed
            audits.append({
                "parameter_set":p["name"],
                "setup":setup,
                "positive_windows":positive,
                "windows_total":8,
                "total_trades":total_trades,
                "pooled_net_pnl":total_pnl,
                "pooled_profit_factor":pooled_pf,
                "worst_window_drawdown_pct":max_dd,
                "passed":passed,
                "windows":pieces,
            })

    # Sort best first for reporting only; criteria were fixed before run.
    audits.sort(key=lambda x:(x["passed"],x["pooled_profit_factor"],x["positive_windows"]),reverse=True)
    result={
        "strategy":"public_blue_whale_robustness_v4",
        "symbol":v3.SYMBOL,
        "bars":{"1h":len(h1),"4h":len(h4),"1d":len(d1)},
        "criteria":{
            "positive_windows_min":5,
            "pooled_profit_factor_min":1.10,
            "pooled_net_pnl_positive":True,
            "total_trades_min":40,
        },
        "any_setup_passed":any_pass,
        "audits":audits,
        "note":"Fixed-parameter time-slice robustness test. Not VIP signal reconstruction.",
    }
    print("RESULT_JSON="+json.dumps(result,sort_keys=True),flush=True)

if __name__=="__main__":
    main()
