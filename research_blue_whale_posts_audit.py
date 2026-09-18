#!/usr/bin/env python3
"""
Audit ACTUAL PUBLIC Blue Whale posts, not a reconstructed strategy.

Important limitations:
- We only score a trade when a public pre-outcome post exists.
- If exact entry/TP is hidden behind VIP, we do NOT invent it.
- For incomplete public calls we calculate a "post-time proxy" using BTCUSDT 1m
  price at the public post timestamp and label it PROXY, never as the claimed entry.
- Ambiguous masked stops such as 748xx are treated as a band [74800, 74899].
- Telemetr timestamps are tested under several UTC-offset interpretations to avoid
  relying on an undocumented display timezone.

Current sequence audited:
15 Sep 2026 17:42 — public plan: hold support -> 79,800; failure -> 74k
16 Sep 2026 16:06 — public BTC position post, SL 748xx, 2% capital;
                    exact best entry/TP explicitly reserved for VIP
16 Sep 2026 20:31 — "STILL HOLDING BTC"
17 Sep 2026 04:40 — "LONG BTC ... result we wanted"

Source: public Telemetr mirror of @BlueWhaleCryptoTrading.
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

API = "https://data-api.binance.vision/api/v3/klines"
SYMBOL = "BTCUSDT"

EVENTS = {
    "plan": "2026-09-15T17:42:00",
    "signal": "2026-09-16T16:06:00",
    "hold": "2026-09-16T20:31:00",
    "result": "2026-09-17T04:40:00",
}

# We do not know whether Telemetr's displayed times are UTC or a local display zone.
# Evaluate several plausible offsets. offset means displayed_time = UTC + offset.
DISPLAY_OFFSETS = [-3, 0, 2, 3]

def dt(s: str, display_offset_hours: int) -> datetime:
    naive = datetime.fromisoformat(s)
    return (naive - timedelta(hours=display_offset_hours)).replace(tzinfo=timezone.utc)

def ms(x: datetime) -> int:
    return int(x.timestamp() * 1000)

def fetch_1m(start: datetime, end: datetime):
    out = []
    cur = ms(start)
    end_ms = ms(end)
    while cur < end_ms:
        qs = urllib.parse.urlencode({
            "symbol": SYMBOL,
            "interval": "1m",
            "startTime": cur,
            "endTime": end_ms,
            "limit": 1000,
        })
        req = urllib.request.Request(API + "?" + qs, headers={"User-Agent":"blue-whale-post-audit/1.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            rows = json.loads(r.read().decode())
        if not rows:
            break
        out.extend(rows)
        nxt = int(rows[-1][0]) + 1
        if nxt <= cur:
            break
        cur = nxt
        time.sleep(0.03)
    return out

def price_near(rows, target_ms):
    if not rows:
        return None
    row = min(rows, key=lambda x: abs(int(x[0]) - target_ms))
    return {
        "time_ms": int(row[0]),
        "open": float(row[1]),
        "high": float(row[2]),
        "low": float(row[3]),
        "close": float(row[4]),
    }

def main():
    results = []
    for off in DISPLAY_OFFSETS:
        signal_dt = dt(EVENTS["signal"], off)
        result_dt = dt(EVENTS["result"], off)
        hold_dt = dt(EVENTS["hold"], off)
        start = signal_dt - timedelta(minutes=5)
        end = result_dt + timedelta(minutes=5)
        rows = fetch_1m(start, end)
        if not rows:
            results.append({"display_offset_hours":off, "error":"no market data"})
            continue

        sig = price_near(rows, ms(signal_dt))
        hold = price_near(rows, ms(hold_dt))
        res = price_near(rows, ms(result_dt))
        between = [x for x in rows if ms(signal_dt) <= int(x[0]) <= ms(result_dt)]
        hi = max(float(x[2]) for x in between)
        lo = min(float(x[3]) for x in between)

        proxy_entry = sig["close"]
        proxy_exit = res["close"]
        proxy_return = (proxy_exit / proxy_entry - 1) * 100.0
        stop_low, stop_high = 74800.0, 74899.0

        # For a long, if low <= 74800, every possible 748xx stop was hit.
        # If low > 74899, no possible 748xx stop was hit.
        # Otherwise exact masked stop determines the outcome.
        if lo <= stop_low:
            stop_status = "ALL_748xx_STOPS_HIT"
        elif lo > stop_high:
            stop_status = "NO_748xx_STOP_HIT"
        else:
            stop_status = "MASKED_STOP_AMBIGUOUS"

        # Public plan mentioned 79,800 as upside objective. This is not necessarily
        # the VIP trade's TP, so report reachability only.
        target_79800_reached = hi >= 79800.0

        results.append({
            "display_offset_hours": off,
            "assumed_signal_utc": signal_dt.isoformat(),
            "assumed_result_utc": result_dt.isoformat(),
            "signal_market_proxy": sig,
            "hold_market_proxy": hold,
            "result_market_proxy": res,
            "between_signal_and_result": {
                "high": hi,
                "low": lo,
                "proxy_long_return_pct_before_fees": proxy_return,
                "masked_stop_748xx_status": stop_status,
                "public_plan_79800_reached": target_79800_reached,
            },
        })

    audit = {
        "audit_type":"actual_public_post_sequence",
        "channel":"@BlueWhaleCryptoTrading",
        "events_displayed":EVENTS,
        "public_facts":{
            "plan_upside_level":79800,
            "plan_downside_level":74000,
            "signal_stop_mask":"748xx",
            "signal_risk_text":"Only use 2% of your capital",
            "signal_exact_entry_public":False,
            "signal_exact_tp_public":False,
            "hold_followup":True,
            "result_followup_direction":"LONG",
        },
        "results_by_timestamp_interpretation":results,
        "scoring_rule":"Do not count as an exact trade because public entry/TP are withheld. Proxy market-return is diagnostic only.",
    }
    print("RESULT_JSON=" + json.dumps(audit, sort_keys=True), flush=True)

if __name__ == "__main__":
    main()
