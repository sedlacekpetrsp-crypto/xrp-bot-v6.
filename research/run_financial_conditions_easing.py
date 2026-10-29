"""Direct FRED/Binance validation of frozen financial-conditions rules."""
import csv
import datetime as dt
import gzip
import hashlib
import io
import json
import pathlib
import sys
from dataclasses import replace

from research.financial_conditions_easing_v1 import Config, DAY, backtest, make_signals, validate
from research.run_real_yield_easing import get, prices, unique, folds, metrics, UTC


def macro(cache):
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=NFCI&cosd=2020-01-01&coed=2026-10-01"
    payload = get(url, cache / "fred-NFCI.csv")
    raw = list(csv.DictReader(io.StringIO(payload.decode())))
    rows, missing = [], []
    for item in raw:
        timestamp = int(dt.datetime.strptime(item["observation_date"], "%Y-%m-%d").replace(tzinfo=UTC).timestamp() * 1000)
        value = item["NFCI"].strip()
        if value in ("", "."):
            missing.append(timestamp)
        else:
            rows.append({"timestamp": timestamp, "value": float(value)})
    manifest = {"kind": "FRED_NFCI", "url": url, "sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload), "raw_rows": len(raw), "valid_rows": len(rows), "missing_value_timestamps": missing}
    return rows, manifest


def main():
    cache = pathlib.Path(sys.argv[1]); cache.mkdir(parents=True, exist_ok=True)
    destination = pathlib.Path(sys.argv[2]); destination.mkdir(parents=True, exist_ok=True)
    macro_rows, macro_manifest = macro(cache)
    price_rows, price_manifest = prices(cache)
    macro_data, macro_duplicates = unique(macro_rows, "macro")
    price_data, price_duplicates = unique(price_rows, "price")
    ordered_macro = [macro_data[timestamp] for timestamp in sorted(macro_data)]
    signals = make_signals(ordered_macro)
    rows = []
    for timestamp in sorted(price_data):
        row = dict(price_data[timestamp])
        signal = signals.get(timestamp)
        if signal:
            row.update(macro_signal=True, **signal)
        else:
            row["macro_signal"] = False
        rows.append(row)
    validate(rows)
    quality = {"macro_rows": len(macro_data), "price_rows": len(price_data), "macro_duplicates": macro_duplicates, "price_duplicates": price_duplicates, "eligible_signal_dates": len(signals), "signal_dates_without_price": len(set(signals) - set(price_data)), "macro_start": min(macro_data), "macro_end": max(macro_data), "price_start": min(price_data), "price_end": max(price_data), "price_gaps": [{"after": a["timestamp"], "before": b["timestamp"], "missing_days": (b["timestamp"] - a["timestamp"]) // DAY - 1} for a, b in zip(rows, rows[1:]) if b["timestamp"] - a["timestamp"] != DAY]}
    runs, ledgers = {}, {}
    for name, start, end in folds():
        for label, multiple in (("base", 1), ("stress", 2)):
            base = Config()
            config = replace(base, fee=base.fee * multiple, slippage=base.slippage * multiple)
            trades, curve = backtest(rows, start, end, config)
            key = f"{name}_{label}"
            ledgers[key] = trades
            runs[key] = metrics(trades, curve)
            print(key, runs[key], flush=True)
    years = ["2022", "2023", "2024", "2025", "2026"]
    base_trades = [item for year in years for item in ledgers[f"{year}_base"]]
    stress_trades = [item for year in years for item in ledgers[f"{year}_stress"]]
    base_agg = metrics(base_trades, [{"equity": 10_000}, {"equity": 10_000 + sum(item["pnl"] for item in base_trades)}])
    stress_agg = metrics(stress_trades, [{"equity": 10_000}, {"equity": 10_000 + sum(item["pnl"] for item in stress_trades)}])
    by_year = {year: runs[f"{year}_base"]["net_pnl"] for year in years}
    stress_by_year = {year: runs[f"{year}_stress"]["net_pnl"] for year in years}
    monthly = {}
    for item in base_trades:
        key = dt.datetime.fromtimestamp(item["exit_timestamp"] / 1000, UTC).strftime("%Y-%m")
        monthly[key] = monthly.get(key, 0) + item["pnl"]
    positive_months = sum(max(0, value) for value in monthly.values())
    gates = {"sample": base_agg["trades"] >= 50, "base_net": base_agg["net_pnl"] > 0, "base_expectancy": (base_agg["expectancy"] or 0) > 0, "base_pf": (base_agg["profit_factor"] or 0) > 1.15, "stress_net": stress_agg["net_pnl"] > 0, "stress_expectancy": (stress_agg["expectancy"] or 0) > 0, "stress_pf": (stress_agg["profit_factor"] or 0) > 1.02, "four_positive_years": sum(value > 0 for value in by_year.values()) >= 4, "four_positive_stress_years": sum(value > 0 for value in stress_by_year.values()) >= 4, "final_year": by_year["2026"] > 0 and stress_by_year["2026"] > 0, "drawdown": max(runs["continuous_oos_base"]["max_drawdown_pct"], runs["continuous_oos_stress"]["max_drawdown_pct"]) <= 10, "concentration": base_agg["net_pnl"] > 0 and positive_months > 0 and max(monthly.values(), default=0) <= .25 * positive_months}
    historical_pass = all(gates.values())
    protocol = pathlib.Path("research/financial_conditions_easing_protocol_20261029.md")
    result = {"strategy": "XRP_FINANCIAL_CONDITIONS_EASING_V1", "status": "TEST NEDOKONCEN: independent forward PAPER evidence required" if historical_pass else "NEPROSEL", "protocol_sha256": hashlib.sha256(protocol.read_bytes()).hexdigest(), "manifest": [macro_manifest] + price_manifest, "data_quality": quality, "runs": runs, "aggregate_oos": base_agg, "aggregate_stress": stress_agg, "by_year": by_year, "stress_by_year": stress_by_year, "monthly_base": monthly, "gates": gates, "historical_pass": historical_pass, "limitations": ["FRED NFCI can be revised; downloaded bytes are locally hashed, not publisher-signed.", "Missing NFCI values are not filled and availability is delayed to the second subsequent valid weekly observation.", "Daily OHLC is not tick execution; historical dates are exploratory and no forward PAPER evidence exists."]}
    (destination / "results.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    with gzip.open(destination / "trades.json.gz", "wt") as handle:
        json.dump(ledgers, handle)
    print(result["status"], gates, flush=True)


if __name__ == "__main__":
    main()
