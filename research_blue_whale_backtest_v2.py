#!/usr/bin/env python3
"""
Blue Whale public-style approximation v2.

This version follows the public posts more literally than v1:
- key levels come from CLOSED 4H swing highs/lows;
- a 1H candle must sweep a key level and close back through it;
- the next 1-3 bars must confirm reversal by breaking the sweep candle;
- 4H market structure must agree with the trade;
- 1D structure is used only as a "do not fight a strong regime" filter;
- fees + slippage are included;
- 60/20/20 train/validation/test split, with the final 20% untouched.

This is NOT a reconstruction of VIP entries.
"""
from __future__ import annotations
import json, math, time, urllib.parse, urllib.request
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
MAX_HOLD=36
MIN_STOP=0.0025
MAX_STOP=0.05

@dataclass
class Bar:
    t:int; o:float; h:float; l:float; c:float; v:float

def ms(x): return int(x.timestamp()*1000)

def fetch(interval,start,end):
    out=[]; cur=start
    while cur<end:
        q=urllib.parse.urlencode({"symbol":SYMBOL,"interval":interval,"startTime":cur,"endTime":end,"limit":1000})
        req=urllib.request.Request(API+"?"+q,headers={"User-Agent":"blue-whale-backtest-v2/1.0"})
        with urllib.request.urlopen(req,timeout=30) as r:
            rows=json.loads(r.read().decode())
        if not rows: break
        out += [Bar(int(x[0]),float(x[1]),float(x[2]),float(x[3]),float(x[4]),float(x[5])) for x in rows]
        nxt=int(rows[-1][0])+1
        if nxt<=cur: break
        cur=nxt; time.sleep(0.04)
    d={x.t:x for x in out}
    return [d[k] for k in sorted(d)]

def ema(v,p):
    if not v:return []
    a=2/(p+1); out=[v[0]]
    for x in v[1:]: out.append(a*x+(1-a)*out[-1])
    return out

def closed_idx(bars,t,interval_ms):
    bucket=t-(t%interval_ms)
    target=bucket-interval_ms
    lo,hi=0,len(bars)-1; ans=-1
    while lo<=hi:
        mid=(lo+hi)//2
        if bars[mid].t<=target: ans=mid; lo=mid+1
        else: hi=mid-1
    return ans

def context(h4,d1,t,level_lb):
    i4=closed_idx(h4,t,4*3600_000)
    i1=closed_idx(d1,t,24*3600_000)
    if i4<max(level_lb,55) or i1<30: return None
    prev4=h4[i4-level_lb+1:i4+1]
    key_hi=max(x.h for x in prev4)
    key_lo=min(x.l for x in prev4)

    c4=[x.c for x in h4[:i4+1]]
    e20=ema(c4[-80:],20)[-1]; e50=ema(c4[-80:],50)[-1]
    spread=(e20-e50)/h4[i4].c
    structure4=1 if spread>0.001 else -1 if spread<-0.001 else 0

    c1=[x.c for x in d1[:i1+1]]
    de10=ema(c1[-50:],10)[-1]; de20=ema(c1[-50:],20)[-1]
    dspread=(de10-de20)/d1[i1].c
    regime1=1 if dspread>0.015 else -1 if dspread<-0.015 else 0
    return key_hi,key_lo,structure4,regime1

def signals(h1,h4,d1,level_lb,confirm):
    out=[]; i=2
    while i<len(h1)-confirm-1:
        b=h1[i]; ctx=context(h4,d1,b.t,level_lb)
        if not ctx: i+=1; continue
        hi,lo,s4,r1=ctx
        side=None
        # Reversal at a key 4H level, with 4H structure agreement.
        # Strong opposite 1D regime blocks the trade, but neutral 1D is allowed.
        if b.h>hi and b.c<hi and s4==-1 and r1!=1:
            side="SHORT"
        elif b.l<lo and b.c>lo and s4==1 and r1!=-1:
            side="LONG"
        if side:
            rng=max(b.h-b.l,1e-12)
            reject=((b.h-b.c)/rng>=0.5) if side=="SHORT" else ((b.c-b.l)/rng>=0.5)
            if reject:
                ci=None
                for j in range(i+1,min(i+1+confirm,len(h1))):
                    x=h1[j]
                    if side=="SHORT" and x.l<b.l and x.c<x.o: ci=j; break
                    if side=="LONG" and x.h>b.h and x.c>x.o: ci=j; break
                if ci is not None:
                    out.append((ci,side,i))
                    i=ci
        i+=1
    return out

