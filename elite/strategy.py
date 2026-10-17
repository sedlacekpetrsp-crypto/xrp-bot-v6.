"""ELITE V1 experimental regime-conditioned return-reversion signal.

Research only: no exchange integration, orders, or performance claims.
All inputs are *closed* OHLCV bars, oldest to newest.
"""
from dataclasses import dataclass
from math import log, sqrt
from statistics import mean, pstdev
from typing import Optional, Sequence

@dataclass(frozen=True)
class EliteSignal:
    side: str
    observed_close: float
    zscore: float
    trend_efficiency: float
    volatility_ratio: float
    stop_distance: float
    target_distance: float

def signal_from_closed_bars(
    high: Sequence[float], low: Sequence[float], close: Sequence[float],
    window: int = 48, z_threshold: float = 2.25,
    max_efficiency: float = 0.32, max_volatility_ratio: float = 1.65,
    stop_vol_mult: float = 2.0, reward_risk: float = 1.5,
) -> Optional[EliteSignal]:
    """Signal at bar close; execution must occur at next bar or later.

    Prior-window estimates exclude the current bar to avoid self-normalization.
    Uses price-return trend efficiency to avoid trend-dominated regimes.
    """
    if not (len(high) == len(low) == len(close)) or len(close) < 2*window+2:
        return None
    if window < 20 or any(x <= 0 for x in close):
        return None
    returns = [log(close[i]/close[i-1]) for i in range(1, len(close))]
    current = returns[-1]
    baseline = returns[-window-1:-1]
    prior = returns[-2*window-1:-window-1]
    if len(baseline) != window or len(prior) != window:
        return None
    sd = pstdev(baseline)
    prev_sd = pstdev(prior)
    if sd <= 1e-12 or prev_sd <= 1e-12:
        return None
    z = (current-mean(baseline))/sd
    vol_ratio = sd/prev_sd
    efficiency = abs(sum(baseline))/max(sum(abs(r) for r in baseline), 1e-12)
    if abs(z) < z_threshold or efficiency > max_efficiency or vol_ratio > max_volatility_ratio:
        return None
    # Close-to-close volatility distance is deliberately not called ATR.
    distance = close[-1]*sd*sqrt(5)*stop_vol_mult
    if distance <= 0:
        return None
    return EliteSignal(
        side="SHORT" if z > 0 else "LONG",
        observed_close=close[-1], zscore=z,
        trend_efficiency=efficiency, volatility_ratio=vol_ratio,
        stop_distance=distance, target_distance=distance*reward_risk,
    )
