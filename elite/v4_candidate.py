"""ELITE V4 research: spot-only slow trend regime with low turnover.

Research hypothesis: reduce trading costs by using 5m bars to establish a
multi-day trend, entering only on infrequent trend re-confirmation.
This is not a profitability claim or live execution strategy.
"""
from dataclasses import dataclass
from statistics import mean
from typing import Optional,Sequence

@dataclass(frozen=True)
class Signal:
    side:str
    stop_distance:float
    target_distance:float

def slow_trend(high:Sequence[float],low:Sequence[float],close:Sequence[float],
               fast:int=48,slow:int=96,min_gap:float=.003,
               reward_risk:float=3.0)->Optional[Signal]:
    if not(len(high)==len(low)==len(close)) or len(close)<slow+2:
        return None
    if fast<12 or slow<fast*2 or any(x<=0 for x in close):
        return None
    if any(h<l for h,l in zip(high,low)):
        return None
    fast_ma=mean(close[-fast:])
    slow_ma=mean(close[-slow:])
    old_fast=mean(close[-fast-1:-1])
    old_slow=mean(close[-slow-1:-1])
    # Fresh positive separation after crossover; avoid repeated signals.
    if not (fast_ma>slow_ma*(1+min_gap) and old_fast<=old_slow*(1+min_gap)):
        return None
    recent_range=mean(h-l for h,l in zip(high[-slow:],low[-slow:]))
    if recent_range<=0:return None
    stop=max(3*recent_range,close[-1]*.005)
    return Signal("LONG",stop,stop*reward_risk)
