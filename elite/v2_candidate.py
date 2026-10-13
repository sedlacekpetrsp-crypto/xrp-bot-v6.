"""ELITE V2 research candidate: volatility compression followed by expansion.

This is a testable hypothesis, NOT evidence of profitability. Signals use
only closed OHLC candles; execution belongs to a separate backtest.
"""
from dataclasses import dataclass
from statistics import median
from typing import Optional, Sequence

@dataclass(frozen=True)
class CandidateSignal:
    side: str
    reference_price: float
    stop_distance: float
    target_distance: float
    compression_ratio: float

def compression_expansion(high: Sequence[float], low: Sequence[float],
                          close: Sequence[float], window: int = 24,
                          compression_max: float = 0.72,
                          expansion_min: float = 1.4,
                          reward_risk: float = 1.8) -> Optional[CandidateSignal]:
    """Return a breakout signal after a compressed closed-bar price range."""
    if not (len(high) == len(low) == len(close)) or len(close) < 2*window+1:
        return None
    if window < 12 or any(c <= 0 for c in close):
        return None
    ranges = [h-l for h,l in zip(high,low)]
    if any(r < 0 for r in ranges):
        return None
    recent = median(ranges[-window-1:-1])
    earlier = median(ranges[-2*window-1:-window-1])
    if earlier <= 0 or recent <= 0:
        return None
    ratio = recent/earlier
    if ratio > compression_max or ranges[-1] < expansion_min*recent:
        return None
    upper = max(high[-window-1:-1])
    lower = min(low[-window-1:-1])
    if close[-1] > upper:
        side = "LONG"
    elif close[-1] < lower:
        side = "SHORT"
    else:
        return None
    stop = max(recent*2.0, close[-1]*0.001)
    return CandidateSignal(side, close[-1], stop, stop*reward_risk, ratio)
