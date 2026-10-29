"""Direct Alternative.me/Binance validation of frozen extreme-fear rules."""
import datetime as dt
import gzip
import hashlib
import json
import pathlib
import sys
from dataclasses import replace

from research.extreme_fear_contrarian_v1 import Config, DAY, backtest, validate
from research.run_realized_value_discount import UTC, get, prices, unique, folds, metrics


def sentiment(cache):
    url = "https://api.alternative.me/fng/?limit=0&format=json"
    payload = get(url, cache / "alternative-fng-all.json")
    obj = json.loads(payload)
    if obj.get("metadata", {}).get("error") is not None:
        raise ValueError("sentiment API error")
    rows = []
    for item in obj["data"]:
        timestamp = int(item["timestamp"]) * 1000
        value = int(item["value"])
        rows.append({"timestamp": timestamp, "fear": value, "classification": item.get("value_classification")})
    rows.sort(key=lambda item: item["timestamp"])
    return rows, {"kind": "alternative_me_fear_greed", "url": url, "sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload), "rows": len(rows)}


def main():
    cache = pathlib.Path(sys.argv[1]); cache.mkdir(parents=True, exist_ok=True)
    destination = pathlib.Path(sys.argv[2]); destination.mkdir(parents=True, exist_ok=True)
    sentiment_rows, sentiment_manifest = sentiment(cache)
    price_rows, price_manifest = prices(cache)
    metric_data, metric_duplicates = unique(sentiment_rows, "sentiment")
    price_data, price_duplicates = unique(price_rows, "price")
    common = sorted(set(metric_data) & set(price_data))
    rows = [{**price_data[timestamp], **metric_data[timestamp]} for timestamp in common]
    validate(rows)
    quality = {"sentiment_rows": len(metric_data), "price_rows": len(price_data), "aligned_days": len(rows), "sentiment_duplicates": metric_duplicates, "price_duplicates": price_duplicates, "sentiment_only": len(set(metric_data) - set(price_data)), "price_only": len(set(price_data) - set(metric_data)), "sentiment_start": min(metric_data), "sentiment_end": max(metric_data), "price_start": min(price_data), "price_end": max(price_data), "gaps": [{"after": a["timestamp"], "before": b["timestamp"], "missing_days": (b["timestamp"] - a["timestamp"]) // DAY - 1} for a, b in zip(rows, rows[1:]) if b["timestamp"] - a["timestamp"] != DAY]}
    runs, ledgers = {}, {}
    for name, start, end in folds():
        for label, multiple in (("base", 1), ("stress", 2)):
            base = Config(); config = replace(base, fee=base.fee * multiple, slippage=base.slippage * multiple)
            trades, curve = backtest(rows, start, end, config)
            key = f"{name}_{label}"; ledgers[key] = trades; runs[key] = metrics(trades, curve)
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
    gates = {"sample": base_agg["trades"] >= 75, "base_net": base_agg["net_pnl"] > 0, "base_expectancy": (base_agg["expectancy"] or 0) > 0, "base_pf": (base_agg["profit_factor"] or 0) > 1.15, "stress_net": stress_agg["net_pnl"] > 0, "stress_expectancy": (stress_agg["expectancy"] or 0) > 0, "stress_pf": (stress_agg["profit_factor"] or 0) > 1.02, "four_positive_years": sum(value > 0 for value in by_year.values()) >= 4, "four_positive_stress_years": sum(value > 0 for value in stress_by_year.values()) >= 4, "final_year": by_year["2026"] > 0 and stress_by_year["2026"] > 0, "drawdown": max(runs["continuous_oos_base"]["max_drawdown_pct"], runs["continuous_oos_stress"]["max_drawdown_pct"]) <= 10, "concentration": base_agg["net_pnl"] > 0 and positive_months > 0 and max(monthly.values(), default=0) <= .25 * positive_months}
    historical_pass = all(gates.values())
    protocol = pathlib.Path("research/extreme_fear_contrarian_protocol_20261029.md")
    result = {"strategy": "XRP_EXTREME_FEAR_CONTRARIAN_V1", "status": "TEST NEDOKONCEN: independent forward PAPER evidence required" if historical_pass else "NEPROSEL", "protocol_sha256": hashlib.sha256(protocol.read_bytes()).hexdigest(), "manifest": [sentiment_manifest] + price_manifest, "data_quality": quality, "runs": runs, "aggregate_oos": base_agg, "aggregate_stress": stress_agg, "by_year": by_year, "stress_by_year": stress_by_year, "monthly_base": monthly, "gates": gates, "historical_pass": historical_pass, "limitations": ["Alternative.me methodology and past values can change; downloaded bytes are locally hashed, not publisher-signed.", "Classification text is ignored; only the integer value with a full-day lag is used, with no interpolation.", "Daily OHLC is not tick execution; historical dates are exploratory and no forward PAPER evidence exists."]}
    (destination / "results.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    with gzip.open(destination / "trades.json.gz", "wt") as handle:
        json.dump(ledgers, handle)
    print(result["status"], gates, flush=True)


if __name__ == "__main__":
    main()
