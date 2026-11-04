import datetime as dt
import gzip
import hashlib
import json
import pathlib
import statistics
import sys

DAY = 86_400_000
UTC = dt.timezone.utc


def close(a, b, tol=1e-8):
    return abs(a - b) <= tol * max(1, abs(a), abs(b))


def main():
    cache = pathlib.Path(sys.argv[1])
    dest = pathlib.Path(sys.argv[2])
    result = json.loads((dest / "results.json").read_text())
    checks = []
    def check(name, value):
        checks.append(dict(name=name, passed=bool(value)))

    for item in result["manifest"]:
        raw = (cache / item["cache_file"]).read_bytes()
        check("hash_" + item["cache_file"], hashlib.sha256(raw).hexdigest() == item["sha256"] and len(raw) == item["bytes"])

    raw_metric = json.loads((cache / result["manifest"][0]["cache_file"]).read_bytes())["values"]
    cutoff = int(dt.datetime(2026, 10, 1, tzinfo=UTC).timestamp() * 1000)
    points = [(int(x["x"]) * 1000, float(x["y"])) for x in raw_metric if int(dt.datetime(2019, 1, 1, tzinfo=UTC).timestamp() * 1000) <= int(x["x"]) * 1000 < cutoff]
    check("intraday_rows", len(points) == result["data_quality"]["intraday_rows"])
    check("intraday_unique_ordered", all(b[0] > a[0] for a, b in zip(points, points[1:])) and len({x[0] for x in points}) == len(points))
    grouped = {}
    for timestamp, value in points:
        grouped.setdefault(timestamp - timestamp % DAY, []).append(value)
    daily = []
    for day in sorted(grouped):
        values = grouped[day]
        check("samples_" + str(day), len(values) >= 64)
        daily.append(dict(timestamp=day, mempool_bytes=statistics.median(values), samples=len(values)))
    check("daily_rows", len(daily) == result["data_quality"]["daily_rows"])
    check("daily_gaps", all(b["timestamp"] - a["timestamp"] == DAY for a, b in zip(daily, daily[1:])))
    with gzip.open(dest / "daily_metric.json.gz", "rt") as handle:
        stored_daily = json.load(handle)
    check("daily_exact", stored_daily == daily)

    signals = {}
    for i in range(365, len(daily)):
        row = daily[i]
        if dt.datetime.fromtimestamp(row["timestamp"] / 1000, UTC).weekday() != 4:
            continue
        window = sorted(x["mempool_bytes"] for x in daily[i - 365:i])
        cutoff_value = window[121]
        if row["mempool_bytes"] <= cutoff_value:
            signals[row["timestamp"] + 3 * DAY] = dict(metric_timestamp=row["timestamp"], mempool_bytes=row["mempool_bytes"], cutoff365=cutoff_value, samples=row["samples"])
    check("signals_total", len(signals) == result["signals_total"])

    prices = []
    for item in result["manifest"][1:]:
        doc = json.loads((cache / item["cache_file"]).read_bytes())
        check("rows_" + item["cache_file"], len(doc) == item["rows"])
        prices += [dict(timestamp=int(x[0]), open=float(x[1]), high=float(x[2]), low=float(x[3]), close=float(x[4])) for x in doc]
    check("price_rows", len(prices) == result["data_quality"]["price_rows"])
    check("price_gaps", all(b["timestamp"] - a["timestamp"] == DAY for a, b in zip(prices, prices[1:])))
    index = {x["timestamp"]: i for i, x in enumerate(prices)}
    with gzip.open(dest / "trades.json.gz", "rt") as handle:
        ledgers = json.load(handle)
    trade_checks = 0
    for key, trades in ledgers.items():
        fee = .0019 if key.endswith("_stress") else .00095
        slip = .0004 if key.endswith("_stress") else .0002
        for a, b in zip(trades, trades[1:]):
            check("nonoverlap_" + key + "_" + str(trade_checks), a["exit_timestamp"] < b["entry_timestamp"])
        curve_equities = [10_000.0]
        for trade in trades:
            trade_checks += 1
            signal = signals[trade["entry_timestamp"]]
            check("signal_" + str(trade_checks), all(close(trade[k], signal[k]) if isinstance(signal[k], float) else trade[k] == signal[k] for k in signal))
            i = index[trade["entry_timestamp"]]
            row = prices[i]
            check("monday_" + str(trade_checks), dt.datetime.fromtimestamp(trade["entry_timestamp"] / 1000, UTC).weekday() == 0)
            check("lag_" + str(trade_checks), trade["metric_timestamp"] + 3 * DAY == trade["entry_timestamp"])
            check("entry_" + str(trade_checks), close(trade["raw_entry"], row["open"]) and close(trade["entry"], row["open"] * (1 + slip)))
            av = sum(max(prices[j]["high"] - prices[j]["low"], abs(prices[j]["high"] - prices[j - 1]["close"]), abs(prices[j]["low"] - prices[j - 1]["close"])) for j in range(i - 14, i)) / 14
            check("atr_" + str(trade_checks), close(trade["atr"], av))
            check("brackets_" + str(trade_checks), close(trade["stop"], trade["entry"] - 2 * av) and close(trade["target"], trade["entry"] + 3 * (trade["entry"] - trade["stop"])))
            check("limits_" + str(trade_checks), trade["leg_notional"] <= trade["entry_equity"] * .2 + 1e-7 and trade["qty"] * (trade["entry"] - trade["stop"]) <= trade["entry_equity"] * .005 + 1e-7)
            j = index[trade["exit_timestamp"]]
            erow = prices[j]
            reason = trade["reason"]
            expected = erow["open"] if reason == "GAP_STOP" else trade["stop"] if reason == "STOP" else trade["target"] if reason == "TARGET" else erow["close"]
            check("exit_" + str(trade_checks), close(trade["raw_exit"], expected) and close(trade["exit"], expected * (1 - slip)))
            fees = trade["qty"] * trade["entry"] * fee + trade["qty"] * trade["exit"] * fee
            pnl = trade["qty"] * (trade["exit"] - trade["entry"]) - fees
            check("cost_" + str(trade_checks), close(trade["fees"], fees) and close(trade["pnl"], pnl) and close(trade["equity"], trade["entry_equity"] + pnl))
            entry_fee = trade["qty"] * trade["entry"] * fee
            # The simulator records a conservative low mark on the final fold
            # candle before realizing its close at the same timestamp.
            mark_end = j + 1 if reason == "FOLD_END" else j
            for k in range(i, mark_end):
                mark = prices[k]["low"] * (1 - slip)
                curve_equities.append(trade["entry_equity"] + trade["qty"] * (mark - trade["entry"]) - entry_fee - trade["qty"] * mark * fee)
            curve_equities.append(trade["equity"])
        metric = result["runs"][key]
        wins = sum(max(0, x["pnl"]) for x in trades)
        losses = -sum(min(0, x["pnl"]) for x in trades)
        net = sum(x["pnl"] for x in trades)
        peak = 10_000.0
        drawdown = 0.0
        for equity in curve_equities:
            peak = max(peak, equity)
            drawdown = max(drawdown, (peak - equity) / peak * 100)
        check("report_" + key, metric["trades"] == len(trades) and close(metric["net_pnl"], net) and close(metric["gross_profit"], wins) and close(metric["gross_loss"], losses) and close(metric["max_drawdown_pct"], drawdown) and (metric["profit_factor"] is None if not losses else close(metric["profit_factor"], wins / losses)))

    passed = all(x["passed"] for x in checks)
    result["gates"]["audit"] = passed
    historical = all(value for key, value in result["gates"].items() if key != "forward_paper")
    result["status"] = "TEST NEDOKONCEN: forward PAPER required" if historical else "NEPROSEL"
    (dest / "results.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    audit = dict(strategy=result["strategy"], passed=passed, checks=len(checks), trade_checks=trade_checks, failures=[x["name"] for x in checks if not x["passed"]])
    (dest / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    print(audit, flush=True)
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