def bt(h1,h4,d1,start_i,end_i,level_lb,confirm,rr):
    sig=signals(h1,h4,d1,level_lb,confirm)
    sig=[s for s in sig if start_i<=s[0]<end_i]
    eq=START_EQUITY; peak=eq; dd=0; gp=0; gl=0; nfree=start_i; trades=[]
    for ei,side,si in sig:
        if ei<nfree or ei>=end_i-1: continue
        e=h1[ei]; sweep=h1[si]
        entry_m=e.c
        entry=entry_m*(1+SLIPPAGE if side=="LONG" else 1-SLIPPAGE)
        stop=sweep.l*(1-STOP_BUFFER) if side=="LONG" else sweep.h*(1+STOP_BUFFER)
        sr=((entry-stop)/entry) if side=="LONG" else ((stop-entry)/entry)
        if not(MIN_STOP<=sr<=MAX_STOP): continue
        eff=sr+ROUND_TRIP_COST
        risk=eq*RISK_FRACTION
        notional=risk/eff; qty=notional/entry
        td=rr*eff
        target=entry*(1+td) if side=="LONG" else entry*(1-td)
        xi=min(ei+MAX_HOLD,end_i-1); xm=h1[xi].c; reason="TIME"
        for k in range(ei+1,xi+1):
            x=h1[k]
            sl=(x.l<=stop) if side=="LONG" else (x.h>=stop)
            tp=(x.h>=target) if side=="LONG" else (x.l<=target)
            if sl: xi=k; xm=stop; reason="SL"; break
            if tp: xi=k; xm=target; reason="TP"; break
        xp=xm*(1-SLIPPAGE if side=="LONG" else 1+SLIPPAGE)
        gross=(xp-entry)*qty if side=="LONG" else (entry-xp)*qty
        fees=(entry+xp)*qty*FEE
        pnl=gross-fees
        eq+=pnl; peak=max(peak,eq); dd=max(dd,(peak-eq)/peak)
        if pnl>=0: gp+=pnl
        else: gl+=-pnl
        trades.append((pnl,reason,side)); nfree=xi+1
    w=sum(1 for p,_,__ in trades if p>0)
    pf=gp/gl if gl>0 else (999 if gp>0 else 0)
    return {"trades":len(trades),"wins":w,"losses":len(trades)-w,"winrate":w/len(trades) if trades else 0,
            "net_pnl":eq-START_EQUITY,"return_pct":(eq/START_EQUITY-1)*100,
            "profit_factor":pf,"max_drawdown_pct":dd*100,"ending_equity":eq}

def main():
    now=datetime.now(timezone.utc); start=now-timedelta(days=720)
    print("Fetching data",flush=True)
    h1=fetch("1h",ms(start),ms(now))
    h4=fetch("4h",ms(start-timedelta(days=30)),ms(now))
    d1=fetch("1d",ms(start-timedelta(days=120)),ms(now))
    if len(h1)<10000: raise RuntimeError("insufficient 1h data")
    a=int(len(h1)*0.60); b=int(len(h1)*0.80)

    grid=[]
    for lb in (12,20,30,42):
      for cf in (1,2,3):
       for rr in (1.2,1.5,2.0):
        tr=bt(h1,h4,d1,200,a,lb,cf,rr)
        if tr["trades"]>=25:
            score=tr["profit_factor"]-0.015*tr["max_drawdown_pct"]
            grid.append((score,lb,cf,rr,tr))
    if not grid: raise RuntimeError("no train candidates")
    grid.sort(reverse=True,key=lambda x:x[0])

    # Parameter selection requires positive validation; final test remains untouched.
    selected=None
    for score,lb,cf,rr,tr in grid:
        va=bt(h1,h4,d1,a,b,lb,cf,rr)
        if va["trades"]>=10 and va["net_pnl"]>0 and va["profit_factor"]>=1.05:
            selected=(lb,cf,rr,tr,va); break
    if selected is None:
        # Still report the best training candidate and its validation/test, but mark fail.
        _,lb,cf,rr,tr=grid[0]
        va=bt(h1,h4,d1,a,b,lb,cf,rr)
    else:
        lb,cf,rr,tr,va=selected

    te=bt(h1,h4,d1,b,len(h1),lb,cf,rr)
    passed=(selected is not None and te["trades"]>=10 and te["net_pnl"]>0 and
            te["profit_factor"]>=1.10 and te["max_drawdown_pct"]<=10)
    res={"strategy":"public_blue_whale_approx_v2","symbol":SYMBOL,
         "bars":{"1h":len(h1),"4h":len(h4),"1d":len(d1)},
         "split":"60/20/20","selected":{"level_lookback_4h":lb,"confirm_bars":cf,"rr":rr},
         "train":tr,"validation":va,"test":te,"passed":passed,
         "note":"Approximation of public Blue Whale concepts only; not VIP entries."}
    print("RESULT_JSON="+json.dumps(res,sort_keys=True),flush=True)

if __name__=="__main__": main()
