"""Independent RRP/XRP ledger audit; intentionally does not import strategy code."""
import csv
import datetime as dt
import gzip
import hashlib
import io
import json
import pathlib
import sys

DAY = 86_400_000
UTC = dt.timezone.utc
root = pathlib.Path(sys.argv[1])
cache = pathlib.Path(sys.argv[2])
result = json.loads((root / "results.json").read_text())
with gzip.open(root / "trades.json.gz", "rt") as handle:
    ledgers = json.load(handle)

checks, failures = 0, []


def check(value, message):
    global checks
    checks += 1
    if not value:
        failures.append(message)


macro = {}
prices = {}
for source in result["manifest"]:
    if source["kind"] == "FRED_RRPONTSYD":
        path = cache / "fred-RRPONTSYD.csv"
    else:
        page = sum(1 for prior in result["manifest"][:result["manifest"].index(source)] if prior["kind"] == "binance_XRPUSDT_1d")
        path = cache / f"XRPUSDT-1d-rrp-api-{page}.json"
    payload = path.read_bytes()
    check(hashlib.sha256(payload).hexdigest() == source["sha256"], "hash:" + path.name)
    if source["kind"] == "FRED_RRPONTSYD":
        for item in csv.DictReader(io.StringIO(payload.decode())):
            if item["RRPONTSYD"].strip() in ("", "."):
                continue
            timestamp = int(dt.datetime.strptime(item["observation_date"], "%Y-%m-%d").replace(tzinfo=UTC).timestamp() * 1000)
            macro[timestamp] = float(item["RRPONTSYD"])
    else:
        for item in json.loads(payload):
            prices[int(item[0])] = dict(open=float(item[1]), high=float(item[2]), low=float(item[3]), close=float(item[4]))

ordered_macro = sorted(macro)
macro_index = {timestamp: i for i, timestamp in enumerate(ordered_macro)}
for key, trades in ledgers.items():
    previous_exit, equity = None, 10_000.0
    fee = .0019 if key.endswith("_stress") else .00095
    slippage = .0004 if key.endswith("_stress") else .0002
    for index, trade in enumerate(trades):
        label = f"{key}[{index}]"
        latest_i = macro_index[trade["metric_timestamp"]]
        earlier_i = macro_index[trade["earlier_timestamp"]]
        signal_i = macro_index[trade["signal_timestamp"]]
        earlier, latest = macro[trade["earlier_timestamp"]], macro[trade["metric_timestamp"]]
        change = latest / earlier - 1.0
        check(signal_i - latest_i == 2, label + ":release_lag")
        check(latest_i - earlier_i == 20, label + ":lookback")
        check(earlier >= 100 and change <= -.10 + 1e-12, label + ":signal")
        check(abs(change - trade["rrp_change"]) < 1e-12, label + ":feature")
        check(trade["entry_timestamp"] - trade["signal_timestamp"] == DAY, label + ":entry_lag")
        check(abs(trade["raw_entry"] - prices[trade["entry_timestamp"]]["open"]) < 1e-12, label + ":entry_open")
        check(previous_exit is None or trade["entry_timestamp"] > previous_exit, label + ":nonoverlap")
        check(trade["leg_notional"] <= trade["entry_equity"] * .2 + 1e-7, label + ":cap")
        check(trade["qty"] * (trade["entry"] - trade["stop"]) <= trade["entry_equity"] * .005 + 1e-7, label + ":risk")
        expected_fees = fee * trade["qty"] * (trade["entry"] + trade["exit"])
        check(abs(expected_fees - trade["fees"]) < 1e-7, label + ":fees")
        fill_pnl = trade["qty"] * (trade["exit"] - trade["entry"])
        check(abs(fill_pnl - trade["fees"] - trade["pnl"]) < 1e-7, label + ":pnl")
        check(abs(trade["gross"] - fill_pnl - trade["slippage_cost"]) < 1e-7, label + ":slippage")
        check(abs(trade["entry_equity"] - equity) < 1e-7 and abs(trade["equity"] - equity - trade["pnl"]) < 1e-7, label + ":equity")
        if trade["reason"] == "GAP_STOP":
            check(trade["raw_exit"] == prices[trade["exit_timestamp"]]["open"], label + ":gap_stop_open")
            check(trade["raw_exit"] <= trade["stop"], label + ":gap_stop_worse")
        check(abs(trade["entry"] - trade["raw_entry"] * (1 + slippage)) < 1e-9, label + ":entry_slippage")
        check(abs(trade["exit"] - trade["raw_exit"] * (1 - slippage)) < 1e-9, label + ":exit_slippage")
        previous_exit, equity = trade["exit_timestamp"], trade["equity"]
    check(len(trades) == result["runs"][key]["trades"], key + ":count")
    check(abs(sum(x["pnl"] for x in trades) - result["runs"][key]["net_pnl"]) < 1e-7, key + ":net")

passed = not failures
result["gates"]["audit"] = passed
historical = all(value for key, value in result["gates"].items() if key != "forward_paper")
result["status"] = "TEST NEDOKONCEN: independent forward PAPER evidence required" if historical else "NEPROSEL"
(root / "results.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
output = dict(strategy=result["strategy"], passed=passed, checks=checks, trade_checks=sum(len(x) for x in ledgers.values()), failures=failures)
(root / "audit.json").write_text(json.dumps(output, indent=2) + "\n")
print(json.dumps(output, indent=2))
raise SystemExit(0 if passed else 1)

