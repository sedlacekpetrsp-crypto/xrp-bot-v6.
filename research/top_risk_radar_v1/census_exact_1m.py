"""Protocol-aligned OOS outcome census from Binance XRPUSDT 1m spot klines (RADAR-G1-LOWN).

DESCRIPTIVE ONLY: no model, no predictions, no P/L. Aligns the census with PROTOCOL.md ř. 6-8:
- decision 00:05:00 UTC; P(t) = OPEN of the 00:05 1m candle (= first trade in [00:05, 00:06),
  i.e. within 60 s); candle with 0 trades or missing => decision excluded with reason;
- risk label: any 1m LOW <= 0.8*P(t) in minutes [00:05, 00:05+336h) (1m LOW = min traded price);
- growth label (same convention): any 1m HIGH >= 1.3*P(t) within 720h;
- any missing minute inside the horizon => decision excluded (never filled).
Episode counts reported under both conventions (anchored, grouped > horizon), no rule chosen here.
"""
from __future__ import annotations
import csv, hashlib, io, json, os, re, zipfile
from datetime import datetime, timedelta, timezone
from research.top_risk_radar_v1.exploratory_kline_census import get
from research.top_risk_radar_v1.multiyear_census import month_range
from research.top_risk_radar_v1.episodes import group_positive_episodes
from research.top_risk_radar_v1.anchored_episodes import anchored_episodes

BASE1M = "https://data.binance.vision/data/spot/monthly/klines/XRPUSDT/1m/"
M = timedelta(minutes=1)


def parse_rows(lines):
    out = []
    for row in csv.reader(lines):
        if not row or row[0].lower().startswith("open"):
            continue
        if len(row) != 12:
            raise ValueError("bad candle")
        stamp = int(row[0])
        if 10**12 <= stamp < 10**14: divisor = 1000
        elif 10**15 <= stamp < 10**17: divisor = 1000000
        else: raise ValueError("unexpected timestamp")
        dt = datetime.fromtimestamp(stamp / divisor, tz=timezone.utc)
        o, hi, lo, n = float(row[1]), float(row[2]), float(row[3]), int(row[8])
        if min(o, hi, lo) <= 0 or lo > hi:
            raise ValueError("invalid candle")
        out.append((dt, o, hi, lo, n))
    return out


def load_month_1m(month):
    name = f"XRPUSDT-1m-{month}.zip"
    blob = get(BASE1M + name)
    chk = get(BASE1M + name + ".CHECKSUM").decode()
    m = re.search(r"\b([a-fA-F0-9]{64})\b", chk)
    if not m or hashlib.sha256(blob).hexdigest() != m.group(1).lower():
        raise ValueError(f"checksum mismatch: {month}")
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        files = [f for f in z.infolist() if not f.is_dir()]
        if len(files) != 1 or not files[0].filename.endswith(".csv"):
            raise ValueError("unexpected ZIP")
        with z.open(files[0]) as f:
            rows = parse_rows(io.TextIOWrapper(f, encoding="utf-8-sig"))
    return rows, {"month": month, "sha256": hashlib.sha256(blob).hexdigest(), "candles": len(rows)}


def evaluate(rows, risk_h=336, growth_h=720):
    rows = sorted(rows)
    t0 = rows[0][0]
    span = int((rows[-1][0] - t0) / M) + 1
    lows = [None] * span; highs = [None] * span; opens = [None] * span; ntr = [0] * span
    for dt, o, hi, lo, n in rows:
        i = int((dt - t0) / M)
        if lows[i] is not None:
            raise ValueError("duplicate timestamps")
        lows[i], highs[i], opens[i], ntr[i] = lo, hi, o, n
    miss_prefix = [0]
    for v in lows:
        miss_prefix.append(miss_prefix[-1] + (v is None))
    reasons = {"no_trade_in_first_60s": 0, "missing_minutes_in_horizon": 0}
    growth, risk = [], []
    matured = 0
    gm, rm = growth_h * 60, risk_h * 60
    day = datetime(t0.year, t0.month, t0.day, 0, 5, tzinfo=timezone.utc)
    if day < t0:
        day += timedelta(days=1)
    while True:
        i = int((day - t0) / M)
        if i + gm > span:
            break
        if lows[i] is None or ntr[i] == 0:
            reasons["no_trade_in_first_60s"] += 1
        elif miss_prefix[i + gm] - miss_prefix[i] > 0:
            reasons["missing_minutes_in_horizon"] += 1
        else:
            p = opens[i]; matured += 1
            if min(lows[i:i + rm]) <= 0.8 * p:
                risk.append(day)
            if max(highs[i:i + gm]) >= 1.3 * p:
                growth.append(day)
        day += timedelta(days=1)

    def grouped(d, days):
        return len(group_positive_episodes(d, [True] * len(d), max_separation=timedelta(days=days)))

    return {"matured_decisions": matured, "excluded": reasons,
            "growth_positive_decisions": len(growth), "risk_positive_decisions": len(risk),
            "anchored_growth_episodes_30d": len(anchored_episodes(growth, horizon_days=30)),
            "grouped_growth_episodes_30d": grouped(growth, 30),
            "anchored_risk_episodes_14d": len(anchored_episodes(risk, horizon_days=14)),
            "grouped_risk_episodes_14d": grouped(risk, 14),
            "risk_episode_first_dates_grouped": [e["first_decision"].date().isoformat() for e in
                group_positive_episodes(risk, [True] * len(risk), max_separation=timedelta(days=14))]}


if __name__ == "__main__":
    months = month_range(os.environ.get("CENSUS_START", "2022-01"), os.environ.get("CENSUS_END", "2026-10"))
    rows, manifests = [], []
    for month in months:
        part, meta = load_month_1m(month)
        rows.extend(part); manifests.append(meta)
    report = {"status": "DESCRIPTIVE_PROTOCOL_ALIGNED_NOT_PREDICTION",
              "reference": "00:05 UTC 1m candle OPEN (first trade within 60 s); 1m LOW/HIGH barrier",
              "months": f"{months[0]}..{months[-1]}", "sources": manifests, "analysis": evaluate(rows)}
    with open("xrp_census_exact_1m.json", "w") as f:
        json.dump(report, f, indent=2)
    a = dict(report["analysis"]); a.pop("risk_episode_first_dates_grouped")
    print(json.dumps({"status": report["status"], "archive_count": len(manifests), **a,
                      "risk_grouped_first_dates": report["analysis"]["risk_episode_first_dates_grouped"]}, indent=2))
