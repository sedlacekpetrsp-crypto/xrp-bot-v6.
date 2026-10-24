"""Historical runner for BTC_QUARTERLY_CARRY_V1."""
import csv, hashlib, io, json, urllib.request, zipfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from research.btc_quarterly_carry_v1 import Config, HOUR_MS, backtest_contract, with_cost_stress

EXPIRIES = ["2021-03-26","2021-06-25","2021-09-24","2021-12-31",
            "2022-03-25","2022-06-24","2022-09-30","2022-12-30",
            "2023-03-31","2023-06-30","2023-09-29","2023-12-29",
            "2024-03-29","2024-06-28","2024-09-27","2024-12-27",
            "2025-03-28","2025-06-27","2025-09-26","2025-12-26",
            "2026-03-27","2026-06-26","2026-09-25"]
DEV = (("2021", "2021-01-01", "2022-01-01"), ("2022", "2022-01-01", "2023-01-01"), ("2023", "2023-01-01", "2024-01-01"))
VAL = (("2024_H1", "2024-01-01", "2024-07-01"), ("2024_H2", "2024-07-01", "2025-01-01"),
       ("2025_H1", "2025-01-01", "2025-07-01"), ("2025_H2", "2025-07-01", "2026-01-01"),
       ("2026_JAN_SEP", "2026-01-01", "2026-10-01"))


def timestamp(value): return int(datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp() * 1000)
def expiry_timestamp(value): return timestamp(value) + 8 * HOUR_MS


def contract_symbol(value): return "BTCUSDT_" + value[2:].replace("-", "")


def contract_months(value):
    dt = datetime.fromisoformat(value); previous_month = 12 if dt.month == 1 else dt.month - 1; previous_year = dt.year - 1 if dt.month == 1 else dt.year
    return [(previous_year, previous_month), (dt.year, dt.month)]


def download(kind, expiry, month):
    symbol = "BTCUSDT" if kind == "spot" else contract_symbol(expiry); y, m = month
    prefix = "spot" if kind == "spot" else "futures/um"
    url = f"https://data.binance.vision/data/{prefix}/monthly/klines/{symbol}/1h/{symbol}-1h-{y}-{m:02d}.zip"
    request = urllib.request.Request(url, headers={"User-Agent": "btc-quarterly-carry/1.0"})
    with urllib.request.urlopen(request, timeout=90) as response: payload = response.read()
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = [name for name in archive.namelist() if name.endswith(".csv")]
        if len(names) != 1: raise ValueError(url)
        rows = list(csv.reader(io.TextIOWrapper(archive.open(names[0]), encoding="utf-8")))
    data = {}
    for row in rows:
        if row and row[0].isdigit():
            stamp = int(row[0]); stamp = stamp // 1000 if stamp > 10**14 else stamp
            data[stamp] = (float(row[1]), float(row[4]))
    return data, {"kind": kind, "contract": contract_symbol(expiry), "url": url,
                  "sha256": hashlib.sha256(payload).hexdigest(), "rows": len(data)}


def fetch(expiry):
    spot = {}; future = {}; manifest = []
    for month in contract_months(expiry):
        s, sm = download("spot", expiry, month); f, fm = download("future", expiry, month)
        spot.update(s); future.update(f); manifest.extend([sm, fm])
    common = sorted(set(spot) & set(future)); bars = [{"timestamp": ts, "spot_open": spot[ts][0], "spot_close": spot[ts][1],
                                                       "future_open": future[ts][0], "future_close": future[ts][1]} for ts in common]
    start = expiry_timestamp(expiry) - 28 * 86_400_000; end = expiry_timestamp(expiry)
    expected = set(range(start, end + HOUR_MS, HOUR_MS)); missing = sorted(expected - set(common))
    return {"expiry": expiry, "expiry_ts": end, "bars": bars,
            "coverage": {"expected_window_hours": len(expected), "missing_synchronized_hours": len(missing),
                         "first_missing_timestamp": missing[0] if missing else None, "expiry_open_present": end in common},
            "manifest": manifest}


