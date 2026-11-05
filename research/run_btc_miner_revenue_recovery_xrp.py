"""Frozen Blockchain.com miner-revenue/Binance XRP validation."""
import datetime as dt
import gzip
import hashlib
import json
import pathlib
import sys
import urllib.request

from research.run_xrp_bank_credit_expansion import load_prices, metrics, stamp, unique
from research.btc_miner_revenue_recovery_xrp_v1 import DAY, backtest, execution_config, make_signals, validate_prices

UTC = dt.timezone.utc


def get(url, path):
    if not path.exists():
        request = urllib.request.Request(url, headers={"User-Agent": "xrp-paper-research/1.0"})
        with urllib.request.urlopen(request, timeout=120) as response:
            path.write_bytes(response.read())
    return path.read_bytes()


def load_miner_revenue(cache):
    url = "https://api.blockchain.info/charts/miners-revenue?timespan=all&format=json"
    payload = get(url, cache / "blockchain-miners-revenue.json")
    document = json.loads(payload)
    raw = document["values"]
    rows = [{"timestamp": int(row["x"]) * 1000, "value": float(row["y"])} for row in raw]
    return rows, {"kind": "BLOCKCHAIN_COM_MINERS_REVENUE", "url": url, "sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload), "raw_rows": len(raw), "valid_rows": len(rows), "unit": document.get("unit"), "period": document.get("period")}


def main():
    cache = pathlib.Path(sys.argv[1]); cache.mkdir(parents=True, exist_ok=True)
    dest = pathlib.Path(sys.argv[2]); dest.mkdir(parents=True, exist_ok=True)
    source_rows, source_manifest = load_miner_revenue(cache)
    price_rows, price_manifest = load_prices(cache)
    observations, source_duplicates = unique(source_rows, "miner revenue")
    prices, price_duplicates = unique(price_rows, "price")
    validate_prices(prices); signals = make_signals(observations); rows = []
    for price in prices:
        row = dict(price); source = signals.get(price["timestamp"])
        row.update(macro_signal=bool(source)); row.update(source or {}); rows.append(row)
    source_gaps = [{"after": a["timestamp"], "before": b["timestamp"], "delta_days": (b["timestamp"] - a["timestamp"]) / DAY} for a, b in zip(observations, observations[1:]) if b["timestamp"] - a["timestamp"] != DAY]
    price_gaps = [{"after": a["timestamp"], "before": b["timestamp"], "missing_days": (b["timestamp"] - a["timestamp"]) // DAY - 1} for a, b in zip(prices, prices[1:]) if b["timestamp"] - a["timestamp"] != DAY]
    quality = {"source_rows": len(observations), "source_duplicates": source_duplicates, "source_start": observations[0]["timestamp"], "source_end": observations[-1]["timestamp"], "source_gaps": source_gaps, "price_rows": len(prices), "price_duplicates": price_duplicates, "price_start": prices[0]["timestamp"], "price_end": prices[-1]["timestamp"], "price_gaps": price_gaps, "eligible_signal_dates": len(signals), "signal_dates_without_price": len(set(signals) - {row["timestamp"] for row in prices})}
    folds = [("2020_2021_control", stamp(2020), stamp(2022))] + [(str(year), stamp(year), stamp(year + 1) if year < 2026 else stamp(2026, 10, 1)) for year in range(2022, 2027)] + [("continuous_oos", stamp(2022), stamp(2026, 10, 1))]
    runs = {}; ledgers = {}
    for name, start, end in folds:
        for label, multiple in (("base", 1), ("stress", 2)):
            trades, curve = backtest(rows, start, end, execution_config(multiple))
            key = f"{name}_{label}"; ledgers[key] = trades; runs[key] = metrics(trades, curve)
            print(key, runs[key], flush=True)
    years = [str(year) for year in range(2022, 2027)]
    base_trades = [trade for year in years for trade in ledgers[year + "_base"]]
    stress_trades = [trade for year in years for trade in ledgers[year + "_stress"]]
    def aggregate(trades):
        return metrics(trades, [{"equity": 10000.0}, {"equity": 10000.0 + sum(trade["pnl"] for trade in trades)}])
    base_aggregate = aggregate(base_trades); stress_aggregate = aggregate(stress_trades)
    base_aggregate["max_drawdown_pct"] = None; stress_aggregate["max_drawdown_pct"] = None
    by_year = {year: runs[year + "_base"]["net_pnl"] for year in years}
    stress_by_year = {year: runs[year + "_stress"]["net_pnl"] for year in years}
    monthly = {}
    for trade in base_trades:
        month = dt.datetime.fromtimestamp(trade["exit_timestamp"] / 1000, UTC).strftime("%Y-%m")
        monthly[month] = monthly.get(month, 0) + trade["pnl"]
    positive = sum(max(0, value) for value in monthly.values())
    gates = {"sample": base_aggregate["trades"] >= 75, "base_net": base_aggregate["net_pnl"] > 0, "base_expectancy": (base_aggregate["expectancy"] or 0) > 0, "base_pf": (base_aggregate["profit_factor"] or 0) > 1.15, "stress_net": stress_aggregate["net_pnl"] > 0, "stress_expectancy": (stress_aggregate["expectancy"] or 0) > 0, "stress_pf": (stress_aggregate["profit_factor"] or 0) > 1.02, "four_positive_years": sum(value > 0 for value in by_year.values()) >= 4, "four_positive_stress_years": sum(value > 0 for value in stress_by_year.values()) >= 4, "final_year": by_year["2026"] > 0 and stress_by_year["2026"] > 0, "drawdown": max(runs["continuous_oos_base"]["max_drawdown_pct"], runs["continuous_oos_stress"]["max_drawdown_pct"]) <= 10, "concentration": base_aggregate["net_pnl"] > 0 and positive > 0 and max(monthly.values(), default=0) <= 0.25 * positive, "audit": False, "forward_paper": False}
    historical = all(value for key, value in gates.items() if key not in ("audit", "forward_paper"))
    protocol = pathlib.Path("research/btc_miner_revenue_recovery_xrp_protocol_20261105.md")
    result = {"strategy": "BTC_MINER_REVENUE_RECOVERY_XRP_V1", "status": "TEST NEDOKONCEN: audit and forward PAPER required" if historical else "NEPROSEL", "protocol_sha256": hashlib.sha256(protocol.read_bytes()).hexdigest(), "manifest": [source_manifest] + price_manifest, "data_quality": quality, "runs": runs, "aggregate_oos": base_aggregate, "aggregate_stress": stress_aggregate, "by_year": by_year, "stress_by_year": stress_by_year, "monthly_base": monthly, "gates": gates, "historical_pass_before_audit": historical, "limitations": ["Blockchain.com may revise chart history; the retained hash identifies this response, not an original vintage.", "The two-observation lag is conservative but cannot reconstruct historical publication snapshots.", "Miner revenue in USD is partly affected by BTC price and fees and is not a pure miner-balance-sheet measure.", "Daily OHLC uses conservative stop-first ambiguity; no independent forward PAPER evidence exists."]}
    (dest / "results.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    with gzip.open(dest / "trades.json.gz", "wt") as handle: json.dump(ledgers, handle)
    print(result["status"], gates, flush=True)


if __name__ == "__main__":
    main()
