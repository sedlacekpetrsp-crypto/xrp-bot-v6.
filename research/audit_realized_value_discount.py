"""Independent realized-value ledger audit; no strategy import."""
import gzip, json, pathlib, sys

root = pathlib.Path(sys.argv[1]); result = json.loads((root / "results.json").read_text())
with gzip.open(root / "trades.json.gz", "rt") as handle:
    ledgers = json.load(handle)
checks, failures = 0, []


def check(value, message):
    global checks
    checks += 1
    if not value:
        failures.append(message)


for key, trades in ledgers.items():
    previous = None; rate = .0019 if key.endswith("_stress") else .00095
    for i, trade in enumerate(trades):
        label = f"{key}[{i}]"
        check(trade["signal_timestamp"] - trade["metric_timestamp"] == 86_400_000, label + " metric lag")
        check(trade["entry_timestamp"] - trade["metric_timestamp"] == 172_800_000, label + " entry lag")
        check(previous is None or trade["entry_timestamp"] > previous, label + " overlap"); previous = trade["exit_timestamp"]
        check(trade["signal_mvrv"] <= .90, label + " signal")
        check(trade["leg_notional"] <= trade["entry_equity"] * .2 + 1e-7, label + " cap")
        fees = rate * trade["qty"] * (trade["entry"] + trade["exit"])
        check(abs(fees - trade["fees"]) < 1e-7, label + " fees")
        fill = trade["qty"] * (trade["exit"] - trade["entry"])
        check(abs(fill - trade["fees"] - trade["pnl"]) < 1e-7, label + " pnl")
        check(abs(trade["gross"] - fill - trade["slippage_cost"]) < 1e-7, label + " slippage")
check(result["historical_pass"] == all(result["gates"].values()), "gates")
check(result["status"] == ("TEST NEDOKONCEN: independent forward PAPER evidence required" if result["historical_pass"] else "NEPROSEL"), "status")
output = {"checks": checks, "failures": failures, "passed": not failures}
(root / "audit.json").write_text(json.dumps(output, indent=2) + "\n")
print(json.dumps(output)); raise SystemExit(bool(failures))
