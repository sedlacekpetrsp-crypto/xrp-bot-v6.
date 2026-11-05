"""Independent miner-revenue recovery audit without importing strategy code."""
import gzip
import hashlib
import json
import pathlib
import statistics
import sys

DAY = 86400000
root = pathlib.Path(sys.argv[1]); cache = pathlib.Path(sys.argv[2])
result = json.loads((root / "results.json").read_text())
with gzip.open(root / "trades.json.gz", "rt") as handle: ledgers = json.load(handle)
checks = 0; failures = []


def check(value, message):
    global checks
    checks += 1
    if not value: failures.append(message)


source = {}; prices = {}; page = 0
for manifest in result["manifest"]:
    if manifest["kind"] == "BLOCKCHAIN_COM_MINERS_REVENUE":
        path = cache / "blockchain-miners-revenue.json"
    else:
        path = cache / f"XRPUSDT-1d-credit-api-{page}.json"; page += 1
    payload = path.read_bytes()
    check(hashlib.sha256(payload).hexdigest() == manifest["sha256"], "hash:" + path.name)
    if manifest["kind"] == "BLOCKCHAIN_COM_MINERS_REVENUE":
        for row in json.loads(payload)["values"]:
            source[int(row["x"]) * 1000] = float(row["y"])
    else:
        for row in json.loads(payload):
            prices[int(row[0])] = {"open": float(row[1]), "high": float(row[2]), "low": float(row[3]), "close": float(row[4])}

ordered = sorted(source); location = {timestamp: index for index, timestamp in enumerate(ordered)}
for key, trades in ledgers.items():
    previous = None; equity = 10000.0
    fee = 0.0019 if key.endswith("_stress") else 0.00095
    slip = 0.0004 if key.endswith("_stress") else 0.0002
    for number, trade in enumerate(trades):
        label = f"{key}[{number}]"; latest_i = location[trade["metric_timestamp"]]; signal_i = location[trade["signal_timestamp"]]
        history = [source[timestamp] for timestamp in ordered[latest_i - 90 : latest_i]]
        recent = [source[timestamp] for timestamp in ordered[latest_i - 6 : latest_i + 1]]
        prior = [source[timestamp] for timestamp in ordered[latest_i - 13 : latest_i - 6]]
        check(signal_i - latest_i == 2, label + ":lag")
        check(trade["latest_miner_revenue"] > statistics.median(history), label + ":median")
        check(sum(recent) / 7 > sum(prior) / 7, label + ":trend")
        check(trade["entry_timestamp"] - trade["signal_timestamp"] == DAY, label + ":entry")
        check(abs(trade["raw_entry"] - prices[trade["entry_timestamp"]]["open"]) < 1e-12, label + ":open")
        check(previous is None or trade["entry_timestamp"] > previous, label + ":overlap")
        check(trade["leg_notional"] <= trade["entry_equity"] * 0.2 + 1e-7, label + ":cap")
        check(trade["qty"] * (trade["entry"] - trade["stop"]) <= trade["entry_equity"] * 0.005 + 1e-7, label + ":risk")
        expected_fees = fee * trade["qty"] * (trade["entry"] + trade["exit"])
        fill_pnl = trade["qty"] * (trade["exit"] - trade["entry"])
        check(abs(expected_fees - trade["fees"]) < 1e-7, label + ":fees")
        check(abs(fill_pnl - trade["fees"] - trade["pnl"]) < 1e-7, label + ":pnl")
        check(abs(trade["entry_equity"] - equity) < 1e-7 and abs(trade["equity"] - equity - trade["pnl"]) < 1e-7, label + ":equity")
        check(trade["intratrade_min_equity"] <= trade["entry_equity"] + 1e-7, label + ":dd")
        check(abs(trade["entry"] - trade["raw_entry"] * (1 + slip)) < 1e-9, label + ":entry_slip")
        check(abs(trade["exit"] - trade["raw_exit"] * (1 - slip)) < 1e-9, label + ":exit_slip")
        previous = trade["exit_timestamp"]; equity = trade["equity"]
    check(len(trades) == result["runs"][key]["trades"], key + ":count")
    check(abs(sum(trade["pnl"] for trade in trades) - result["runs"][key]["net_pnl"]) < 1e-7, key + ":net")

passed = not failures
result["gates"]["audit"] = passed
historical = all(value for key, value in result["gates"].items() if key != "forward_paper")
result["status"] = "TEST NEDOKONCEN: forward PAPER required" if historical else "NEPROSEL"
(root / "results.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
audit = {"passed": passed, "checks": checks, "failures": failures}
(root / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
print(json.dumps(audit))
if not passed: raise SystemExit(1)
