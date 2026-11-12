"""Upper-bound sensitivity of the OOS outcome census (RADAR-G1-LOWN, dialog 0318/0319).

DESCRIPTIVE ONLY: no model, no predictions, no P/L. Purpose: decide whether an exact
protocol (00:05 first spot trade) reconciliation could materially change LOW_N status.

Bound construction (Binance XRPUSDT 1h spot klines):
- reference price = OPEN of the 00:00 UTC candle (first trade of the day, closer to the
  protocol 00:05 first trade than the 01:00 close proxy used in 08ae57e);
- barrier touches use intra-hour HIGH / LOW of every candle in the horizon (hour 0 included).
Every traded price lies within [LOW, HIGH], so trade-level barrier hits are a subset of
these touches -> episode counts here are an UPPER BOUND for barrier hits measured from
this reference. If grouped counts stay < 20, exact-protocol labels cannot lift the
conservative census over the gate (up to the 00:00->00:05 reference shift).
"""
from __future__ import annotations
import csv, hashlib, io, json, os, re, zipfile
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from research.top_risk_radar_v1.exploratory_kline_census import BASE, get
from research.top_risk_radar_v1.multiyear_census import month_range
from research.top_risk_radar_v1.episodes import group_positive_episodes
from research.top_risk_radar_v1.anchored_episodes import anchored_episodes

H = timedelta(hours=1)


def load_month_ohlc(month):
    name = f"XRPUSDT-1h-{month}.zip"
    blob = get(BASE + name)
    chk = get(BASE + name + ".CHECKSUM").decode()
    m = re.search(r"\b([a-fA-F0-9]{64})\b", chk)
    if not m or hashlib.sha256(blob).hexdigest() != m.group(1).lower():
        raise ValueError(f"checksum mismatch: {month}")
    out = []
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        files = [f for f in z.infolist() if not f.is_dir()]
        if len(files) != 1 or not files[0].filename.endswith(".csv"):
            raise ValueError("unexpected ZIP")
        with z.open(files[0]) as f:
            for row in csv.reader(io.TextIOWrapper(f, encoding="utf-8-sig")):
                if row and row[0].lower().startswith("open"):
                    continue
                if len(row) != 12:
                    raise ValueError("bad candle")
                stamp = int(row[0])
                if 10**12 <= stamp < 10**14: divisor = 1000
                elif 10**15 <= stamp < 10**17: divisor = 1000000
                else: raise ValueError("unexpected timestamp")
                dt = datetime.fromtimestamp(stamp / divisor, tz=timezone.utc)
                o, hi, lo = Decimal(row[1]), Decimal(row[2]), Decimal(row[3])
                if min(o, hi, lo) <= 0 or lo > hi or not (lo <= o <= hi):
                    raise ValueError("invalid candle")
                out.append((dt, (o, hi, lo)))
    return out, {"month": month, "sha256": hashlib.sha256(blob).hexdigest(), "candles": len(out)}


def evaluate(rows):
    by_time = dict(rows)
    if len(by_time) != len(rows):
        raise ValueError("duplicate timestamps")
    times = sorted(by_time)
    missing = set()
    for a, b in zip(times, times[1:]):
        while b - a > H:
            a += H
            missing.add(a)
    if len(missing) > 1000:
        raise ValueError("too many missing hours; refuse census")
    growth, risk = [], []
    matured = excluded = 0
    for t in times:
        if t.hour != 0 or t + timedelta(days=30) > times[-1]:
            continue
        if any(t + h * H in missing for h in range(0, 720)):
            excluded += 1
            continue
        ref = by_time[t][0]
        matured += 1
        if any(by_time[t + h * H][1] >= ref * Decimal("1.30") for h in range(0, 720)):
            growth.append(t)
        if any(by_time[t + h * H][2] <= ref * Decimal("0.80") for h in range(0, 336)):
            risk.append(t)

    def grouped(d, days):
        return len(group_positive_episodes(d, [True] * len(d), max_separation=timedelta(days=days)))

    return {"matured_decisions": matured, "excluded_missing_data": excluded,
            "growth_positive_decisions": len(growth), "risk_positive_decisions": len(risk),
            "anchored_growth_episodes_30d": len(anchored_episodes(growth, horizon_days=30)),
            "grouped_growth_episodes_30d": grouped(growth, 30),
            "anchored_risk_episodes_14d": len(anchored_episodes(risk, horizon_days=14)),
            "grouped_risk_episodes_14d": grouped(risk, 14),
            "last_matured_decision": max((t for t in times if t.hour == 0 and t + timedelta(days=30) <= times[-1]), default=None).isoformat() if times else None}


if __name__ == "__main__":
    months = month_range(os.environ.get("CENSUS_START", "2022-01"), os.environ.get("CENSUS_END", "2026-10"))
    rows, manifests = [], []
    for month in months:
        part, meta = load_month_ohlc(month)
        rows.extend(part); manifests.append(meta)
    report = {"status": "DESCRIPTIVE_UPPER_BOUND_NOT_PREDICTION",
              "reference": "00:00 UTC candle OPEN; touches via intra-hour HIGH/LOW (upper bound)",
              "months": f"{months[0]}..{months[-1]}", "sources": manifests, "analysis": evaluate(rows)}
    with open("xrp_census_touch_bound.json", "w") as f:
        json.dump(report, f, indent=2)
    print(json.dumps({"status": report["status"], "archive_count": len(manifests), **report["analysis"]}, indent=2))
