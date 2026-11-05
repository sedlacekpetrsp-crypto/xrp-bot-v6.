"""Cost-inclusive historical replay of the LIVE combined PAPER selection rule.

NOT YET EXECUTED on market data (2026-11-05): the session network blocked
data.binance.vision. See README.md for the exact procedure and frozen protocol.

Usage (public data only, no keys, no orders):
    python -m research.combined_selection_replay.run --cache /tmp/vision-1h \
        --end 2026-11-01 --out research/combined_selection_replay/results.json

Steps:
1. Download Binance Vision monthly 1h spot archives for BTC/ETH/SOL/XRP USDT,
   Sep 2020 .. month before --end. Archives up to 2026-09 must match the SHA256
   manifest of the 2026-10-22 VMM research run; mismatch aborts.
2. Keep only UTC days complete (24 bars) for all four assets; never fill bars.
3. CONTROL: re-run the unchanged VMM_V1 rule. All stored reference metrics must
   match within 1e-6; otherwise abort before evaluating the combined rule.
4. Evaluate the combined selection (select_candidates, live caps) per block at
   1x, 2x and 3x fee+slippage. Spot LONG only: no funding applies.
"""
import argparse
import csv
import hashlib
import io
import json
import math
import urllib.request
import zipfile
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from research.combined_best_signals_paper import select_candidates
from research.volatility_managed_momentum_v1 import Config, SYMBOLS, backtest

HERE = Path(__file__).resolve().parent
DAY_MS = 86_400_000
HOUR_MS = 3_600_000
COST_MULTIPLIERS = (1.0, 2.0, 3.0)
# Frozen before any combined-rule result exists. "contaminated" = these years were
# visible when the selection filters were written on 2026-11-04.
BLOCKS = (("2021", "2021-01-01", "2022-01-01", "development"),
          ("2022", "2022-01-01", "2023-01-01", "development"),
          ("2023", "2023-01-01", "2024-01-01", "contaminated_check"),
          ("2024", "2024-01-01", "2025-01-01", "contaminated_check"),
          ("2025", "2025-01-01", "2026-01-01", "contaminated_check"),
          ("2026_JAN_SEP", "2026-01-01", "2026-10-01", "contaminated_check"))
CONTAMINATED_ALL = ("2023-01-01", "2026-10-01")
FORWARD_START = "2026-10-01"  # first month never seen by VMM research or the filters


def ts(text):
    return int(datetime.fromisoformat(text).replace(tzinfo=timezone.utc).timestamp() * 1000)


def months(end_exclusive):
    year, month, out = 2020, 9, []
    while ts(f"{year}-{month:02d}-01") < ts(end_exclusive):
        out.append((year, month))
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return out


def parse_archive(payload, symbol, year, month):
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = [n for n in archive.namelist() if n.endswith(".csv")]
        if len(names) != 1:
            raise ValueError(f"Unexpected archive contents {symbol} {year}-{month:02d}")
        rows = list(csv.reader(io.TextIOWrapper(archive.open(names[0]), encoding="utf-8")))
    bars = []
    for row in rows:
        if not row or not row[0].isdigit():
            continue
        stamp = int(row[0])
        if stamp > 10**14:  # microsecond timestamps in newer archives
            stamp //= 1000
        bars.append({"timestamp": stamp, "open": float(row[1]), "high": float(row[2]),
                     "low": float(row[3]), "close": float(row[4]), "volume": float(row[5])})
    start = ts(f"{year}-{month:02d}-01")
    ny, nm = (year + 1, 1) if month == 12 else (year, month + 1)
    expected = set(range(start, ts(f"{ny}-{nm:02d}-01"), HOUR_MS))
    stamps = [b["timestamp"] for b in bars]
    if not stamps or stamps != sorted(set(stamps)) or not set(stamps) <= expected:
        raise ValueError(f"Invalid or unordered archive {symbol} {year}-{month:02d}")
    return bars


def load_market(cache, end_exclusive, reference_manifest, fetch=None):
    expected_hash = {m["url"]: m["sha256"] for m in reference_manifest}
    manifest, market = [], {s: [] for s in SYMBOLS}
    for symbol in SYMBOLS:
        for year, month in months(end_exclusive):
            name = f"{symbol}-1h-{year}-{month:02d}.zip"
            url = f"https://data.binance.vision/data/spot/monthly/klines/{symbol}/1h/{name}"
            path = Path(cache) / name
            if not path.exists():
                payload = (fetch or _fetch)(url)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(payload)
            payload = path.read_bytes()
            digest = hashlib.sha256(payload).hexdigest()
            if url in expected_hash and expected_hash[url] != digest:
                raise ValueError(f"SHA256 differs from reference manifest: {name}")
            bars = parse_archive(payload, symbol, year, month)
            market[symbol].extend(bars)
            manifest.append({"url": url, "sha256": digest, "bars": len(bars),
                             "in_reference_manifest": url in expected_hash})
    return align_complete_days(market), manifest


