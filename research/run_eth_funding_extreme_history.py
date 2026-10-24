"""Historical runner for ETH_FUNDING_EXTREME_REVERSAL_V1."""
import csv
import hashlib
import io
import json
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from research.eth_funding_extreme_reversal_v1 import Config, HOUR_MS, backtest, with_cost_stress

SYMBOL = "ETHUSDT"
MONTHS = [(y, m) for y in range(2020, 2027) for m in range(1, 13) if (2020, 12) <= (y, m) <= (2026, 9)]
DEV = (("2021", "2021-01-01", "2022-01-01"), ("2022", "2022-01-01", "2023-01-01"),
       ("2023", "2023-01-01", "2024-01-01"))
VAL = (("2024_H1", "2024-01-01", "2024-07-01"), ("2024_H2", "2024-07-01", "2025-01-01"),
       ("2025_H1", "2025-01-01", "2025-07-01"), ("2025_H2", "2025-07-01", "2026-01-01"),
       ("2026_JAN_SEP", "2026-01-01", "2026-10-01"))


def timestamp(value):
    return int(datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp() * 1000)


def download(kind, item):
    year, month = item
    leaf = "klines" if kind == "price" else "fundingRate"
    suffix = f"1h/{SYMBOL}-1h-{year}-{month:02d}.zip" if kind == "price" else f"{SYMBOL}-fundingRate-{year}-{month:02d}.zip"
    url = f"https://data.binance.vision/data/futures/um/monthly/{leaf}/{SYMBOL}/{suffix}"
    request = urllib.request.Request(url, headers={"User-Agent": "eth-funding-extreme/1.0"})
    with urllib.request.urlopen(request, timeout=90) as response:
        payload = response.read()
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = [name for name in archive.namelist() if name.endswith(".csv")]
        if len(names) != 1:
            raise ValueError(url)
        rows = list(csv.reader(io.TextIOWrapper(archive.open(names[0]), encoding="utf-8")))
    return rows, {"kind": kind, "symbol": SYMBOL, "url": url,
                  "sha256": hashlib.sha256(payload).hexdigest(), "rows": len(rows) - 1}


def fetch(item):
    price_rows, price_manifest = download("price", item)
    funding_rows, funding_manifest = download("funding", item)
    bars = []
    for row in price_rows:
        if not row or not row[0].isdigit():
            continue
        stamp = int(row[0]); stamp = stamp // 1000 if stamp > 10**14 else stamp
        bars.append({"timestamp": stamp, "open": float(row[1]), "high": float(row[2]),
                     "low": float(row[3]), "close": float(row[4])})
    rates = {}
    for row in funding_rows:
        if not row or not row[0].isdigit():
            continue
        stamp = int(row[0]); stamp = stamp // 1000 if stamp > 10**14 else stamp
        rates[stamp] = float(row[2])
    start = timestamp(f"{item[0]}-{item[1]:02d}-01")
    next_year, next_month = (item[0] + 1, 1) if item[1] == 12 else (item[0], item[1] + 1)
    expected = set(range(start, timestamp(f"{next_year}-{next_month:02d}-01"), HOUR_MS))
    stamps = [bar["timestamp"] for bar in bars]
    if not stamps or stamps != sorted(set(stamps)) or not set(stamps) <= expected:
        raise ValueError(price_manifest["url"])
    missing = sorted(expected - set(stamps))
    price_manifest.update({"expected_rows": len(expected), "missing_rows": len(missing),
                           "first_missing_timestamp": missing[0] if missing else None})
    if any(stamp < start or stamp >= timestamp(f"{next_year}-{next_month:02d}-01") for stamp in rates):
        raise ValueError(funding_manifest["url"])
    return bars, rates, [price_manifest, funding_manifest]


def metrics(result):
    trades = result["trades"]
    profit = sum(max(0, trade["net_pnl"]) for trade in trades)
    loss = -sum(min(0, trade["net_pnl"]) for trade in trades)
    return {"trades": len(trades), "longs": sum(t["side"] == 1 for t in trades),
            "shorts": sum(t["side"] == -1 for t in trades),
            "win_rate": sum(t["net_pnl"] > 0 for t in trades) / len(trades) if trades else None,
            "net_return": result["net_return"], "net_pnl": result["ending_equity"] - 10_000,
            "profit_factor": profit / loss if loss else None, "max_drawdown": result["max_drawdown"],
            "fees": sum(t["fees"] for t in trades), "funding_pnl": sum(t["funding_pnl"] for t in trades)}


def evaluate(bars, funding, blocks, config):
    return {name: metrics(backtest(bars, funding, timestamp(start), timestamp(end), config))
            for name, start, end in blocks}


def main():
    with ThreadPoolExecutor(max_workers=8) as pool:
        parts = list(pool.map(fetch, MONTHS))
    bars = [bar for part, _, _ in parts for bar in part]
    funding = {stamp: rate for _, rates, _ in parts for stamp, rate in rates.items()}
    manifest = [entry for _, _, entries in parts for entry in entries]
    config = Config(); stress = with_cost_stress(config)
    development = evaluate(bars, funding, DEV, config)
    development_stress = evaluate(bars, funding, DEV, stress)
    validation = evaluate(bars, funding, VAL, config)
    validation_stress = evaluate(bars, funding, VAL, stress)
    validation["ALL"] = metrics(backtest(bars, funding, timestamp("2024-01-01"), timestamp("2026-10-01"), config))
    validation_stress["ALL"] = metrics(backtest(bars, funding, timestamp("2024-01-01"), timestamp("2026-10-01"), stress))
    positive = sum(max(0, validation[name]["net_pnl"]) for name, *_ in VAL)
    share = max((max(0, validation[name]["net_pnl"]) for name, *_ in VAL), default=0) / positive if positive else 1.0
    count = validation["ALL"]["trades"]
    balance = min(validation["ALL"]["longs"], validation["ALL"]["shorts"]) / count if count else 0
    gate = {
        "development_positive_all_years": all(development[name]["net_return"] > 0 for name, *_ in DEV),
        "validation_minimum_80_trades": count >= 80,
        "validation_both_directions_at_least_20pct": balance >= 0.20,
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
        "strategy": "ETH_FUNDING_EXTREME_REVERSAL_V1",
        "data": "Binance ETHUSDT USD-M perpetual 1h klines and funding-rate archives",
        "development_period": "2021-01-01/2023-12-31", "validation_period": "2024-01-01/2026-09-30",
        "config": config.__dict__, "stress_config": stress.__dict__, "development": development,
        "development_stress": development_stress, "validation": validation,
        "validation_stress": validation_stress, "largest_positive_validation_block_share": share,
        "smaller_direction_share": balance, "gate": gate,
        "passes_historical_gate": all(value for key, value in gate.items() if key != "forward_paper_50_trades"),
        "robust_candidate": all(gate.values()), "manifest": manifest,
        "limitations": ["Hourly OHLC cannot reveal intrabar stop/target order; stop is assumed first.",
                        "Liquidations, maintenance margin and order-book impact are not modeled.",
                        "Funding archive timestamps are treated as known only for the following hourly entry.",
                        "Historical passage would still require 50 new forward PAPER trades."],
    }
    Path("research/eth_funding_extreme_results_20261024.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "manifest"}, indent=2))


if __name__ == "__main__":
    main()
