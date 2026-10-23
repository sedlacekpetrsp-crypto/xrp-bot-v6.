"""Liquidity Hunter V2 — PAPER only.
Edge: stop-hunt/liquidity sweep -> reclaim -> next closed-candle confirmation.
Higher-TF EMA is a safety filter, not an entry trigger. No breakout/pullback setup.
"""
from dataclasses import dataclass
from typing import Optional, Sequence
PAPER_ONLY=True

@dataclass
class Signal:
    side:str; entry:float; stop:float; target:float; score:int
    sweep_level:float; atr:float; reason:str

def ema(v:Sequence[float],p:int)->Optional[float]:
    if len(v)<p:return None
    a=2/(p+1); out=sum(v[:p])/p
    for x in v[p:]: out=a*x+(1-a)*out
    return out

def atr(h,l,c,p=14):
    if len(c)<p+1:return None
    tr=[max(h[i]-l[i],abs(h[i]-c[i-1]),abs(l[i]-c[i-1])) for i in range(1,len(c))]
    return sum(tr[-p:])/p

def _trend(c):
    e20,e50=ema(c,20),ema(c,50)
    if e20 is None or e50 is None:return "NEUTRAL"
    if c[-1]>e20>e50:return "BULL"
    if c[-1]<e20<e50:return "BEAR"
    return "NEUTRAL"

def signal_from_closed_candles(high5,low5,open5,close5,volume5,close15,close1h,
                               taker_buy_ratio=None,lookback=24,volume_ratio_min=1.05,
                               min_wick_atr=.12,stop_atr=1.0,rr=2.0):
    # -2 = sweep/reclaim; -1 = confirmation. Closed candles only.
    if min(map(len,[high5,low5,open5,close5,volume5]))<max(56,lookback+3) or len(close15)<50 or len(close1h)<50:return None
    a=atr(high5,low5,close5,14)
    if not a or a<=0:return None
    i=len(close5)-2; j=i+1
    lo=min(low5[i-lookback:i]); hi=max(high5[i-lookback:i])
    vv=volume5[i-20:i]; vr=volume5[i]/(sum(vv)/len(vv)) if vv and sum(vv)>0 else 0
    if vr<volume_ratio_min:return None
    t15,t1h=_trend(close15),_trend(close1h)
    long_sweep=low5[i]<lo and close5[i]>lo and lo-low5[i]>=min_wick_atr*a
    short_sweep=high5[i]>hi and close5[i]<hi and high5[i]-hi>=min_wick_atr*a
    if long_sweep and close5[j]>open5[j] and close5[j]>close5[i] and t15!="BEAR" and t1h!="BEAR" and (taker_buy_ratio is None or taker_buy_ratio>=.52):
        entry=close5[j]; stop=min(low5[i],entry-stop_atr*a); risk=entry-stop
        if risk>0:return Signal("LONG",entry,stop,entry+rr*risk,6,lo,a,f"V2 low sweep+reclaim+confirm; trend {t15}/{t1h}; vol {vr:.2f}x; taker {taker_buy_ratio}")
    if short_sweep and close5[j]<open5[j] and close5[j]<close5[i] and t15!="BULL" and t1h!="BULL" and (taker_buy_ratio is None or taker_buy_ratio<=.48):
        entry=close5[j]; stop=max(high5[i],entry+stop_atr*a); risk=stop-entry
        if risk>0:return Signal("SHORT",entry,stop,entry-rr*risk,6,hi,a,f"V2 high sweep+reclaim+confirm; trend {t15}/{t1h}; vol {vr:.2f}x; taker {taker_buy_ratio}")
    return None

def position_size(equity,entry,stop,risk_pct=.005):
    d=abs(entry-stop)
    return equity*risk_pct/d if equity>0 and d>0 and risk_pct>0 else 0.0
