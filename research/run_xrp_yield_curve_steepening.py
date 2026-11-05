"""Frozen direct FRED/Binance validation for yield-curve steepening."""
import csv, datetime as dt, gzip, hashlib, io, json, pathlib, sys, urllib.parse, urllib.request
from dataclasses import replace

from research.xrp_yield_curve_steepening_v1 import Config, DAY, backtest, make_signals, validate_prices

UTC = dt.timezone.utc


def get(url, path):
    if not path.exists():
        request = urllib.request.Request(url, headers={"User-Agent": "xrp-paper-research/1.0"})
        with urllib.request.urlopen(request, timeout=120) as response:
            path.write_bytes(response.read())
    return path.read_bytes()


def stamp(year, month=1, day=1):
    return int(dt.datetime(year, month, day, tzinfo=UTC).timestamp() * 1000)


def load_macro(cache):
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=T10Y2Y&cosd=2020-01-01&coed=2026-10-01"
    payload = get(url, cache / "fred-T10Y2Y.csv")
    raw = list(csv.DictReader(io.StringIO(payload.decode())))
    rows, missing = [], []
    for item in raw:
        timestamp = int(dt.datetime.strptime(item["observation_date"], "%Y-%m-%d").replace(tzinfo=UTC).timestamp() * 1000)
        value = item["T10Y2Y"].strip()
        if value in ("", "."):
            missing.append(timestamp)
            continue
        rows.append(dict(timestamp=timestamp, value=float(value)))
    manifest = dict(kind="FRED_T10Y2Y", url=url, sha256=hashlib.sha256(payload).hexdigest(), bytes=len(payload), raw_rows=len(raw), valid_rows=len(rows), missing_value_timestamps=missing)
    return rows, manifest


def load_prices(cache):
    base = "https://data-api.binance.vision/api/v3/klines"
    start, end, page, rows, manifest = stamp(2020), stamp(2026, 10, 1) - 1, 0, [], []
    while start <= end:
        query = urllib.parse.urlencode(dict(symbol="XRPUSDT", interval="1d", startTime=start, endTime=end, limit=1000))
        url = base + "?" + query
        path = cache / f"XRPUSDT-1d-curve-api-{page}.json"
        payload = get(url, path)
        data = json.loads(payload)
        if not isinstance(data, list) or not data:
            raise ValueError("empty Binance page")
        parsed = [dict(timestamp=int(x[0]), open=float(x[1]), high=float(x[2]), low=float(x[3]), close=float(x[4])) for x in data]
        rows.extend(parsed)
        manifest.append(dict(kind="binance_XRPUSDT_1d", url=url, sha256=hashlib.sha256(payload).hexdigest(), bytes=len(payload), rows=len(parsed), first_timestamp=parsed[0]["timestamp"], last_timestamp=parsed[-1]["timestamp"]))
        new_start = parsed[-1]["timestamp"] + DAY
        if new_start <= start:
            raise ValueError("non-advancing Binance page")
        start, page = new_start, page + 1
    return rows, manifest


def unique(rows, name):
    data, duplicates = {}, 0
    for row in rows:
        timestamp = row["timestamp"]
        if timestamp in data:
            if data[timestamp] != row:
                raise ValueError("conflicting duplicate " + name)
            duplicates += 1
        data[timestamp] = row
    return [data[t] for t in sorted(data)], duplicates


def metrics(trades, curve, initial=10_000.0):
    gain = sum(max(0.0, x["pnl"]) for x in trades); loss = -sum(min(0.0, x["pnl"]) for x in trades); net = sum(x["pnl"] for x in trades)
    peak, drawdown = initial, 0.0
    for point in curve:
        peak = max(peak, point["equity"]); drawdown = max(drawdown, (peak - point["equity"]) / peak * 100)
    return dict(trades=len(trades), net_pnl=net, net_return_pct=net / initial * 100, profit_factor=gain / loss if loss else None, expectancy=net / len(trades) if trades else None, max_drawdown_pct=drawdown, fees=sum(x["fees"] for x in trades), slippage_cost=sum(x["slippage_cost"] for x in trades))


