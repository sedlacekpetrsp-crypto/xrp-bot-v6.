import datetime as dt
import gzip
import hashlib
import json
import pathlib
import sys
import urllib.parse
import urllib.request
from dataclasses import replace

from research.btc_mempool_clearance_xrp_v1 import Config, DAY, aggregate_daily, backtest, make_signals, validate

UTC = dt.timezone.utc
MEMPOOL = "https://api.blockchain.info/charts/mempool-size?start=2019-01-01&timespan=2830days&format=json&sampled=false"
BINANCE = "https://data-api.binance.vision/api/v3/klines"


def stamp(y, m=1, d=1):
    return int(dt.datetime(y, m, d, tzinfo=UTC).timestamp() * 1000)


def get(url, path):
    if not path.exists():
        req = urllib.request.Request(url, headers={"User-Agent": "xrp-research/1.0"})
        with urllib.request.urlopen(req, timeout=180) as response:
            path.write_bytes(response.read())
    return path.read_bytes()


def load_metric(cache):
    path = cache / "blockchain-info-btc-mempool-size-2019-2026.json"
    raw = get(MEMPOOL, path)
    doc = json.loads(raw)
    cutoff = stamp(2026, 10)
    points = [
        dict(timestamp=int(x["x"]) * 1000, mempool_bytes=float(x["y"]))
        for x in doc["values"]
        if stamp(2019) <= int(x["x"]) * 1000 < cutoff
    ]
    daily = aggregate_daily(points, Config().min_intraday_points)
    manifest = dict(
        kind="blockchain_info_BTC_mempool_size",
        url=MEMPOOL,
        cache_file=path.name,
        sha256=hashlib.sha256(raw).hexdigest(),
        bytes=len(raw),
        raw_rows=len(doc["values"]),
        used_rows=len(points),
        daily_rows=len(daily),
    )
    return points, daily, manifest


def load_prices(cache):
    start = stamp(2020)
    end = stamp(2026, 10) - 1
    cursor = start
    page = 0
    rows = []
    manifest = []
    while cursor <= end:
        query = urllib.parse.urlencode(dict(symbol="XRPUSDT", interval="1d", startTime=cursor, endTime=end, limit=1000))
        url = BINANCE + "?" + query
        path = cache / f"XRPUSDT-1d-mempool-api-{page}.json"
        raw = get(url, path)
        doc = json.loads(raw)
        manifest.append(dict(kind="binance_XRPUSDT_1d", url=url, cache_file=path.name, sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw), rows=len(doc)))
        if not doc:
            break
        rows += [dict(timestamp=int(x[0]), open=float(x[1]), high=float(x[2]), low=float(x[3]), close=float(x[4])) for x in doc]
        cursor = int(doc[-1][0]) + DAY
        page += 1
        if len(doc) < 1000:
            break
    return rows, manifest


def metrics(trades, curve, initial=10_000.0):
    wins = sum(max(0, x["pnl"]) for x in trades)
    losses = -sum(min(0, x["pnl"]) for x in trades)
    net = sum(x["pnl"] for x in trades)
    peak = initial
    drawdown = 0.0
    for point in curve:
        peak = max(peak, point["equity"])
        drawdown = max(drawdown, (peak - point["equity"]) / peak * 100)
    return dict(
        trades=len(trades), net_pnl=net, net_return_pct=net / initial * 100,
        profit_factor=wins / losses if losses else None,
        expectancy=net / len(trades) if trades else None,
        max_drawdown_pct=drawdown,
        fees=sum(x["fees"] for x in trades),
        slippage_cost=sum(x["slippage_cost"] for x in trades),
        gross_profit=wins, gross_loss=losses,
    )