def evaluate(contracts, blocks, config):
    answer = {}
    for name, start, end in blocks:
        equity = config.initial_equity; peak = equity; drawdown = 0.0; trades = []
        for contract in contracts:
            stamp = expiry_timestamp(contract["expiry"])
            if not (timestamp(start) <= stamp < timestamp(end)): continue
            result = backtest_contract(contract["bars"], contract["expiry_ts"], replace(config, initial_equity=equity))
            equity = result["ending_equity"]; peak = max(peak, equity); drawdown = max(drawdown, result["max_drawdown"], (peak - equity) / peak)
            if result["trade"]: trades.append({**result["trade"], "contract": contract_symbol(contract["expiry"])})
        profit = sum(max(0, t["net_pnl"]) for t in trades); loss = -sum(min(0, t["net_pnl"]) for t in trades)
        answer[name] = {"trades": len(trades), "net_return": equity / config.initial_equity - 1,
                        "net_pnl": equity - config.initial_equity, "profit_factor": profit / loss if loss else None,
                        "max_drawdown": drawdown, "fees": sum(t["fees"] for t in trades), "contracts": [t["contract"] for t in trades]}
    return answer


def main():
    with ThreadPoolExecutor(max_workers=8) as pool: contracts = list(pool.map(fetch, EXPIRIES))
    config = Config(); stress = with_cost_stress(config)
    dev = evaluate(contracts, DEV, config); dev_stress = evaluate(contracts, DEV, stress)
    val = evaluate(contracts, VAL, config); val_stress = evaluate(contracts, VAL, stress)
    val["ALL"] = evaluate(contracts, (("ALL", "2024-01-01", "2026-10-01"),), config)["ALL"]
    val_stress["ALL"] = evaluate(contracts, (("ALL", "2024-01-01", "2026-10-01"),), stress)["ALL"]
    positive = sum(max(0, val[name]["net_pnl"]) for name, *_ in VAL); share = max((max(0, val[name]["net_pnl"]) for name, *_ in VAL), default=0) / positive if positive else 1
    normal_pf_ok = val["ALL"]["trades"] > 0 and (val["ALL"]["profit_factor"] is None or val["ALL"]["profit_factor"] >= 1.20)
    stress_pf_ok = val_stress["ALL"]["trades"] > 0 and (val_stress["ALL"]["profit_factor"] is None or val_stress["ALL"]["profit_factor"] >= 1.05)
    gate = {"development_positive_all_years": all(dev[name]["net_return"] > 0 for name, *_ in DEV),
            "validation_minimum_8_expiries": val["ALL"]["trades"] >= 8, "normal_pf_at_least_1_20": normal_pf_ok,
            "stress_pf_at_least_1_05": stress_pf_ok, "normal_positive_all_blocks": all(val[name]["net_return"] > 0 for name, *_ in VAL),
            "stress_positive_four_blocks": sum(val_stress[name]["net_return"] > 0 for name, *_ in VAL) >= 4,
            "stress_total_positive": val_stress["ALL"]["net_return"] > 0,
            "normal_max_drawdown_at_most_5pct": val["ALL"]["max_drawdown"] <= 0.05,
            "profit_not_concentrated": share <= 0.45, "forward_paper_4_expiries": False}
    report = {"strategy": "BTC_QUARTERLY_CARRY_V1", "data": "Binance BTCUSDT spot and dated USD-M quarterly futures 1h archives",
              "development_period": "2021-01-01/2023-12-31", "validation_period": "2024-01-01/2026-09-30",
              "config": config.__dict__, "stress_config": stress.__dict__, "development": dev, "development_stress": dev_stress,
              "validation": val, "validation_stress": val_stress, "largest_positive_validation_block_share": share,
              "gate": gate, "passes_historical_gate": all(v for k, v in gate.items() if k != "forward_paper_4_expiries"),
              "robust_candidate": all(gate.values()), "coverage": [{"contract": contract_symbol(c["expiry"]), **c["coverage"]} for c in contracts],
              "manifest": [entry for contract in contracts for entry in contract["manifest"]],
              "limitations": ["Settlement is represented by the synchronized expiry-hour open, not an exchange settlement statement.",
                              "Margin liquidation and order-book impact are not modeled.",
                              "Historical passage would still require four new quarterly forward PAPER expiries."]}
    Path("research/btc_quarterly_carry_results_20261024.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "manifest"}, indent=2))


if __name__ == "__main__": main()