def main():
    cache = pathlib.Path(sys.argv[1]); cache.mkdir(parents=True, exist_ok=True)
    dest = pathlib.Path(sys.argv[2]); dest.mkdir(parents=True, exist_ok=True)
    macro_raw, macro_manifest = load_macro(cache); price_raw, price_manifest = load_prices(cache)
    macro, macro_duplicates = unique(macro_raw, "macro"); prices, price_duplicates = unique(price_raw, "price")
    validate_prices(prices); signals = make_signals(macro)
    rows = []
    for item in prices:
        row = dict(item); signal = signals.get(item["timestamp"])
        if signal: row.update(macro_signal=True, **signal)
        else: row["macro_signal"] = False
        rows.append(row)
    price_gaps = [dict(after=a["timestamp"], before=b["timestamp"], missing_days=(b["timestamp"] - a["timestamp"]) // DAY - 1) for a, b in zip(prices, prices[1:]) if b["timestamp"] - a["timestamp"] != DAY]
    quality = dict(macro_rows=len(macro), macro_duplicates=macro_duplicates, macro_start=macro[0]["timestamp"], macro_end=macro[-1]["timestamp"], price_rows=len(prices), price_duplicates=price_duplicates, price_start=prices[0]["timestamp"], price_end=prices[-1]["timestamp"], price_gaps=price_gaps, eligible_signal_dates=len(signals), signal_dates_without_price=len(set(signals) - {x["timestamp"] for x in prices}))
    folds = [("2020_2021_control", stamp(2020), stamp(2022))] + [(str(y), stamp(y), stamp(y + 1) if y < 2026 else stamp(2026, 10, 1)) for y in range(2022, 2027)] + [("continuous_oos", stamp(2022), stamp(2026, 10, 1))]
    runs, ledgers = {}, {}
    for name, start, end in folds:
        for label, multiple in (("base", 1), ("stress", 2)):
            base = Config(); config = replace(base, fee=base.fee * multiple, slippage=base.slippage * multiple)
            trades, curve = backtest(rows, start, end, config)
            key = f"{name}_{label}"; ledgers[key], runs[key] = trades, metrics(trades, curve)
            print(key, runs[key], flush=True)
    years = [str(y) for y in range(2022, 2027)]
    base_trades = [x for y in years for x in ledgers[y + "_base"]]; stress_trades = [x for y in years for x in ledgers[y + "_stress"]]
    aggregate = metrics(base_trades, [{"equity": 10_000.0}, {"equity": 10_000.0 + sum(x["pnl"] for x in base_trades)}])
    aggregate_stress = metrics(stress_trades, [{"equity": 10_000.0}, {"equity": 10_000.0 + sum(x["pnl"] for x in stress_trades)}])
    aggregate["max_drawdown_pct"] = None; aggregate_stress["max_drawdown_pct"] = None
    by_year = {y: runs[y + "_base"]["net_pnl"] for y in years}; stress_by_year = {y: runs[y + "_stress"]["net_pnl"] for y in years}
    monthly = {}
    for trade in base_trades:
        month = dt.datetime.fromtimestamp(trade["exit_timestamp"] / 1000, UTC).strftime("%Y-%m"); monthly[month] = monthly.get(month, 0.0) + trade["pnl"]
    positive = sum(max(0.0, value) for value in monthly.values())
    gates = dict(sample=aggregate["trades"] >= 75, base_net=aggregate["net_pnl"] > 0, base_expectancy=(aggregate["expectancy"] or 0) > 0, base_pf=(aggregate["profit_factor"] or 0) > 1.15, stress_net=aggregate_stress["net_pnl"] > 0, stress_expectancy=(aggregate_stress["expectancy"] or 0) > 0, stress_pf=(aggregate_stress["profit_factor"] or 0) > 1.02, four_positive_years=sum(v > 0 for v in by_year.values()) >= 4, four_positive_stress_years=sum(v > 0 for v in stress_by_year.values()) >= 4, final_year=by_year["2026"] > 0 and stress_by_year["2026"] > 0, drawdown=max(runs["continuous_oos_base"]["max_drawdown_pct"], runs["continuous_oos_stress"]["max_drawdown_pct"]) <= 10, concentration=aggregate["net_pnl"] > 0 and positive > 0 and max(monthly.values(), default=0) <= .25 * positive, audit=False, forward_paper=False)
    historical_before_audit = all(value for key, value in gates.items() if key not in ("audit", "forward_paper"))
    protocol = pathlib.Path("research/xrp_yield_curve_steepening_protocol_20261105.md")
    result = dict(strategy="XRP_YIELD_CURVE_STEEPENING_V1", status="TEST NEDOKONCEN: audit and forward PAPER required" if historical_before_audit else "NEPROSEL", protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(), manifest=[macro_manifest] + price_manifest, data_quality=quality, runs=runs, aggregate_oos=aggregate, aggregate_stress=aggregate_stress, by_year=by_year, stress_by_year=stress_by_year, monthly_base=monthly, gates=gates, historical_pass_before_audit=historical_before_audit, limitations=["FRED can revise history; retained SHA256 identifies the evaluated response, not an original vintage.", "Curve steepening can reflect inflation or term premium rather than improving risk appetite.", "Business-day observations are not filled; the two-observation lag is conservative.", "Daily OHLC cannot reconstruct tick ordering; conservative stop-first and gap rules apply.", "No independent forward PAPER evidence exists."])
    (dest / "results.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    with gzip.open(dest / "trades.json.gz", "wt") as handle: json.dump(ledgers, handle)
    print(result["status"], gates, flush=True)


if __name__ == "__main__": main()

