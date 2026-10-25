"""Download Binance funding and spot bars; run the frozen OOS screen."""
import concurrent.futures
import csv
import gzip
import hashlib
import io
import json
import pathlib
import sys
import urllib.request
import zipfile
from dataclasses import replace

from research.funding_reversal_v1 import Config, STEP, backtest, validate
from research.run_autocorr_history import metrics as score, stamp

MONTHS = [(y, m) for y in range(2022, 2027) for m in range(1, 13) if (y, m) < (2026, 10)]


def get(url, path):
    if not path.exists():
        with urllib.request.urlopen(url, timeout=45) as response:
            path.write_bytes(response.read())
    return path.read_bytes()


def fetch_funding(job):
    y, m, cache = job
    name = f"XRPUSDT-fundingRate-{y}-{m:02d}.zip"
    url = f"https://data.binance.vision/data/futures/um/monthly/fundingRate/XRPUSDT/{name}"
    payload = get(url, cache / name)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        members = archive.namelist()
        if members != [name[:-4] + ".csv"]:
            raise ValueError("unexpected funding archive")
        rows = list(csv.DictReader(io.TextIOWrapper(archive.open(members[0]))))
    output = [
        dict(timestamp=int(r["calc_time"]), interval_hours=int(r["funding_interval_hours"]), rate=float(r["last_funding_rate"]))
        for r in rows
    ]
    return output, dict(url=url, sha256=hashlib.sha256(payload).hexdigest(), bytes=len(payload), rows=len(output))


def fetch_spot(job):
    y, m, cache = job
    name = f"XRPUSDT-1h-{y}-{m:02d}.zip"
    url = f"https://data.binance.vision/data/spot/monthly/klines/XRPUSDT/1h/{name}"
    payload = get(url, cache / name)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        members = archive.namelist()
        if members != [name[:-4] + ".csv"]:
            raise ValueError("unexpected spot archive")
        rows = list(csv.reader(io.TextIOWrapper(archive.open(members[0]))))
    output = []
    for row in rows:
        timestamp = int(row[0])
        timestamp = timestamp // 1000 if timestamp > 10**14 else timestamp
        output.append(dict(timestamp=timestamp, open=float(row[1]), high=float(row[2]), low=float(row[3]), close=float(row[4])))
    return output, dict(url=url, sha256=hashlib.sha256(payload).hexdigest(), bytes=len(payload), rows=len(output))


def aggregate(trades):
    wins = sum(max(0, t["pnl"]) for t in trades)
    losses = -sum(min(0, t["pnl"]) for t in trades)
    return dict(
        trades=len(trades),
        net_pnl=wins-losses,
        profit_factor=wins/losses if losses else None,
        expectancy=(wins-losses)/len(trades) if trades else None,
    )


def quarter_folds():
    folds = [("2022_control", stamp(2022, 1), stamp(2023, 1))]
    for year in range(2023, 2027):
        for quarter, month in enumerate((1, 4, 7, 10), 1):
            if (year, month) >= (2026, 10):
                continue
            end_year, end_month = (year + 1, 1) if month == 10 else (year, month + 3)
            folds.append((f"{year}Q{quarter}", stamp(year, month), stamp(end_year, end_month)))
    folds.append(("continuous_oos", stamp(2023, 1), stamp(2026, 10)))
    return folds


