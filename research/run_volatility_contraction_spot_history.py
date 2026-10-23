"""Preregistered historical runner for VOLATILITY_CONTRACTION_SPOT_V1."""
import csv
import hashlib
import io
import json
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from research.volatility_contraction_spot_v1 import Config, backtest, with_double_costs


SYMBOL = "BTCUSDT"
MONTHS = [(year, month) for year in range(2020, 2027) for month in range(1, 13)
          if (year, month) >= (2020, 9) and (year, month) <= (2026, 9)]
DEVELOPMENT = (("2021", "2021-01-01", "2022-01-01"),
               ("2022", "2022-01-01", "2023-01-01"))
VALIDATION = (("2023", "2023-01-01", "2024-01-01"),
              ("2024", "2024-01-01", "2025-01-01"),
              ("2025", "2025-01-01", "2026-01-01"),
              ("2026_JAN_SEP", "2026-01-01", "2026-10-01"))
DAY_MS = 86_400_000


def timestamp(text):
    return int(datetime.fromisoformat(text).replace(tzinfo=timezone.utc).timestamp() * 1000)


def fetch(item):
    year, month = item
    filename = f"{SYMBOL}-1h-{year}-{month:02d}.zip"
    url = f"https://data.binance.vision/data/spot/monthly/klines/{SYMBOL}/1h/{filename}"
    request = urllib.request.Request(url, headers={"User-Agent": "vol-contraction-spot/1.0"})
    with urllib.request.urlopen(request, timeout=90) as response:
        payload = response.read()
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = [name for name in archive.namelist() if name.endswith(".csv")]
        if len(names) != 1:
            raise ValueError(f"Unexpected archive contents: {filename}")
        rows = list(csv.reader(io.TextIOWrapper(archive.open(names[0]), encoding="utf-8")))
    bars = []
    for row in rows:
        if not row or not row[0].isdigit():
            continue
        stamp = int(row[0])
        if stamp > 10**14:
            stamp //= 1000
        bars.append({"timestamp": stamp, "open": float(row[1]), "high": float(row[2]),
                     "low": float(row[3]), "close": float(row[4]), "volume": float(row[5])})
    start = timestamp(f"{year}-{month:02d}-01")
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
    end = timestamp(f"{next_year}-{next_month:02d}-01")
    expected = set(range(start, end, 3_600_000))
    stamps = [bar["timestamp"] for bar in bars]
    if not stamps or stamps != sorted(set(stamps)) or not set(stamps) <= expected:
        raise ValueError(f"Invalid or unordered archive: {filename}")
    missing = sorted(expected - set(stamps))
    return bars, {"symbol": SYMBOL, "url": url,
                  "sha256": hashlib.sha256(payload).hexdigest(), "bars": len(bars),
                  "expected_bars": len(expected), "missing_bars": len(missing),
                  "first_missing_timestamp": missing[0] if missing else None}


def metrics(result):
    trades = result["trades"]
    profit = sum(max(0.0, trade["net_pnl"]) for trade in trades)
    loss = -sum(min(0.0, trade["net_pnl"]) for trade in trades)
    return {"trades": len(trades),
            "win_rate": sum(trade["net_pnl"] > 0 for trade in trades) / len(trades) if trades else None,
            "net_return": result["net_return"], "net_pnl": result["ending_equity"] - 10_000.0,
            "profit_factor": profit / loss if loss else None,
            "max_drawdown": result["max_drawdown"],
            "fees": sum(trade["fees"] for trade in trades)}


def evaluate(bars, blocks, config):
    return {name: metrics(backtest(bars, timestamp(start), timestamp(end), config))
            for name, start, end in blocks}


def main():
    with ThreadPoolExecutor(max_workers=8) as pool:
        parts = list(pool.map(fetch, MONTHS))
    bars = [bar for part, _ in parts for bar in part]
    manifest = [item for _, item in parts]
    counts = {}
    for bar in bars:
        day = bar["timestamp"] // DAY_MS * DAY_MS
        counts[day] = counts.get(day, 0) + 1
    complete_days = {day for day, count in counts.items() if count == 24}
    dropped_days = sorted(set(counts) - complete_days)
    bars = [bar for bar in bars if bar["timestamp"] // DAY_MS * DAY_MS in complete_days]

    config = Config()
    development = evaluate(bars, DEVELOPMENT, config)
    development_stress = evaluate(bars, DEVELOPMENT, with_double_costs(config))
    validation = evaluate(bars, VALIDATION, config)
    validation_stress = evaluate(bars, VALIDATION, with_double_costs(config))
    validation["ALL"] = metrics(backtest(bars, timestamp("2023-01-01"), timestamp("2026-10-01"), config))
    validation_stress["ALL"] = metrics(backtest(
        bars, timestamp("2023-01-01"), timestamp("2026-10-01"), with_double_costs(config)))
    positive_profit = sum(max(0.0, validation[name]["net_pnl"]) for name, *_ in VALIDATION)
    largest_share = (max(max(0.0, validation[name]["net_pnl"]) for name, *_ in VALIDATION)
                     / positive_profit if positive_profit else 1.0)
    gate = {"development_positive": all(development[name]["net_return"] > 0 for name, *_ in DEVELOPMENT),
            "validation_minimum_trades": validation["ALL"]["trades"] >= 60,
            "normal_pf": (validation["ALL"]["profit_factor"] or 0) >= 1.25,
            "stress_pf": (validation_stress["ALL"]["profit_factor"] or 0) >= 1.10,
            "normal_positive_all_blocks": all(validation[name]["net_return"] > 0 for name, *_ in VALIDATION),
            "stress_positive_three_blocks": sum(validation_stress[name]["net_return"] > 0
                                                 for name, *_ in VALIDATION) >= 3,
            "stress_total_positive": validation_stress["ALL"]["net_return"] > 0,
            "max_drawdown": validation["ALL"]["max_drawdown"] <= 0.15,
            "profit_not_concentrated": largest_share <= 0.60,
            "forward_paper_30_trades": False}
    report = {"strategy": "VOLATILITY_CONTRACTION_SPOT_V1",
              "data": "Binance BTCUSDT spot 1h monthly archives",
              "development_period": "2021-01-01/2022-12-31",
              "validation_period": "2023-01-01/2026-09-30", "config": config.__dict__,
              "development": development, "development_double_costs": development_stress,
              "validation": validation, "validation_double_costs": validation_stress,
              "largest_positive_validation_block_share": largest_share, "gate": gate,
              "passes_historical_gate": all(value for key, value in gate.items()
                                              if key != "forward_paper_30_trades"),
              "robust_candidate": all(gate.values()),
              "coverage": {"complete_days": len(complete_days),
                           "dropped_incomplete_days": dropped_days}, "manifest": manifest,
              "limitations": ["A single BTC venue may not generalize to other exchanges.",
                              "Hourly OHLC cannot reveal sub-hour stop paths.",
                              "The fixed volatility ratio may be regime dependent.",
                              "Historical success would still require 30 new forward PAPER trades."]}
    Path("research/volatility_contraction_spot_results_20261023.json").write_text(
        json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "manifest"}, indent=2))


if __name__ == "__main__":
    main()
