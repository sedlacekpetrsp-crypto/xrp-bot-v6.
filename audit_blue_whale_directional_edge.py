#!/usr/bin/env python3
"""
Measure directional edge of DISTINCT public Blue Whale BTC calls at fixed horizons.

This is deliberately NOT a profit backtest of VIP trades.
Entry proxy = Binance BTCUSDT 1m close at the timestamp of the FIRST public post.
Direction is inferred only when the public SL band is clearly on the correct side
of the public-post price. Calls with ambiguous direction are excluded.

For each usable call we measure directional return at 1h/4h/12h/24h/48h,
whether the public masked SL was definitely hit before that horizon, and a
simple sign hit-rate. Only horizons that have actually elapsed are included.
"""
from __future__ import annotations
import json, math
from datetime import datetime, timezone, timedelta

import audit_blue_whale_signal_sequences as seq

HOURS = [1, 4, 12, 24, 48]

def binom_tail_at_least(k, n, p=0.5):
    if n <= 0: return None
    return sum(math.comb(n, i)*(p**i)*((1-p)**(n-i)) for i in range(k, n+1))

def main():
    posts = seq.collect()
    sigs = []
    for p in posts:
        if not p["dt"] or not seq.is_btc(p["text"]):
            continue
        st = seq.parse_stop(p["text"])
        if st:
            sigs.append({**p, "stop": st})

    # Same dedupe rule as sequence audit: repeated same SL within 72h = same cluster.
    clusters = []
    for s in sigs:
        t = seq.dtparse(s["dt"])
        matched = None
        for c in reversed(clusters):
            if c["stop"]["low"] == s["stop"]["low"] and c["stop"]["high"] == s["stop"]["high"]:
                if t - seq.dtparse(c["first"]["dt"]) <= timedelta(hours=72):
                    matched = c
                    break
        if matched:
            matched["reposts"].append(s)
        else:
            clusters.append({"first": s, "stop": s["stop"], "reposts": []})

    now = datetime.now(timezone.utc)
    calls = []

    for c in clusters:
        start = seq.dtparse(c["first"]["dt"])
        if start >= now:
            continue

        max_h = max(h for h in HOURS if start + timedelta(hours=h) <= now) if any(start + timedelta(hours=h) <= now for h in HOURS) else None
        if max_h is None:
            continue

        rows = seq.fetch_1m(start - timedelta(minutes=1), start + timedelta(hours=max_h, minutes=2))
        if not rows:
            continue

        first = min(rows, key=lambda x: abs(int(x[0]) - seq.ms(start)))
        entry = float(first[4])
        sl = c["stop"]

        if sl["high"] < entry * 0.995:
            side = "LONG"
        elif sl["low"] > entry * 1.005:
            side = "SHORT"
        else:
            side = "UNKNOWN"

        if side == "UNKNOWN":
            calls.append({
                "signal_id": c["first"]["id"],
                "signal_dt": c["first"]["dt"],
                "proxy_entry": entry,
                "stop": sl,
                "side": side,
                "excluded_reason": "SL band too close to / inconsistent with proxy price",
            })
            continue

        metrics = {}
        for h in HOURS:
            end = start + timedelta(hours=h)
            if end > now:
                continue
            end_ms = seq.ms(end)
            subset = [x for x in rows if seq.ms(start) <= int(x[0]) <= end_ms]
            if not subset:
                continue
            last = min(subset, key=lambda x: abs(int(x[0]) - end_ms))
            close = float(last[4])
            high = max(float(x[2]) for x in subset)
            low = min(float(x[3]) for x in subset)

            if side == "LONG":
                dret = (close / entry - 1.0) * 100.0
                mfe = (high / entry - 1.0) * 100.0
                mae = (low / entry - 1.0) * 100.0
                if low <= sl["low"]:
                    stop = "DEFINITELY_HIT"
                elif low > sl["high"]:
                    stop = "DEFINITELY_NOT_HIT"
                else:
                    stop = "AMBIGUOUS_MASK"
            else:
                dret = (entry / close - 1.0) * 100.0
                mfe = (entry / low - 1.0) * 100.0
                mae = (entry / high - 1.0) * 100.0
                if high >= sl["high"]:
                    stop = "DEFINITELY_HIT"
                elif high < sl["low"]:
                    stop = "DEFINITELY_NOT_HIT"
                else:
                    stop = "AMBIGUOUS_MASK"

            metrics[str(h)] = {
                "directional_return_pct": dret,
                "mfe_pct": mfe,
                "mae_pct": mae,
                "stop_status": stop,
                "positive": dret > 0,
            }

        calls.append({
            "signal_id": c["first"]["id"],
            "signal_dt": c["first"]["dt"],
            "signal_text": c["first"]["text"],
            "repost_count": len(c["reposts"]),
            "proxy_entry": entry,
            "stop": sl,
            "side": side,
            "metrics": metrics,
        })

    usable = [c for c in calls if c.get("side") in ("LONG","SHORT")]
    aggregate = {}
    for h in HOURS:
        vals = []
        for c in usable:
            m = c.get("metrics", {}).get(str(h))
            if m:
                vals.append(m)
        if not vals:
            continue
        wins = sum(1 for x in vals if x["positive"])
        definitely_stopped = sum(1 for x in vals if x["stop_status"] == "DEFINITELY_HIT")
        ambiguous_stop = sum(1 for x in vals if x["stop_status"] == "AMBIGUOUS_MASK")
        rets = sorted(x["directional_return_pct"] for x in vals)
        med = rets[len(rets)//2] if len(rets)%2 else (rets[len(rets)//2-1]+rets[len(rets)//2])/2
        aggregate[str(h)] = {
            "calls": len(vals),
            "positive_calls": wins,
            "hit_rate_pct": 100.0*wins/len(vals),
            "avg_directional_return_pct": sum(rets)/len(rets),
            "median_directional_return_pct": med,
            "definitely_stopped": definitely_stopped,
            "ambiguous_stop": ambiguous_stop,
            "binomial_one_sided_p_vs_50pct": binom_tail_at_least(wins, len(vals), 0.5),
        }

    result = {
        "method": "fixed_horizon_public_post_directional_audit",
        "distinct_clusters": len(clusters),
        "usable_direction_calls": len(usable),
        "excluded_ambiguous_direction": sum(1 for c in calls if c.get("side") == "UNKNOWN"),
        "horizons_hours": HOURS,
        "aggregate": aggregate,
        "calls": calls,
        "warning": "Not VIP trade PnL. Proxy entry is public-post-time BTC price; exact entry/TP/exit are unknown.",
    }
    print("RESULT_JSON="+json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)

if __name__ == "__main__":
    main()