def main():
    cache = pathlib.Path(sys.argv[1])
    dest = pathlib.Path(sys.argv[2])
    cache.mkdir(parents=True, exist_ok=True)
    dest.mkdir(parents=True, exist_ok=True)
    points, daily, metric_manifest = load_metric(cache)
    prices, price_manifest = load_prices(cache)
    validate(prices)
    signals = make_signals(daily)
    for row in prices:
        if row["timestamp"] in signals:
            row["mempool_signal"] = signals[row["timestamp"]]

    folds = [("2020_2021_control", stamp(2020), stamp(2022))]
    folds += [(str(y), stamp(y), stamp(y + 1) if y < 2026 else stamp(2026, 10)) for y in range(2022, 2027)]
    folds += [("continuous_oos", stamp(2022), stamp(2026, 10))]
    runs = {}
    ledgers = {}
    for name, start, end in folds:
        for label, multiplier in (("base", 1), ("stress", 2)):
            c = replace(Config(), fee=Config().fee * multiplier, slippage=Config().slippage * multiplier)
            trades, curve = backtest(prices, start, end, c)
            key = name + "_" + label
            ledgers[key] = trades
            runs[key] = metrics(trades, curve)
            print(key, runs[key], flush=True)

    years = [str(y) for y in range(2022, 2027)]
    base = [x for y in years for x in ledgers[y + "_base"]]
    stress = [x for y in years for x in ledgers[y + "_stress"]]
    aggregate = metrics(base, [])
    aggregate_stress = metrics(stress, [])
    aggregate["max_drawdown_pct"] = None
    aggregate_stress["max_drawdown_pct"] = None
    by_year = {y: runs[y + "_base"]["net_pnl"] for y in years}
    stress_by_year = {y: runs[y + "_stress"]["net_pnl"] for y in years}
    monthly = {}
    for trade in base:
        key = dt.datetime.fromtimestamp(trade["exit_timestamp"] / 1000, UTC).strftime("%Y-%m")
        monthly[key] = monthly.get(key, 0.0) + trade["pnl"]
    positive = sum(max(0, x) for x in monthly.values())
    concentration = max((max(0, x) / positive for x in monthly.values()), default=1.0)
    gates = dict(
        sample=aggregate["trades"] >= 75,
        base_net=aggregate["net_pnl"] > 0,
        base_expectancy=(aggregate["expectancy"] or 0) > 0,
        base_pf=(aggregate["profit_factor"] or 0) > 1.20,
        stress_net=aggregate_stress["net_pnl"] > 0,
        stress_expectancy=(aggregate_stress["expectancy"] or 0) > 0,
        stress_pf=(aggregate_stress["profit_factor"] or 0) > 1.05,
        four_years=sum(x > 0 for x in by_year.values()) >= 4,
        four_years_stress=sum(x > 0 for x in stress_by_year.values()) >= 4,
        final_year=by_year["2026"] > 0 and stress_by_year["2026"] > 0,
        drawdown=max(runs["continuous_oos_base"]["max_drawdown_pct"], runs["continuous_oos_stress"]["max_drawdown_pct"]) <= 10,
        concentration=aggregate["net_pnl"] > 0 and positive > 0 and concentration <= .25,
        audit=False,
        forward_paper=False,
    )
    historical_pass = all(value for key, value in gates.items() if key not in ("audit", "forward_paper"))
    protocol = pathlib.Path("research/btc_mempool_clearance_xrp_protocol_20261104.md")
    signal_by_year = {str(y): sum(dt.datetime.fromtimestamp(t / 1000, UTC).year == y for t in signals) for y in range(2020, 2027)}
    samples = [x["samples"] for x in daily]
    result = dict(
        strategy="BTC_MEMPOOL_CLEARANCE_XRP_V1",
        status="TEST NEDOKONCEN: audit and forward PAPER required" if historical_pass else "NEPROSEL",
        protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),
        manifest=[metric_manifest] + price_manifest,
        data_quality=dict(
            intraday_rows=len(points), intraday_start=points[0]["timestamp"], intraday_end=points[-1]["timestamp"],
            daily_rows=len(daily), daily_start=daily[0]["timestamp"], daily_end=daily[-1]["timestamp"],
            daily_min_samples=min(samples), daily_max_samples=max(samples), daily_gaps=[],
            price_rows=len(prices), price_start=prices[0]["timestamp"], price_end=prices[-1]["timestamp"], price_gaps=[],
        ),
        signals_total=len(signals), signals_by_entry_year=signal_by_year,
        runs=runs, aggregate_oos=aggregate, aggregate_stress=aggregate_stress,
        by_year=by_year, stress_by_year=stress_by_year, monthly_base=monthly,
        positive_month_profit_concentration=concentration,
        gates=gates, historical_pass_before_audit=historical_pass,
        limitations=[
            "Blockchain.com mempool observations are third-party chart data and may be revised.",
            "Low backlog can reflect weak demand rather than healthy settlement capacity.",
            "Daily XRP OHLC cannot reconstruct tick paths; fixed conservative gap/stop rules apply.",
            "Local SHA256 values are not publisher signatures.",
            "No independent forward PAPER evidence exists.",
        ],
    )
    (dest / "results.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    with gzip.open(dest / "daily_metric.json.gz", "wt") as handle:
        json.dump(daily, handle)
    with gzip.open(dest / "trades.json.gz", "wt") as handle:
        json.dump(ledgers, handle)
    print(result["status"], gates, signal_by_year, flush=True)


if __name__ == "__main__":
    main()
