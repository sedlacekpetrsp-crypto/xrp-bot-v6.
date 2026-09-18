#!/usr/bin/env python3
"""
Blue Whale public-style approximation v3.

Publicly described logic modeled here:
1) Identify an important support/resistance zone from CLOSED higher-timeframe data.
2) Do not chase price at the level.
3) Trade a confirmed reclaim/rejection after a false break (reversal), OR
4) trade a confirmed break + retest when the level genuinely fails.
5) Include fees/slippage and use a final untouched test set.

This is NOT a reconstruction of VIP signals.
"""
from __future__ import annotations
import json, time, urllib.parse, urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta

SYMBOL="BTCUSDT"
API="https://data-api.binance.vision/api/v3/klines"
START_EQUITY=10_000.0
RISK_FRACTION=0.003
FEE=0.0005
SLIPPAGE=0.0002
ROUND_TRIP_COST=2*(FEE+SLIPPAGE)
STOP_BUFFER=0.001
MIN_STOP=0.0025
MAX_STOP=0.04
MAX_HOLD=30

@dataclass
class Bar:
    t:int; o:float; h:float; l:float; c:float; v:float

def ms(x): return int(x.timestamp()*1000)

def fetch(interval,start,end):
    out=[]; cur=start
    while cur<end:
        q=urllib.parse.urlencode({"symbol":SYMBOL,"interval":interval,"startTime":cur,"endTime":end,"limit":1000})
        req=urllib.request.Request(API+"?"+q,headers={"User-Agent":"blue-whale-backtest-v3/1.0"})
        with urllib.request.urlopen(req,timeout=30) as r:
            rows=json.loads(r.read().decode())
        if not rows: break
        out += [Bar(int(x[0]),float(x[1]),float(x[2]),float(x[3]),float(x[4]),float(x[5])) for x in rows]
        nxt=int(rows[-1][0])+1
        if nxt<=cur: break
        cur=nxt; time.sleep(0.04)
    d={x.t:x for x in out}
    return [d[k] for k in sorted(d)]

def closed_index(bars,t,interval_ms):
    bucket=t-(t%interval_ms)
    target=bucket-interval_ms
    lo,hi,ans=0,len(bars)-1,-1
    while lo<=hi:
        m=(lo+hi)//2
        if bars[m].t<=target: ans=m; lo=m+1
        else: hi=m-1
    return ans

def key_levels(h4,d1,t,lb4):
    i4=closed_index(h4,t,4*3600_000)
    i1=closed_index(d1,t,24*3600_000)
    if i4<lb4+2 or i1<2: return None
    recent=h4[i4-lb4+1:i4+1]
    # Higher-timeframe rolling extremes plus prior-day high/low.
    vals=[
        ("R4", max(x.h for x in recent)),
        ("S4", min(x.l for x in recent)),
        ("PDH", d1[i1].h),
        ("PDL", d1[i1].l),
    ]
    # Deduplicate levels closer than 0.25%.
    vals=sorted(vals,key=lambda x:x[1])
    keep=[]
    for name,p in vals:
        if not keep or abs(p-keep[-1][1])/p>0.0025:
            keep.append((name,p))
    return keep

def setup_signals(h1,h4,d1,lb4,zone,confirm,retest_bars):
    out=[]; i=3
    while i<len(h1)-max(confirm,retest_bars)-2:
        b=h1[i]
        levels=key_levels(h4,d1,b.t,lb4)
        if not levels: i+=1; continue
        made=False
        for lname,level in levels:
            z=level*zone

            # FALSE BREAK / RECLAIM LONG
            if b.l < level-z and b.c > level:
                rng=max(b.h-b.l,1e-12)
                if (b.c-b.l)/rng>=0.55:
                    for j in range(i+1,min(i+1+confirm,len(h1))):
                        x=h1[j]
                        if x.c>b.h and x.c>x.o:
                            out.append((j,"LONG",i,"RECLAIM_"+lname,level))
                            i=j; made=True; break
                if made: break

            # FALSE BREAK / REJECT SHORT
            if b.h > level+z and b.c < level:
                rng=max(b.h-b.l,1e-12)
                if (b.h-b.c)/rng>=0.55:
                    for j in range(i+1,min(i+1+confirm,len(h1))):
                        x=h1[j]
                        if x.c<b.l and x.c<x.o:
                            out.append((j,"SHORT",i,"REJECT_"+lname,level))
                            i=j; made=True; break
                if made: break

            # TRUE BREAKDOWN + RETEST SHORT
            if b.c < level-z and b.o > level:
                for j in range(i+1,min(i+1+retest_bars,len(h1))):
                    x=h1[j]
                    touched=x.h>=level-z*0.5
                    rejected=x.c<level and x.c<x.o
                    if touched and rejected:
                        out.append((j,"SHORT",i,"BREAKDOWN_"+lname,level))
                        i=j; made=True; break
                if made: break

            # TRUE BREAKOUT + RETEST LONG
            if b.c > level+z and b.o < level:
                for j in range(i+1,min(i+1+retest_bars,len(h1))):
                    x=h1[j]
                    touched=x.l<=level+z*0.5
                    reclaimed=x.c>level and x.c>x.o
                    if touched and reclaimed:
                        out.append((j,"LONG",i,"BREAKOUT_"+lname,level))
                        i=j; made=True; break
                if made: break
        i+=1
    return out