def _fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "paper-replay/1.0"})
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read()


def align_complete_days(market):
    complete = []
    for bars in market.values():
        counts = {}
        for bar in bars:
            day = bar["timestamp"] // DAY_MS * DAY_MS
            counts[day] = counts.get(day, 0) + 1
        complete.append({d for d, c in counts.items() if c == 24})
    common = set.intersection(*complete)
    return {s: [b for b in bars if b["timestamp"] // DAY_MS * DAY_MS in common]
            for s, bars in market.items()}


def combined_weights(daily, completed_index, config):
    return {c["symbol"]: c["weight"]
            for c in select_candidates(daily, completed_index, strategy=config)}


def scaled(config, multiplier):
    return replace(config, fee=config.fee * multiplier, slippage=config.slippage * multiplier)


def metrics(result, initial=10_000.0):
    trades = result["trades"]
    pnl = [t["net_pnl"] for t in trades]
    gain = sum(p for p in pnl if p > 0)
    loss = -sum(p for p in pnl if p < 0)
    net = result["ending_equity"] - initial
    top3 = sum(sorted(pnl, reverse=True)[:3])
    return {"trades": len(trades),
            "win_rate": sum(p > 0 for p in pnl) / len(pnl) if pnl else None,
            "net_pnl": net, "net_return": result["net_return"],
            "profit_factor": gain / loss if loss else (math.inf if gain else None),
            "max_drawdown": result["max_drawdown"],
            "fees": sum(t["fees"] for t in trades),
            "net_without_top3_trades": net - top3 if pnl else 0.0,
            "reasons": {r: sum(t["reason"] == r for t in trades)
                        for r in sorted({t["reason"] for t in trades})}}


def control_check(market, reference, tolerance=1e-6):
    """Reproduce the stored VMM_V1 metrics with the unchanged default rule."""
    base = Config()
    mismatches = []
    groups = (("development", 1.0, BLOCKS[:2]), ("development_double_costs", 2.0, BLOCKS[:2]),
              ("validation", 1.0, BLOCKS[2:]), ("validation_double_costs", 2.0, BLOCKS[2:]))
    for key, mult, blocks in groups:
        for name, start, end, _ in blocks:
            got = metrics(backtest(market, ts(start), ts(end), scaled(base, mult)))
            want = reference[key][name]
            for field in ("trades", "net_pnl", "max_drawdown", "profit_factor"):
                if want.get(field) is None or got[field] is None:
                    if want.get(field) != got[field]:
                        mismatches.append((key, name, field, want.get(field), got[field]))
                elif abs(float(want[field]) - float(got[field])) > tolerance:
                    mismatches.append((key, name, field, want[field], got[field]))
    return mismatches


def evaluate(market, end_exclusive):
    base = Config()
    out = {}
    for mult in COST_MULTIPLIERS:
        cfg = scaled(base, mult)
        row = {name: dict(metrics(backtest(market, ts(s), ts(e), cfg, combined_weights)), role=role)
               for name, s, e, role in BLOCKS}
        row["CONTAMINATED_2023_2026SEP_CONTINUOUS"] = metrics(backtest(
            market, ts(CONTAMINATED_ALL[0]), ts(CONTAMINATED_ALL[1]), cfg, combined_weights))
        if ts(end_exclusive) > ts(FORWARD_START):
            row["FORWARD_UNUSED"] = metrics(backtest(
                market, ts(FORWARD_START), ts(end_exclusive), cfg, combined_weights))
        out[f"cost_x{mult:g}"] = row
    return out


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", required=True)
    parser.add_argument("--end", required=True, help="exclusive month start, e.g. 2026-11-01")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    reference = json.loads((HERE / "reference_vmm_20261022.json").read_text())
    market, manifest = load_market(args.cache, args.end, reference["manifest"])
    mismatches = control_check(market, reference["reference_results"])
    report = {"strategy": "COMBINED_BEST_SIGNALS_V1 (live selection) historical replay",
              "end_exclusive": args.end, "control_mismatches": mismatches,
              "manifest": manifest}
    if mismatches:
        report["status"] = "ABORTED_CONTROL_MISMATCH"
    else:
        report["status"] = "EVALUATED"
        report["results"] = evaluate(market, args.end)
    Path(args.out).write_text(json.dumps(report, indent=1, default=str) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "manifest"}, indent=1, default=str))
    return 0 if not mismatches else 2


if __name__ == "__main__":
    raise SystemExit(main())
