"""Research-only selective signal combiner. No exchange orders or production integration.

This deliberately does NOT cherry-pick winning historical trades. All decisions
use completed daily candles and the pre-registered volatility momentum signal.
Other failed research strategies are excluded until independently validated.
"""
from dataclasses import dataclass
from math import log, sqrt
from research.volatility_managed_momentum_v1 import Config, SYMBOLS, allocation


@dataclass(frozen=True)
class SelectionConfig:
    max_positions: int = 2
    gross_cap: float = 0.20
    per_asset_cap: float = 0.10
    minimum_30d_momentum: float = 0.03
    maximum_daily_volatility: float = 0.08


def select_candidates(daily, completed_day_index, strategy=Config(),
                      selection=SelectionConfig()):
    """Return ranked paper-only target weights from information available at i.

    Caller must execute no earlier than the next daily open, and only after
    confirming that all input days through i have closed.
    """
    i = completed_day_index
    if i < max(strategy.momentum_days, strategy.volatility_days, 30):
        return []
    base = allocation(daily, i, strategy)
    ranked = []
    for symbol in SYMBOLS:
        if symbol not in base:
            continue
        bars = daily[symbol]
        if len(bars) <= i or any(bars[j]["close"] <= 0 for j in range(i-30, i+1)):
            continue
        momentum_30d = bars[i]["close"] / bars[i-30]["close"] - 1
        returns = [log(bars[j]["close"] / bars[j-1]["close"])
                   for j in range(i-29, i+1)]
        mean = sum(returns)/len(returns)
        vol = sqrt(sum((r-mean)**2 for r in returns)/len(returns))
        if momentum_30d < selection.minimum_30d_momentum or vol > selection.maximum_daily_volatility:
            continue
        ranked.append((symbol, momentum_30d, vol, base[symbol]))
    ranked.sort(key=lambda row: (-row[1], row[2], row[0]))
    remaining = selection.gross_cap
    result = []
    for symbol, momentum, vol, weight in ranked[:selection.max_positions]:
        target = min(weight, selection.per_asset_cap, remaining)
        if target > 0:
            result.append({"symbol": symbol, "weight": target,
                           "momentum_30d": momentum, "daily_volatility": vol,
                           "mode": "PAPER_RESEARCH_ONLY"})
            remaining -= target
    return result
