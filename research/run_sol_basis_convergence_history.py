"""Historical runner for SOL_BASIS_CONVERGENCE_V1."""
import csv, hashlib, io, json, urllib.request, zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from research.sol_basis_convergence_v1 import Config, HOUR_MS, backtest, with_cost_stress

SYMBOL = "SOLUSDT"
MONTHS = [(y, m) for y in range(2020, 2027) for m in range(1, 13) if (2020, 12) <= (y, m) <= (2026, 9)]
DEV = (("2021", "2021-01-01", "2022-01-01"), ("2022", "2022-01-01", "2023-01-01"), ("2023", "2023-01-01", "2024-01-01"))
VAL = (("2024_H1", "2024-01-01", "2024-07-01"), ("2024_H2", "2024-07-01", "2025-01-01"),
       ("2025_H1", "2025-01-01", "2025-07-01"), ("2025_H2", "2025-07-01", "2026-01-01"),
       ("2026_JAN_SEP", "2026-01-01", "2026-10-01"))


def timestamp(value): return int(datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp() * 1000)


def normalize_funding_timestamp(value):
    stamp = int(value); stamp = stamp // 1000 if stamp > 10**14 else stamp; offset = stamp % HOUR_MS
    if offset > 1_000: raise ValueError(f"Non-nominal funding timestamp: {stamp}")
    return stamp - offset


def download(kind, item):
    y, m = item
    if kind == "spot": url = f"https://data.binance.vision/data/spot/monthly/klines/{SYMBOL}/1h/{SYMBOL}-1h-{y}-{m:02d}.zip"
    elif kind == "perp": url = f"https://data.binance.vision/data/futures/um/monthly/klines/{SYMBOL}/1h/{SYMBOL}-1h-{y}-{m:02d}.zip"
    else: url = f"https://data.binance.vision/data/futures/um/monthly/fundingRate/{SYMBOL}/{SYMBOL}-fundingRate-{y}-{m:02d}.zip"
    request = urllib.request.Request(url, headers={"User-Agent": "sol-basis-convergence/1.0"})
    with urllib.request.urlopen(request, timeout=90) as response: payload = response.read()
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = [name for name in archive.namelist() if name.endswith(".csv")]
        if len(names) != 1: raise ValueError(url)
        rows = list(csv.reader(io.TextIOWrapper(archive.open(names[0]), encoding="utf-8")))
    return rows, {"kind": kind, "url": url, "sha256": hashlib.sha256(payload).hexdigest(), "rows": len(rows) - 1}


def fetch(item):
    spot_rows, sm = download("spot", item); perp_rows, pm = download("perp", item); funding_rows, fm = download("funding", item)
    def prices(rows):
        answer = {}
        for row in rows:
            if row and row[0].isdigit():
                stamp = int(row[0]); stamp = stamp // 1000 if stamp > 10**14 else stamp
                answer[stamp] = (float(row[1]), float(row[4]))
        return answer
    spot = prices(spot_rows); perp = prices(perp_rows); common = sorted(set(spot) & set(perp))
    bars = [{"timestamp": ts, "spot_open": spot[ts][0], "spot_close": spot[ts][1],
             "perp_open": perp[ts][0], "perp_close": perp[ts][1]} for ts in common]
    rates = {normalize_funding_timestamp(row[0]): float(row[2]) for row in funding_rows if row and row[0].isdigit()}
    y, m = item; start = timestamp(f"{y}-{m:02d}-01"); ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
    expected = set(range(start, timestamp(f"{ny}-{nm:02d}-01"), HOUR_MS))
    for manifest, data in ((sm, spot), (pm, perp)):
        missing = sorted(expected - set(data)); manifest.update({"expected_rows": len(expected), "missing_rows": len(missing),
                                                                 "first_missing_timestamp": missing[0] if missing else None})
    missing_common = sorted(expected - set(common)); sm["missing_synchronized_rows"] = len(missing_common)
    return bars, rates, [sm, pm, fm]