def main():
    cache = pathlib.Path(sys.argv[1]); cache.mkdir(parents=True, exist_ok=True)
    destination = pathlib.Path(sys.argv[2]); destination.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        funding_chunks = list(pool.map(fetch_funding, [(y, m, cache) for y, m in MONTHS]))
        spot_chunks = list(pool.map(fetch_spot, [(y, m, cache) for y, m in MONTHS]))
    raw_funding = [x for chunk, _ in funding_chunks for x in chunk]
    raw_bars = [x for chunk, _ in spot_chunks for x in chunk]
    funding_map = {x["timestamp"]: x for x in raw_funding}
    bar_map = {x["timestamp"]: x for x in raw_bars}
    funding = [funding_map[t] for t in sorted(funding_map)]
    bars = [bar_map[t] for t in sorted(bar_map)]
    validate(bars, funding)
    quality = dict(
        funding_duplicates=len(raw_funding)-len(funding_map),
        spot_duplicates=len(raw_bars)-len(bar_map),
        spot_gap_hours=[(a["timestamp"], b["timestamp"], (b["timestamp"]-a["timestamp"])//STEP-1) for a, b in zip(bars, bars[1:]) if b["timestamp"]-a["timestamp"] != STEP],
        funding_unexpected_gaps=[(a["timestamp"], b["timestamp"], a["interval_hours"]) for a, b in zip(funding, funding[1:]) if b["timestamp"]-a["timestamp"] != a["interval_hours"]*STEP],
    )
    runs, ledger = {}, {}
    for name, start, end in quarter_folds():
        for cost, multiplier in (("base", 1), ("stress", 2)):
            config = replace(Config(), fee=Config().fee*multiplier, slippage=Config().slippage*multiplier)
            trades = backtest(bars, funding, start, end, config)
            key = f"{name}_{cost}"
            runs[key] = score(bars, trades, 10_000, config)
            runs[key]["slippage_cost"] = sum(t["slippage_cost"] for t in trades)
            ledger[key] = [dict(t, entry_timestamp=bars[t["entry_index"]]["timestamp"], exit_timestamp=bars[t["exit_index"]]["timestamp"]) for t in trades]
            print(key, runs[key], flush=True)
    quarters = [name for name, _, _ in quarter_folds() if name not in ("2022_control", "continuous_oos")]
    base_trades = [t for q in quarters for t in ledger[f"{q}_base"]]
    stress_trades = [t for q in quarters for t in ledger[f"{q}_stress"]]
    base, stress = aggregate(base_trades), aggregate(stress_trades)
    by_quarter = {q: runs[f"{q}_base"]["net_pnl"] for q in quarters}
    positive_total = sum(max(0, value) for value in by_quarter.values())
    gates = dict(
        sample=base["trades"] >= 150,
        base_net=base["net_pnl"] > 0,
        base_expectancy=(base["expectancy"] or 0) > 0,
        base_pf=(base["profit_factor"] or 0) > 1.15,
        stress_net=stress["net_pnl"] > 0,
        stress_expectancy=(stress["expectancy"] or 0) > 0,
        stress_pf=(stress["profit_factor"] or 0) > 1.02,
        ten_positive_quarters=sum(value > 0 for value in by_quarter.values()) >= 10,
        final_quarter=by_quarter["2026Q3"] > 0,
        drawdown=all(runs[f"continuous_oos_{cost}"]["max_drawdown_pct"] <= 10 for cost in ("base", "stress")),
        concentration=base["net_pnl"] > 0 and positive_total > 0 and max(by_quarter.values()) <= 0.30*positive_total,
    )
    protocol = pathlib.Path("research/funding_reversal_protocol.md")
    result = dict(
        strategy="XRP_FUNDING_DISLOCATION_REVERSAL_V1",
        status="NEPROSEL" if not all(gates.values()) else "TEST NEDOKONCEN: forward evidence required",
        protocol=str(protocol),
        protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),
        manifest=[source for _, source in funding_chunks+spot_chunks],
        data_quality=quality,
        runs=runs,
        aggregate_oos=base,
        aggregate_stress=stress,
        by_quarter=by_quarter,
        gates=gates,
        limitations=["Exploratory historical evidence.", "Local SHA256 are not publisher signatures.", "Funding informs spot-only trades; no funding cashflow is claimed.", "No independent forward PAPER evidence."],
    )
    (destination/"results.json").write_text(json.dumps(result, indent=2, allow_nan=False)+"\n")
    with gzip.open(destination/"trades.json.gz", "wt") as handle:
        json.dump(ledger, handle)
    print(result["status"], gates)


if __name__ == "__main__":
    main()
