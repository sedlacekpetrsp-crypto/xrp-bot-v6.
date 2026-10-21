"""Historical runner for SOL_ETH_PAIRS_V1 using public spot archives."""
import csv
import hashlib
import io
import json
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from research.sol_eth_pairs_v1 import Config, backtest, with_double_costs


SYMBOLS = ("SOLUSDT", "ETHUSDT")
MONTHS = [(year, month) for year in range(2022, 2027) for month in range(1, 13)
          if (year, month) >= (2022, 11) and (year, month) <= (2026, 9)]
BLOCKS = (("2023", "2023-01-01", "2024-01-01"),
          ("2024", "2024-01-01", "2025-01-01"),
          ("2025", "2025-01-01", "2026-01-01"),
          ("2026_JAN_SEP", "2026-01-01", "2026-10-01"))
DAY_MS = 86_400_000


def timestamp(text):
    return int(datetime.fromisoformat(text).replace(tzinfo=timezone.utc).timestamp() * 1000)


def fetch(item):
    symbol, year, month = item
    filename = f"{symbol}-1h-{year}-{month:02d}.zip"
    url = f"https://data.binance.vision/data/spot/monthly/klines/{symbol}/1h/{filename}"
    request = urllib.request.Request(url, headers={"User-Agent": "pairs-research/1.0"})
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
    return symbol, bars, {"symbol": symbol, "url": url,
                          "sha256": hashlib.sha256(payload).hexdigest(),
                          "bars": len(bars), "expected_bars": len(expected),
                          "missing_bars": len(missing),
                          "first_missing_timestamp": missing[0] if missing else None}


def metrics(result):
    trades = result["trades"]
    wins = sum(max(0.0, trade["net_pnl"]) for trade in trades)
    losses = -sum(min(0.0, trade["net_pnl"]) for trade in trades)
    return {"trades": len(trades),
            "win_rate": sum(trade["net_pnl"] > 0 for trade in trades) / len(trades) if trades else None,
            "net_return": result["net_return"],
            "net_pnl": result["ending_equity"] - 10_000.0,
            "profit_factor": wins / losses if losses else None,
            "max_drawdown": result["max_drawdown"],
            "fees": sum(trade["fees"] for trade in trades),
            "borrow_cost": sum(trade["borrow_cost"] for trade in trades)}


def main():
    jobs = [(symbol, year, month) for symbol in SYMBOLS for year, month in MONTHS]
    with ThreadPoolExecutor(max_workers=8) as pool:
        parts = list(pool.map(fetch, jobs))
    market = {symbol: [] for symbol in SYMBOLS}
    manifest = []
    for symbol, bars, item in parts:
        market[symbol].extend(bars)
        manifest.append(item)
    complete_by_symbol = {}
    observed_days = set()
    for symbol, bars in market.items():
        counts = {}
        for bar in bars:
            day = bar["timestamp"] // DAY_MS * DAY_MS
            counts[day] = counts.get(day, 0) + 1
        observed_days.update(counts)
        complete_by_symbol[symbol] = {day for day, count in counts.items() if count == 24}
    common_days = set.intersection(*complete_by_symbol.values())
    dropped_days = sorted(observed_days - common_days)
    market = {symbol: [bar for bar in bars if bar["timestamp"] // DAY_MS * DAY_MS in common_days]
              for symbol, bars in market.items()}

    config = Config()
    normal, stress = {}, {}
    for name, start, end in BLOCKS:
        normal[name] = metrics(backtest(market, timestamp(start), timestamp(end), config))
        stress[name] = metrics(backtest(market, timestamp(start), timestamp(end), with_double_costs(config)))
    start, end = timestamp("2023-01-01"), timestamp("2026-10-01")
    normal["ALL"] = metrics(backtest(market, start, end, config))
    stress["ALL"] = metrics(backtest(market, start, end, with_double_costs(config)))
    gate = {"minimum_trades": normal["ALL"]["trades"] >= 50,
            "normal_pf": (normal["ALL"]["profit_factor"] or 0) >= 1.25,
            "stress_pf": (stress["ALL"]["profit_factor"] or 0) >= 1.05,
            "normal_positive_all_blocks": all(normal[name]["net_return"] > 0 for name, *_ in BLOCKS),
            "stress_positive_three_blocks": sum(stress[name]["net_return"] > 0 for name, *_ in BLOCKS) >= 3,
            "stress_total_positive": stress["ALL"]["net_return"] > 0,
            "max_drawdown": normal["ALL"]["max_drawdown"] <= 0.12,
            "forward_paper_40_trades": False}
    report = {"strategy": "SOL_ETH_PAIRS_V1", "period": "2023-01-01/2026-09-30",
              "data": "Binance spot 1h monthly archives", "config": config.__dict__,
              "normal": normal, "double_costs": stress, "gate": gate,
              "passes_historical_gate": all(value for key, value in gate.items()
                                              if key != "forward_paper_40_trades"),
              "robust_candidate": all(gate.values()),
              "coverage": {"common_complete_days": len(common_days),
                           "dropped_incomplete_or_unaligned_days": dropped_days},
              "manifest": manifest,
              "limitations": ["Hourly OHLC cannot reproduce sub-hour path ordering.",
                              "Borrow is modeled at a fixed annual rate, not historical exchange rates.",
                              "Historical success would still require 40 new forward PAPER trades."]}
    Path("research/sol_eth_pairs_results_20261021.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "manifest"}, indent=2))


if __name__ == "__main__":
    main()
