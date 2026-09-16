"""Confirmed Fibonacci 0.618-0.786 pullback setup."""

def fib_pullback(highs, lows, closes, volumes, lookback=24, min_impulse_pct=0.006, min_volume_ratio=0.85):
    if min(len(highs), len(lows), len(closes), len(volumes)) < lookback + 3:
        return None
    h = list(map(float, highs)); l = list(map(float, lows)); c = list(map(float, closes)); v = list(map(float, volumes))
    start = max(0, len(c) - lookback - 2); end = len(c) - 1
    sh = h[start:end]; sl = l[start:end]
    hi = max(sh); lo = min(sl)
    hi_i = start + sh.index(hi); lo_i = start + sl.index(lo)
    price = c[-1]; prev = c[-2]
    base = sum(v[-21:-1]) / max(len(v[-21:-1]), 1)
    vr = v[-1] / base if base > 0 else 0.0
    if lo_i < hi_i and (hi - lo) / max(lo, 1e-12) >= min_impulse_pct:
        f618 = hi - (hi - lo) * .618
        f786 = hi - (hi - lo) * .786
        if l[-1] <= f618 and h[-1] >= f786 and price >= f618 and price > prev and vr >= min_volume_ratio:
            return {"signal":"LONG","setup":"FIB_0618_0786","fib_0618":f618,"fib_0786":f786,"swing_high":hi,"swing_low":lo,"volume_ratio":vr}
    if hi_i < lo_i and (hi - lo) / max(hi, 1e-12) >= min_impulse_pct:
        f618 = lo + (hi - lo) * .618
        f786 = lo + (hi - lo) * .786
        if h[-1] >= f618 and l[-1] <= f786 and price <= f618 and price < prev and vr >= min_volume_ratio:
            return {"signal":"SHORT","setup":"FIB_0618_0786","fib_0618":f618,"fib_0786":f786,"swing_high":hi,"swing_low":lo,"volume_ratio":vr}
    return None