def bt(h1,h4,d1,start_i,end_i,lb4,zone,confirm,retest_bars,rr):
    sig=setup_signals(h1,h4,d1,lb4,zone,confirm,retest_bars)
    sig=[s for s in sig if start_i<=s[0]<end_i]
    eq=START_EQUITY; peak=eq; dd=0; gp=0; gl=0; next_free=start_i; trades=[]
    for ei,side,si,setup,level in sig:
        if ei<next_free or ei>=end_i-1: continue
        e=h1[ei]; trigger=h1[si]
        em=e.c
        entry=em*(1+SLIPPAGE if side=="LONG" else 1-SLIPPAGE)

        if "RECLAIM" in setup or "REJECT" in setup:
            stop=trigger.l*(1-STOP_BUFFER) if side=="LONG" else trigger.h*(1+STOP_BUFFER)
        else:
            # Break/retest setups invalidate across the retest candle/level.
            stop=min(h1[ei].l,level*(1-STOP_BUFFER)) if side=="LONG" else max(h1[ei].h,level*(1+STOP_BUFFER))

        sr=(entry-stop)/entry if side=="LONG" else (stop-entry)/entry
        if not(MIN_STOP<=sr<=MAX_STOP): continue
        eff=sr+ROUND_TRIP_COST
        risk=eq*RISK_FRACTION
        notional=risk/eff
        qty=notional/entry
        td=rr*eff
        target=entry*(1+td) if side=="LONG" else entry*(1-td)

        xi=min(ei+MAX_HOLD,end_i-1); xm=h1[xi].c; reason="TIME"
        for k in range(ei+1,xi+1):
            x=h1[k]
            sl=(x.l<=stop) if side=="LONG" else (x.h>=stop)
            tp=(x.h>=target) if side=="LONG" else (x.l<=target)
            if sl:
                xi=k; xm=stop; reason="SL"; break
            if tp:
                xi=k; xm=target; reason="TP"; break
        xp=xm*(1-SLIPPAGE if side=="LONG" else 1+SLIPPAGE)
        gross=(xp-entry)*qty if side=="LONG" else (entry-xp)*qty
        fees=(entry+xp)*qty*FEE
        pnl=gross-fees
        eq+=pnl; peak=max(peak,eq); dd=max(dd,(peak-eq)/peak)
        if pnl>=0: gp+=pnl
        else: gl+=-pnl
        trades.append({"pnl":pnl,"setup":setup,"side":side})
        next_free=xi+1

    wins=sum(1 for t in trades if t["pnl"]>0)
    pf=gp/gl if gl>0 else (999 if gp>0 else 0)
    by_setup={}
    for t in trades:
        key=t["setup"].split("_",1)[0]
        s=by_setup.setdefault(key,{"trades":0,"pnl":0.0,"wins":0})
        s["trades"]+=1; s["pnl"]+=t["pnl"]; s["wins"]+=1 if t["pnl"]>0 else 0
    return {"trades":len(trades),"wins":wins,"losses":len(trades)-wins,
            "winrate":wins/len(trades) if trades else 0,
            "net_pnl":eq-START_EQUITY,"return_pct":(eq/START_EQUITY-1)*100,
            "profit_factor":pf,"max_drawdown_pct":dd*100,"ending_equity":eq,
            "by_setup":by_setup}

def main():
    now=datetime.now(timezone.utc); start=now-timedelta(days=720)
    print("Fetching BTC data",flush=True)
    h1=fetch("1h",ms(start),ms(now))
    h4=fetch("4h",ms(start-timedelta(days=30)),ms(now))
    d1=fetch("1d",ms(start-timedelta(days=30)),ms(now))
    a=int(len(h1)*0.60); b=int(len(h1)*0.80)

    # Small grid only. Final 20% is never used for selection.
    grid=[]
    for lb4 in (12,20,30):
      for zone in (0.0005,0.001):
       for cf in (1,2):
        for rt in (2,4):
         for rr in (1.2,1.5,2.0):
          tr=bt(h1,h4,d1,200,a,lb4,zone,cf,rt,rr)
          if tr["trades"]>=35:
            score=tr["profit_factor"]-0.015*tr["max_drawdown_pct"]
            grid.append((score,lb4,zone,cf,rt,rr,tr))
    if not grid: raise RuntimeError("No train candidates")
    grid.sort(reverse=True,key=lambda x:x[0])

    selected=None
    for score,lb4,zone,cf,rt,rr,tr in grid:
        va=bt(h1,h4,d1,a,b,lb4,zone,cf,rt,rr)
        if va["trades"]>=12 and va["net_pnl"]>0 and va["profit_factor"]>=1.08:
            selected=(lb4,zone,cf,rt,rr,tr,va)
            break
    if selected is None:
        _,lb4,zone,cf,rt,rr,tr=grid[0]
        va=bt(h1,h4,d1,a,b,lb4,zone,cf,rt,rr)
    else:
        lb4,zone,cf,rt,rr,tr,va=selected

    te=bt(h1,h4,d1,b,len(h1),lb4,zone,cf,rt,rr)
    passed=(selected is not None and te["trades"]>=12 and te["net_pnl"]>0 and
            te["profit_factor"]>=1.10 and te["max_drawdown_pct"]<=10)
    res={"strategy":"public_blue_whale_approx_v3","symbol":SYMBOL,
         "bars":{"1h":len(h1),"4h":len(h4),"1d":len(d1)},"split":"60/20/20",
         "selected":{"lookback_4h":lb4,"zone":zone,"confirm_bars":cf,"retest_bars":rt,"rr":rr},
         "train":tr,"validation":va,"test":te,"passed":passed,
         "note":"Public-plan approximation: important level + wait for confirmation + hold/break scenarios. Not VIP signals."}
    print("RESULT_JSON="+json.dumps(res,sort_keys=True),flush=True)

if __name__=="__main__": main()