def metrics(result):
    trades = result["trades"]; profit = sum(max(0, t["net_pnl"]) for t in trades); loss = -sum(min(0, t["net_pnl"]) for t in trades)
    return {"trades": len(trades), "win_rate": sum(t["net_pnl"] > 0 for t in trades) / len(trades) if trades else None,
            "net_return": result["net_return"], "net_pnl": result["ending_equity"] - 10_000,
            "profit_factor": profit / loss if loss else None, "max_drawdown": result["max_drawdown"],
            "fees": sum(t["fees"] for t in trades), "funding_pnl": sum(t["funding_pnl"] for t in trades)}


def evaluate(bars, funding, blocks, config):
    return {name: metrics(backtest(bars, funding, timestamp(start), timestamp(end), config)) for name, start, end in blocks}


def main():
    with ThreadPoolExecutor(max_workers=8) as pool: parts = list(pool.map(fetch, MONTHS))
    bars = [bar for part, _, _ in parts for bar in part]; funding = {ts: rate for _, rates, _ in parts for ts, rate in rates.items()}
    manifest = [entry for _, _, entries in parts for entry in entries]; config = Config(); stress = with_cost_stress(config)
    dev = evaluate(bars, funding, DEV, config); dev_stress = evaluate(bars, funding, DEV, stress)
    val = evaluate(bars, funding, VAL, config); val_stress = evaluate(bars, funding, VAL, stress)
    val["ALL"] = metrics(backtest(bars, funding, timestamp("2024-01-01"), timestamp("2026-10-01"), config))
    val_stress["ALL"] = metrics(backtest(bars, funding, timestamp("2024-01-01"), timestamp("2026-10-01"), stress))
    positive = sum(max(0, val[name]["net_pnl"]) for name, *_ in VAL); share = max((max(0, val[name]["net_pnl"]) for name, *_ in VAL), default=0) / positive if positive else 1
    gate = {"development_positive_all_years": all(dev[name]["net_return"] > 0 for name, *_ in DEV),
            "validation_minimum_40_trades": val["ALL"]["trades"] >= 40,
            "normal_pf_at_least_1_20": (val["ALL"]["profit_factor"] or 0) >= 1.20,
            "stress_pf_at_least_1_05": (val_stress["ALL"]["profit_factor"] or 0) >= 1.05,
            "normal_positive_all_blocks": all(val[name]["net_return"] > 0 for name, *_ in VAL),
            "stress_positive_four_blocks": sum(val_stress[name]["net_return"] > 0 for name, *_ in VAL) >= 4,
            "stress_total_positive": val_stress["ALL"]["net_return"] > 0,
            "normal_max_drawdown_at_most_10pct": val["ALL"]["max_drawdown"] <= 0.10,
            "profit_not_concentrated": share <= 0.50, "forward_paper_50_trades": False}
    report = {"strategy": "SOL_BASIS_CONVERGENCE_V1", "data": "Binance SOLUSDT spot and USD-M perpetual 1h plus funding archives",
              "development_period": "2021-01-01/2023-12-31", "validation_period": "2024-01-01/2026-09-30",
              "config": config.__dict__, "stress_config": stress.__dict__, "development": dev, "development_stress": dev_stress,
              "validation": val, "validation_stress": val_stress, "largest_positive_validation_block_share": share,
              "gate": gate, "passes_historical_gate": all(v for k, v in gate.items() if k != "forward_paper_50_trades"),
              "robust_candidate": all(gate.values()), "manifest": manifest,
              "limitations": ["Hourly closes trigger exits at the following open, including adverse spread gaps.",
                              "Borrow availability, margin liquidation and order-book impact are not modeled.",
                              "Historical passage would still require 50 new forward PAPER trades."]}
    Path("research/sol_basis_convergence_results_20261024.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "manifest"}, indent=2))


if __name__ == "__main__": main()
