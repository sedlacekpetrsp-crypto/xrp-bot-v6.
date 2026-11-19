"""K11 data-only independent proof gate; a mid-day last candle is not delisting evidence."""
from datetime import datetime

def validated_end_minute(symbol, last_minute, events, asof):
    """Accept only a PIT-observed, source-hashed termination event for this contract."""
    if not isinstance(last_minute, int) or isinstance(last_minute, bool):
        return None
    if asof.tzinfo is None or asof.utcoffset() is None:
        raise ValueError("asof must be timezone aware")
    for e in events:
        if e.get("symbol") != symbol or e.get("status") != "TRADING_TERMINATED":
            continue
        t, seen, digest = e.get("event_time"), e.get("observed_at"), e.get("source_sha256")
        if not isinstance(t, datetime) or not isinstance(seen, datetime):
            continue
        if any(x.tzinfo is None or x.utcoffset() is None for x in (t, seen)):
            continue
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            continue
        if seen > asof or seen < t:
            continue
        end_minute = int(t.timestamp()) // 60
        if end_minute == last_minute + 1 and t.timestamp() % 60 == 0:
            return end_minute
    return None

def coverage_with_proven_end(minutes, lo, hi, symbol, events, asof):
    """Without independently verified termination use full frozen window."""
    if not isinstance(lo, int) or not isinstance(hi, int) or lo >= hi:
        raise ValueError("invalid frozen window")
    last = max(minutes) if minutes else None
    end = validated_end_minute(symbol, last, events, asof) if last is not None else None
    stop = end if end is not None and lo < end < hi else hi
    return {"coverage": sum(lo <= m < stop for m in minutes) / (stop - lo),
            "truncated": stop != hi, "denominator_minutes": stop - lo,
            "termination_evidenced": stop != hi}
