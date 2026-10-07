"""
Liquidity Hunter V2 — PAPER strategy module.
Distinct edge: stop-hunt/liquidity sweep -> reclaim -> confirmation.
EMA 15m/1h is a safety filter, never an entry trigger.
No classic breakout or trend-pullback setup.
"""
from dataclasses import dataclass
from typing import Optional

RISK_PER_TRADE = 0.005
FEE_RATE = 0.0005
SLIPPAGE_RATE = 0.0002
SWEEP_LOOKBACK = 24
MIN_WICK_ATR = 0.12
MIN_VOLUME_RATIO = 1.05
MIN_TAKER_RATIO_LONG = 0.52
MAX_TAKER_RATIO_SHORT = 0.48
RR = 2.0
ATR_STOP_MULT = 1.0

@dataclass
class Signal:
    side: str
    setup: str
    liquidity_level: float
    stop: float
    target: float
    reason: str

def liquidity_hunter_v2(
    highs, lows, opens, closes, volumes, atr,
    trend15: str, trend1h: str,
    taker_buy_ratio: Optional[float] = None,
) -> Optional[Signal]:
    """Closed-candle only. Arrays must include the confirmation candle as the last item."""
    if len(closes) < SWEEP_LOOKBACK + 3 or not atr or atr <= 0:
        return None

    # i=-2 is the sweep/reclaim candle; i=-1 must confirm it.
    i = len(closes) - 2
    conf = i + 1
    prev_hi = max(highs[i-SWEEP_LOOKBACK:i])
    prev_lo = min(lows[i-SWEEP_LOOKBACK:i])
    avg_vol = sum(volumes[i-20:i]) / max(1, len(volumes[i-20:i]))
    vol_ratio = volumes[i] / avg_vol if avg_vol else 0.0
    if vol_ratio < MIN_VOLUME_RATIO:
        return None

    rng = max(highs[i] - lows[i], 1e-12)
    lower_reclaim = lows[i] < prev_lo and closes[i] > prev_lo
    upper_reclaim = highs[i] > prev_hi and closes[i] < prev_hi
    lower_wick = prev_lo - lows[i]
    upper_wick = highs[i] - prev_hi

    # LONG: sweep below liquidity, reclaim, bullish confirmation, no higher-TF bear conflict.
    if lower_reclaim and lower_wick >= atr * MIN_WICK_ATR:
        confirm = closes[conf] > opens[conf] and closes[conf] > closes[i]
        trend_ok = trend15 != "BEAR" and trend1h != "BEAR"
        taker_ok = taker_buy_ratio is None or taker_buy_ratio >= MIN_TAKER_RATIO_LONG
        if confirm and trend_ok and taker_ok:
            entry = closes[conf] * (1 + SLIPPAGE_RATE)
            dist = max(atr * ATR_STOP_MULT, entry - lows[i])
            return Signal("LONG", "LIQUIDITY_SWEEP_RECLAIM", prev_lo,
                          entry-dist, entry+dist*RR,
                          f"sweep_low+reclaim+confirm vol={vol_ratio:.2f}x")

    # SHORT: sweep above liquidity, reclaim, bearish confirmation, no higher-TF bull conflict.
    if upper_reclaim and upper_wick >= atr * MIN_WICK_ATR:
        confirm = closes[conf] < opens[conf] and closes[conf] < closes[i]
        trend_ok = trend15 != "BULL" and trend1h != "BULL"
        taker_ok = taker_buy_ratio is None or taker_buy_ratio <= MAX_TAKER_RATIO_SHORT
        if confirm and trend_ok and taker_ok:
            entry = closes[conf] * (1 - SLIPPAGE_RATE)
            dist = max(atr * ATR_STOP_MULT, highs[i] - entry)
            return Signal("SHORT", "LIQUIDITY_SWEEP_RECLAIM", prev_hi,
                          entry+dist, entry-dist*RR,
                          f"sweep_high+reclaim+confirm vol={vol_ratio:.2f}x")
    return None
