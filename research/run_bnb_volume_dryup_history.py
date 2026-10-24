"""Historical runner for BNB_VOLUME_DRYUP_V1."""
import csv
import hashlib
import io
import json
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from research.bnb_volume_dryup_v1 import Config, HOUR_MS, backtest, with_double_costs

SYMBOL = "BNBUSDT"
MONTHS = [(y, m) for y in range(2020, 2027) for m in range(1, 13) if (2020, 11) <= (y, m) <= (2026, 9)]
DEV = (("2021", "2021-01-01", "2022-01-01"), ("2022", "2022-01-01", "2023-01-01"),
       ("2023", "2023-01-01", "2024-01-01"))
VAL = (("2024_H1", "2024-01-01", "2024-07-01"), ("2024_H2", "2024-07-01", "2025-01-01"),
       ("2025_H1", "2025-01-01", "2025-07-01"), ("2025_H2", "2025-07-01", "2026-01-01"),
       ("2026_JAN_SEP", "2026-01-01", "2026-10-01"))


def timestamp(value):
    return int(datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp() * 1000)


def fetch(item):
    year, month = item
    filename = f"{SYMBOL}-1h-{year}-{month:02d}.zip"
    url = f"https://data.binance.vision/data/spot/monthly/klines/{SYMBOL}/1h/{filename}"
    request = urllib.request.Request(url, headers={"User-Agent": "bnb-volume-dryup/1.0"})
    with urllib.request.urlopen(request, timeout=90) as response:
        payload = response.read()
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = [name for name in archive.namelist() if name.endswith(".csv")]
        if len(names) != 1:
            raise ValueError(filename)
        rows = list(csv.reader(io.TextIOWrapper(archive.open(names[0]), encoding="utf-8")))
    bars = []
    for row in rows:
        if not row or not row[0].isdigit():
            continue
        stamp = int(row[0])
        stamp = stamp // 1000 if stamp > 10**14 else stamp
        bars.append({"timestamp": stamp, "open": float(row[1]), "high": float(row[2]),
                     "low": float(row[3]), "close": float(row[4]), "quote_volume": float(row[7])})
    start = timestamp(f"{year}-{month:02d}-01")
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
    expected = set(range(start, timestamp(f"{next_year}-{next_month:02d}-01"), HOUR_MS))
    stamps = [bar["timestamp"] for bar in bars]
    if not stamps or stamps != sorted(set(stamps)) or not set(stamps) <= expected:
        raise ValueError(filename)
    missing = sorted(expected - set(stamps))
    return bars, {"symbol": SYMBOL, "url": url, "sha256": hashlib.sha256(payload).hexdigest(),
                  "bars": len(bars), "expected_bars": len(expected), "missing_bars": len(missing),
                  "first_missing_timestamp": missing[0] if missing else None}


def metrics(result):
    trades = result["trades"]
    profit = sum(max(0, trade["net_pnl"]) for trade in trades)
    loss = -sum(min(0, trade["net_pnl"]) for trade in trades)
    return {"trades": len(trades), "win_rate": sum(t["net_pnl"] > 0 for t in trades) / len(trades) if trades else None,
            "net_return": result["net_return"], "net_pnl": result["ending_equity"] - 10_000,
            "profit_factor": profit / loss if loss else None, "max_drawdown": result["max_drawdown"],
            "fees": sum(t["fees"] for t in trades)}


def evaluate(bars, blocks, config):
    return {name: metrics(backtest(bars, timestamp(start), timestamp(end), config))
            for name, start, end in blocks}


def main():
    with ThreadPoolExecutor(max_workers=8) as pool:
        parts = list(pool.map(fetch, MONTHS))
    bars = [bar for part, _ in parts for bar in part]
    manifest = [entry for _, entry in parts]
    config = Config()
    development = evaluate(bars, DEV, config)
    development_stress = evaluate(bars, DEV, with_double_costs(config))
    validation = evaluate(bars, VAL, config)
    validation_stress = evaluate(bars, VAL, with_double_costs(config))
    validation["ALL"] = metrics(backtest(bars, timestamp("2024-01-01"), timestamp("2026-10-01"), config))
    validation_stress["ALL"] = metrics(backtest(bars, timestamp("2024-01-01"), timestamp("2026-10-01"), with_double_costs(config)))
    positive = sum(max(0, validation[name]["net_pnl"]) for name, *_ in VAL)
    share = max((max(0, validation[name]["net_pnl"]) for name, *_ in VAL), default=0) / positive if positive else 1.0
    gate = {
        "development_positive_all_years": all(development[name]["net_return"] > 0 for name, *_ in DEV),
        "validation_minimum_80_trades": validation["ALL"]["trades"] >= 80,
        "normal_pf_at_least_1_20": (validation["ALL"]["profit_factor"] or 0) >= 1.20,
        "stress_pf_at_least_1_05": (validation_stress["ALL"]["profit_factor"] or 0) >= 1.05,
        "normal_positive_all_blocks": all(validation[name]["net_return"] > 0 for name, *_ in VAL),
        "stress_positive_four_blocks": sum(validation_stress[name]["net_return"] > 0 for name, *_ in VAL) >= 4,
        "stress_total_positive": validation_stress["ALL"]["net_return"] > 0,
        "normal_max_drawdown_at_most_15pct": validation["ALL"]["max_drawdown"] <= 0.15,
        "profit_not_concentrated": share <= 0.50,
        "forward_paper_50_trades": False,
    }
    report = {
        "strategy": "BNB_VOLUME_DRYUP_V1", "data": "Binance BNBUSDT spot 1h monthly archives",
        "development_period": "2021-01-01/2023-12-31", "validation_period": "2024-01-01/2026-09-30",
        "config": config.__dict__, "double_cost_config": with_double_costs(config).__dict__,
        "development": development, "development_double_cost": development_stress,
        "validation": validation, "validation_double_cost": validation_stress,
        "largest_positive_validation_block_share": share, "gate": gate,
        "passes_historical_gate": all(value for key, value in gate.items() if key != "forward_paper_50_trades"),
        "robust_candidate": all(gate.values()), "manifest": manifest,
        "limitations": ["Hourly OHLC cannot reveal intrabar stop/target order; stop is assumed first.",
                        "Quote-volume behavior on one exchange and one asset may not generalize.",
                        "Historical passage would still require 50 new forward PAPER trades."],
    }
    Path("research/bnb_volume_dryup_results_20261024.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "manifest"}, indent=2))


if __name__ == "__main__":
    main()
