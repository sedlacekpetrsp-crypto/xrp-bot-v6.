"""ELITE V3 research: long-only multi-horizon momentum with volatility targeting.

Distinct from V1 return reversal and V2 compression breakout.
Uses only closed OHLC candles, no orders or execution integration.
"""
from dataclasses import dataclass
from statistics import pstdev
from math import log
from typing import Optional, Sequence

@dataclass(frozen=True)
class V3Signal:
    side: str
    stop_distance: float
    target_distance: float

def multi_horizon_momentum(high: Sequence[float], low: Sequence[float],
                           close: Sequence[float], short_window: int=24,
                           long_window: int=96, min_return: float=0.012,
                           max_volatility: float=0.009,
                           reward_risk: float=2.5) -> Optional[V3Signal]:
    """Trend persistence without channel-breakout requirement; long-only spot."""
    if len(close)<long_window+2 or not(len(high)==len(low)==len(close)):
        return None
    if any(c<=0 for c in close) or short_window<8 or long_window<short_window*2:
        return None
    if any(h<l for h,l in zip(high,low)):
        return None
    returns=[log(close[i]/close[i-1]) for i in range(len(close)-long_window,len(close))]
    vol=pstdev(returns)
    if not (0<vol<=max_volatility):
        return None
    short_return=close[-1]/close[-short_window-1]-1
    long_return=close[-1]/close[-long_window-1]-1
    if short_return<=min_return/3 or long_return<=min_return:
        return None
    # Momentum persistence: most recent quarter must contribute positively.
    if close[-1] <= sum(close[-short_window:])/short_window:
        return None
    stop=max(close[-1]*vol*3,close[-1]*0.004)
    return V3Signal("LONG",stop,stop*reward_risk)
