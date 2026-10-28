"""Direct CoinMetrics/Binance validation of holder-growth divergence."""
import csv, datetime as dt, gzip, hashlib, io, json, pathlib, sys, urllib.parse, urllib.request, zipfile
from dataclasses import replace
from research.holder_growth_divergence_v1 import Config, DAY, backtest, validate

MONTHS = [(y, m) for y in range(2020, 2027) for m in range(1, 13) if (y, m) < (2026, 10)]
UTC = dt.timezone.utc


def get(url, path):
    if not path.exists():
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "xrp-research/1.0"}), timeout=120) as response:
            path.write_bytes(response.read())
    return path.read_bytes()


def stamp(y, m=1):
    return int(dt.datetime(y, m, 1, tzinfo=UTC).timestamp() * 1000)


def metric(cache):
    query = urllib.parse.urlencode(dict(assets="xrp", metrics="AdrBalCnt", frequency="1d", start_time="2020-01-01", end_time="2026-10-01", page_size=10000))
    url = "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?" + query
    payload = get(url, cache / "coinmetrics-xrp-holder-count.json")
    obj = json.loads(payload)
    if "error" in obj or obj.get("next_page_token") or obj.get("next_page_url"):
        raise ValueError("incomplete CoinMetrics response")
    rows = []
    for x in obj["data"]:
        ts = int(dt.datetime.fromisoformat(x["time"].replace("Z", "+00:00")).timestamp() * 1000)
        rows.append(dict(timestamp=ts, holders=float(x["AdrBalCnt"])))
    return rows, dict(kind="coinmetrics_XRP_AdrBalCnt", url=url, sha256=hashlib.sha256(payload).hexdigest(), bytes=len(payload), rows=len(rows))


def prices(cache):
    out, manifest = [], []
    for y, m in MONTHS:
        name = f"XRPUSDT-1d-{y}-{m:02d}.zip"
        url = f"https://data.binance.vision/data/spot/monthly/klines/XRPUSDT/1d/{name}"
        payload = get(url, cache / name)
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            raw = list(csv.reader(io.TextIOWrapper(archive.open(archive.namelist()[0]))))
        rows = []
        for x in raw:
            if x[0].lower().startswith("open"):
                continue
            ts = int(x[0]); ts = ts // 1000 if ts > 10**14 else ts
            rows.append(dict(timestamp=ts, open=float(x[1]), high=float(x[2]), low=float(x[3]), close=float(x[4])))
        out += rows
        manifest.append(dict(kind="binance_XRPUSDT_1d", url=url, sha256=hashlib.sha256(payload).hexdigest(), bytes=len(payload), rows=len(rows)))
    return out, manifest


def unique(rows, name):
    data, duplicates = {}, 0
    for x in rows:
        if x["timestamp"] in data:
            if data[x["timestamp"]] != x:
                raise ValueError("conflicting duplicate " + name)
            duplicates += 1
        data[x["timestamp"]] = x
    return data, duplicates


def folds():
    return [("2020_2021_control", stamp(2020), stamp(2022)), ("2022", stamp(2022), stamp(2023)), ("2023", stamp(2023), stamp(2024)), ("2024", stamp(2024), stamp(2025)), ("2025", stamp(2025), stamp(2026)), ("2026", stamp(2026), stamp(2026, 10)), ("continuous_oos", stamp(2022), stamp(2026, 10))]


def metrics(trades, curve, initial=10_000):
    gain = sum(max(0, x["pnl"]) for x in trades)
    loss = -sum(min(0, x["pnl"]) for x in trades)
    net = sum(x["pnl"] for x in trades)
    peak, drawdown = initial, 0
    for x in curve:
        peak = max(peak, x["equity"])
        drawdown = max(drawdown, (peak - x["equity"]) / peak * 100)
    return dict(trades=len(trades), net_pnl=net, net_return_pct=net / initial * 100, profit_factor=gain / loss if loss else None, expectancy=net / len(trades) if trades else None, max_drawdown_pct=drawdown, fees=sum(x["fees"] for x in trades), slippage_cost=sum(x["slippage_cost"] for x in trades))


