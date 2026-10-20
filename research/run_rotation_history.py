"""Historical runner for CROSS_SECTIONAL_ROTATION_V1; public archives only."""
import csv
import hashlib
import io
import json
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from research.cross_sectional_rotation_v1 import Config, backtest, with_double_costs


SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT")
MONTHS = [(year, month) for year in range(2022, 2027) for month in range(1, 13)
          if (year, month) >= (2022, 10) and (year, month) <= (2026, 9)]
BLOCKS = (
    ("2023", "2023-01-01", "2024-01-01"),
    ("2024", "2024-01-01", "2025-01-01"),
    ("2025", "2025-01-01", "2026-01-01"),
    ("2026_JAN_SEP", "2026-01-01", "2026-10-01"),
)


def _timestamp(text):
    return int(datetime.fromisoformat(text).replace(tzinfo=timezone.utc).timestamp() * 1000)


def fetch(item):
    symbol, year, month = item
    filename = f"{symbol}-15m-{year}-{month:02d}.zip"
    url = f"https://data.binance.vision/data/spot/monthly/klines/{symbol}/15m/{filename}"
    request = urllib.request.Request(url, headers={"User-Agent": "rotation-research/1.0"})
    with urllib.request.urlopen(request, timeout=90) as response:
        payload = response.read()
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = [x for x in archive.namelist() if x.endswith(".csv")]
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
    start = _timestamp(f"{year}-{month:02d}-01")
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
    end = _timestamp(f"{next_year}-{next_month:02d}-01")
    stamps = [x["timestamp"] for x in bars]
    expected = set(range(start, end, 900_000))
    if (not stamps or stamps != sorted(set(stamps)) or not set(stamps) <= expected):
        raise ValueError(f"Invalid or unordered archive: {filename}")
    missing = sorted(expected - set(stamps))
    return symbol, bars, {"url": url, "sha256": hashlib.sha256(payload).hexdigest(),
                          "bars": len(bars), "expected_bars": len(expected),
                          "missing_bars": len(missing),
                          "first_missing_timestamp": missing[0] if missing else None}


def metrics(result):
    trades = result["trades"]
    profit = sum(max(0.0, x["net_pnl"]) for x in trades)
    loss = -sum(min(0.0, x["net_pnl"]) for x in trades)
    return {"trades": len(trades),
            "win_rate": sum(x["net_pnl"] > 0 for x in trades) / len(trades) if trades else None,
            "net_return": result["net_return"], "net_pnl": result["ending_equity"] - 10_000.0,
            "profit_factor": profit / loss if loss else None,
            "max_drawdown": result["max_drawdown"]}


def main():
    jobs = [(symbol, year, month) for symbol in SYMBOLS for year, month in MONTHS]
    with ThreadPoolExecutor(max_workers=8) as pool:
        parts = list(pool.map(fetch, jobs))
    market = {symbol: [] for symbol in SYMBOLS}
    manifest = []
    for symbol, bars, item in parts:
        market[symbol].extend(bars)
        manifest.append({"symbol": symbol, **item})
    # Never fabricate outage candles.  Retain only UTC days that are complete
    # for every asset, so ranking and fills always share identical timestamps.
    complete_by_symbol = {}
    for symbol, bars in market.items():
        counts = {}
        for bar in bars:
            counts[bar["timestamp"] // 86_400_000 * 86_400_000] = counts.get(
                bar["timestamp"] // 86_400_000 * 86_400_000, 0) + 1
        complete_by_symbol[symbol] = {day for day, count in counts.items() if count == 96}
    common_days = set.intersection(*complete_by_symbol.values())
    dropped_days = sorted(set.union(*[set(x for x in days) for days in complete_by_symbol.values()]) - common_days)
    market = {symbol: [bar for bar in bars
                       if bar["timestamp"] // 86_400_000 * 86_400_000 in common_days]
              for symbol, bars in market.items()}
    config = Config()
    normal = {}
    stress = {}
    for name, start, end in BLOCKS:
        normal[name] = metrics(backtest(market, _timestamp(start), _timestamp(end), config))
        stress[name] = metrics(backtest(market, _timestamp(start), _timestamp(end), with_double_costs(config)))
    start, end = _timestamp("2023-01-01"), _timestamp("2026-10-01")
    normal["ALL"] = metrics(backtest(market, start, end, config))
    stress["ALL"] = metrics(backtest(market, start, end, with_double_costs(config)))
    gate = {"minimum_trades": normal["ALL"]["trades"] >= 80,
            "normal_pf": (normal["ALL"]["profit_factor"] or 0) >= 1.20,
            "stress_pf": (stress["ALL"]["profit_factor"] or 0) >= 1.05,
            "normal_positive_all_blocks": all(normal[x]["net_return"] > 0 for x, *_ in BLOCKS),
            "stress_positive_three_blocks": sum(stress[x]["net_return"] > 0 for x, *_ in BLOCKS) >= 3,
            "stress_total_positive": stress["ALL"]["net_return"] > 0,
            "max_drawdown": normal["ALL"]["max_drawdown"] <= 0.15,
            "forward_paper_30_trades": False}
    report = {"strategy": "CROSS_SECTIONAL_ROTATION_V1", "data": "Binance spot 15m monthly archives",
              "period": "2023-01-01/2026-09-30", "config": config.__dict__, "normal": normal,
              "double_costs": stress, "gate": gate, "passes_historical_gate": all(v for k, v in gate.items()
                                                                                   if k != "forward_paper_30_trades"),
              "robust_candidate": all(gate.values()), "manifest": manifest,
              "coverage": {"common_complete_days": len(common_days),
                           "dropped_incomplete_or_unaligned_days": dropped_days},
              "limitations": ["OHLC path cannot reproduce sub-bar execution.",
                              "Spot universe excludes delisted assets and survivorship is possible.",
                              "Historical success would still require 30 new forward PAPER trades."]}
    Path("research/cross_sectional_rotation_results_20261020.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "manifest"}, indent=2))


if __name__ == "__main__":
    main()
