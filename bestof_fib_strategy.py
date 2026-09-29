"""Fibonacci 0.618-0.786 pullback setup shared by V8.1/Fly.
Pure helper: detects a completed impulse and a confirmed rejection from the retracement zone.
"""

def fib_pullback(highs, lows, closes, volumes, lookback=24, min_impulse_pct=0.006, min_volume_ratio=0.85):
    if min(len(highs), len(lows), len(closes), len(volumes)) < lookback + 3:
        return None
    h=list(map(float, highs)); l=list(map(float, lows)); c=list(map(float, closes)); v=list(map(float, volumes))
    # Exclude the confirmation candle from anchor discovery to avoid repainting the swing.
    start=max(0,len(c)-lookback-2); end=len(c)-1
    seg_h=h[start:end]; seg_l=l[start:end]
    hi=max(seg_h); lo=min(seg_l); hi_i=start+seg_h.index(hi); lo_i=start+seg_l.index(lo)
    price=c[-1]; prev=c[-2]; candle_low=l[-1]; candle_high=h[-1]
    base=sum(v[-21:-1])/max(len(v[-21:-1]),1); vr=v[-1]/base if base>0 else 0.0
    # Bull impulse low -> later high. Retracement prices are measured down from high.
    if lo_i < hi_i and (hi-lo)/max(lo,1e-12) >= min_impulse_pct:
        z_hi=hi-(hi-lo)*0.618; z_lo=hi-(hi-lo)*0.786
        touched=candle_low <= z_hi and candle_high >= z_lo
        confirmed=touched and price >= z_hi and price > prev and vr >= min_volume_ratio
        if confirmed:
            return {'signal':'LONG','setup':'FIB_0618_0786','fib_0618':z_hi,'fib_0786':z_lo,'swing_high':hi,'swing_low':lo,'volume_ratio':vr}
    # Bear impulse high -> later low. Retracement prices are measured up from low.
    if hi_i < lo_i and (hi-lo)/max(hi,1e-12) >= min_impulse_pct:
        z_lo=lo+(hi-lo)*0.618; z_hi=lo+(hi-lo)*0.786
        touched=candle_high >= z_lo and candle_low <= z_hi
        confirmed=touched and price <= z_lo and price < prev and vr >= min_volume_ratio
        if confirmed:
            return {'signal':'SHORT','setup':'FIB_0618_0786','fib_0618':z_lo,'fib_0786':z_hi,'swing_high':hi,'swing_low':lo,'volume_ratio':vr}
    return None
