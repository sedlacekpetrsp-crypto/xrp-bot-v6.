"""Liquidity Hunter — PAPER/BACKTEST strategy only.

No order-routing code lives in this module. It generates signals and risk levels
from closed candles so it can be backtested without look-ahead bias.
"""
from dataclasses import dataclass
from typing import Optional, Sequence

PAPER_ONLY = True

@dataclass
class Signal:
    side: str
    entry: float
    stop: float
    target: float
    score: int
    sweep_level: float
    atr: float
    reason: str

def ema(values: Sequence[float], period: int) -> Optional[float]:
    if len(values) < period:
        return None
    a = 2.0 / (period + 1.0)
    out = sum(values[:period]) / period
    for x in values[period:]:
        out = a * x + (1-a) * out
    return out

def atr(high, low, close, period=14) -> Optional[float]:
    if len(close) < period + 1:
        return None
    tr=[]
    for i in range(1,len(close)):
        tr.append(max(high[i]-low[i], abs(high[i]-close[i-1]), abs(low[i]-close[i-1])))
    return sum(tr[-period:])/period

def _trend(closes: Sequence[float]):
    e20=ema(closes,20); e50=ema(closes,50)
    if e20 is None or e50 is None:
        return "NEUTRAL"
    if closes[-1] > e20 > e50:
        return "BULL"
    if closes[-1] < e20 < e50:
        return "BEAR"
    return "NEUTRAL"

def signal_from_closed_candles(
    high5, low5, close5, volume5,
    close15, close1h,
    lookback=20, volume_ratio_min=1.05,
    stop_atr=1.8, rr=2.0, diagnostics=None
) -> Optional[Signal]:
    """Return a signal after a confirmed liquidity sweep/reclaim.

    All arrays must contain CLOSED candles only.
    LONG: latest 5m candle trades below prior lookback low then closes back above it.
    SHORT: latest candle trades above prior lookback high then closes back below it.
    15m and 1h EMA20/50 must agree with the trade direction.
    """
    d = diagnostics if diagnostics is not None else {}
    d.update(reason_code="insufficient_candles", candles_5m=len(close5),
             candles_15m=len(close15), candles_1h=len(close1h))
    n=max(55, lookback+2)
    if min(len(close5),len(high5),len(low5),len(volume5)) < n:
        return None
    if len(close15)<50 or len(close1h)<50:
        return None

    a=atr(high5,low5,close5,14)
    if not a or a<=0:
        d["reason_code"] = "invalid_atr"
        return None

    prior_low=min(low5[-lookback-1:-1])
    prior_high=max(high5[-lookback-1:-1])
    h,l,c=high5[-1],low5[-1],close5[-1]
    prev_vol=volume5[-21:-1]
    vr=volume5[-1]/(sum(prev_vol)/len(prev_vol)) if prev_vol and sum(prev_vol)>0 else 0

    t15=_trend(close15); t1h=_trend(close1h)
    long_sweep=l < prior_low and c > prior_low
    short_sweep=h > prior_high and c < prior_high

    d.update(long_sweep=long_sweep, short_sweep=short_sweep,
             trend_15m=t15, trend_1h=t1h, volume_ratio=vr,
             volume_pass=vr>=volume_ratio_min, atr=a,
             long_trend=t15=="BULL" and t1h=="BULL",
             short_trend=t15=="BEAR" and t1h=="BEAR")
    aligned = (long_sweep and d['long_trend']) or (short_sweep and d['short_trend'])
    d['reason_code'] = ('no_sweep_reclaim' if not (long_sweep or short_sweep)
                        else 'trend_mismatch' if not aligned
                        else 'volume_below_threshold' if vr<volume_ratio_min else 'setup_ready')

    if long_sweep and t15=="BULL" and t1h=="BULL" and vr>=volume_ratio_min:
        stop=min(l, c-stop_atr*a)
        risk=c-stop
        if risk<=0: return None
        return Signal("LONG",c,stop,c+rr*risk,4,prior_low,a,
                      f"low sweep+reclaim; 15m/1h bull; volume {vr:.2f}x")
    if short_sweep and t15=="BEAR" and t1h=="BEAR" and vr>=volume_ratio_min:
        stop=max(h, c+stop_atr*a)
        risk=stop-c
        if risk<=0: return None
        return Signal("SHORT",c,stop,c-rr*risk,4,prior_high,a,
                      f"high sweep+reclaim; 15m/1h bear; volume {vr:.2f}x")
    return None

def position_size(equity: float, entry: float, stop: float, risk_pct=0.005) -> float:
    """Risk-based sizing; 0.5% default. Does not place an order."""
    distance=abs(entry-stop)
    if equity<=0 or distance<=0 or risk_pct<=0:
        return 0.0
    return equity*risk_pct/distance