def main():
    cache = pathlib.Path(sys.argv[1]); cache.mkdir(parents=True, exist_ok=True)
    dest = pathlib.Path(sys.argv[2]); dest.mkdir(parents=True, exist_ok=True)
    mr, mm = metric(cache); pr, pm = prices(cache)
    md, mdup = unique(mr, "metric"); pd, pdup = unique(pr, "price")
    common = sorted(set(md) & set(pd)); rows = [{**pd[t], **md[t]} for t in common]; validate(rows)
    quality = dict(metric_rows=len(md), price_rows=len(pd), aligned_days=len(rows), metric_duplicates=mdup, price_duplicates=pdup, metric_only=len(set(md) - set(pd)), price_only=len(set(pd) - set(md)), gaps=[dict(after=a["timestamp"], before=b["timestamp"], missing_days=(b["timestamp"] - a["timestamp"]) // DAY - 1) for a, b in zip(rows, rows[1:]) if b["timestamp"] - a["timestamp"] != DAY])
    runs, ledgers = {}, {}
    for name, start, end in folds():
        for label, multiple in (("base", 1), ("stress", 2)):
            base = Config(); config = replace(base, fee=base.fee * multiple, slippage=base.slippage * multiple)
            trades, curve = backtest(rows, start, end, config)
            key = f"{name}_{label}"; ledgers[key] = trades; runs[key] = metrics(trades, curve)
            print(key, runs[key], flush=True)
    years = ["2022", "2023", "2024", "2025", "2026"]
    base_trades = [x for y in years for x in ledgers[f"{y}_base"]]
    stress_trades = [x for y in years for x in ledgers[f"{y}_stress"]]
    base_agg = metrics(base_trades, [{"equity": 10000}, {"equity": 10000 + sum(x["pnl"] for x in base_trades)}])
    stress_agg = metrics(stress_trades, [{"equity": 10000}, {"equity": 10000 + sum(x["pnl"] for x in stress_trades)}])
    by_year = {y: runs[f"{y}_base"]["net_pnl"] for y in years}; stress_by_year = {y: runs[f"{y}_stress"]["net_pnl"] for y in years}
    monthly = {}
    for x in base_trades:
        key = dt.datetime.fromtimestamp(x["exit_timestamp"] / 1000, UTC).strftime("%Y-%m")
        monthly[key] = monthly.get(key, 0) + x["pnl"]
    positive_months = sum(max(0, x) for x in monthly.values())
    gates = dict(sample=base_agg["trades"] >= 75, base_net=base_agg["net_pnl"] > 0, base_expectancy=(base_agg["expectancy"] or 0) > 0, base_pf=(base_agg["profit_factor"] or 0) > 1.15, stress_net=stress_agg["net_pnl"] > 0, stress_expectancy=(stress_agg["expectancy"] or 0) > 0, stress_pf=(stress_agg["profit_factor"] or 0) > 1.02, four_positive_years=sum(x > 0 for x in by_year.values()) >= 4, four_positive_stress_years=sum(x > 0 for x in stress_by_year.values()) >= 4, final_year=by_year["2026"] > 0 and stress_by_year["2026"] > 0, drawdown=max(runs["continuous_oos_base"]["max_drawdown_pct"], runs["continuous_oos_stress"]["max_drawdown_pct"]) <= 10, concentration=base_agg["net_pnl"] > 0 and positive_months > 0 and max(monthly.values(), default=0) <= .25 * positive_months)
    historical_pass = all(gates.values())
    protocol = pathlib.Path("research/holder_growth_divergence_protocol.md")
    result = dict(strategy="XRP_HOLDER_GROWTH_DIVERGENCE_V1", status="TEST NEDOKONCEN: independent forward PAPER evidence required" if historical_pass else "NEPROSEL", protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(), manifest=[mm] + pm, data_quality=quality, runs=runs, aggregate_oos=base_agg, aggregate_stress=stress_agg, by_year=by_year, stress_by_year=stress_by_year, monthly_base=monthly, gates=gates, historical_pass=historical_pass, limitations=["AdrBalCnt is third-party derived and may be historically revised; response bytes are locally hashed, not publisher-signed.", "A full-day publication lag prevents same-day metric leakage; exact dates only, with no interpolation.", "Daily OHLC is not tick execution; historical dates are exploratory and no forward PAPER evidence exists."])
    (dest / "results.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    with gzip.open(dest / "trades.json.gz", "wt") as handle:
        json.dump(ledgers, handle)
    print(result["status"], gates, flush=True)


if __name__ == "__main__":
    main()
