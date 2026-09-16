try:
    from fib_strategy import fib_pullback
    import app_v9 as core

    _original_detect_setup = core.detect_setup

    def detect_setup_with_fib(k5, trend_1h, trend_15m):
        base = _original_detect_setup(k5, trend_1h, trend_15m)
        if base.get("signal") in ("LONG", "SHORT"):
            return base

        closed = k5[:-1]
        if len(closed) < 33:
            return base

        highs = [float(x[2]) for x in closed]
        lows = [float(x[3]) for x in closed]
        closes = [float(x[4]) for x in closed]
        volumes = [float(x[5]) for x in closed]
        fib = fib_pullback(
            highs, lows, closes, volumes,
            lookback=30, min_impulse_pct=0.0045, min_volume_ratio=0.85,
        )
        if not fib:
            return base

        side = fib["signal"]
        if trend_1h != side or trend_15m != side:
            return base

        cur = closed[-1]
        c = float(cur[4]); h = float(cur[2]); l = float(cur[3])
        rng = max(h - l, 1e-12)
        range_rate = rng / max(c, 1e-12)
        if range_rate > core.MAX_SIGNAL_RANGE_RATE:
            return base

        return {
            "signal": side,
            "setup": "FIB_0618_0786",
            "reason": "1h+15m trend, FIB 0.618-0.786 pullback, rejection, volume",
            "candle_time": int(cur[0]),
            "closed_price": c,
            "high": h,
            "low": l,
            "ema20_5m": core.ema(closes, 20),
            "ema50_5m": core.ema(closes, 50),
            "volume_ratio": float(fib["volume_ratio"]),
            "body_ratio": core.body_ratio(cur),
            "range_rate": range_rate,
            "fib_0618": float(fib["fib_0618"]),
            "fib_0786": float(fib["fib_0786"]),
            "swing_high": float(fib["swing_high"]),
            "swing_low": float(fib["swing_low"]),
        }

    core.detect_setup = detect_setup_with_fib
    print("FIB_PATCH_ACTIVE v9-best-of", flush=True)
except Exception as exc:
    print("V9 FIB PATCH ERROR", repr(exc), flush=True)
