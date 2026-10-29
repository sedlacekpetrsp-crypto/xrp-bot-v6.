"""Independent real-yield easing arithmetic audit; no strategy import."""
import gzip
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
result = json.loads((root / "results.json").read_text())
with gzip.open(root / "trades.json.gz", "rt") as handle:
    ledgers = json.load(handle)

checks, failures = 0, []


def check(value, message):
    global checks
    checks += 1
    if not value:
        failures.append(message)


for key, trades in ledgers.items():
    previous_exit = None
    fee_rate = .0019 if key.endswith("_stress") else .00095
    for index, trade in enumerate(trades):
        label = f"{key}[{index}]"
        check(trade["signal_timestamp"] - trade["metric_timestamp"] >= 2 * 86_400_000, label + " release lag")
        check(trade["entry_timestamp"] - trade["signal_timestamp"] == 86_400_000, label + " next-open entry")
        check(previous_exit is None or trade["entry_timestamp"] > previous_exit, label + " overlap")
        previous_exit = trade["exit_timestamp"]
        check(trade["signal_macro_return"] <= -.25 + 1e-12, label + " yield change")
        check(trade["leg_notional"] <= trade["entry_equity"] * .2 + 1e-7, label + " notional cap")
        check(trade["qty"] * (trade["entry"] - trade["stop"]) <= trade["entry_equity"] * .005 + 1e-7, label + " stop risk")
        fees = fee_rate * trade["qty"] * (trade["entry"] + trade["exit"])
        check(abs(fees - trade["fees"]) < 1e-7, label + " fees")
        fill_pnl = trade["qty"] * (trade["exit"] - trade["entry"])
        check(abs(fill_pnl - trade["fees"] - trade["pnl"]) < 1e-7, label + " pnl")
        check(abs(trade["gross"] - fill_pnl - trade["slippage_cost"]) < 1e-7, label + " slippage")

years = ["2022", "2023", "2024", "2025", "2026"]
base_count = sum(result["runs"][f"{year}_base"]["trades"] for year in years)
stress_count = sum(result["runs"][f"{year}_stress"]["trades"] for year in years)
check(base_count == result["aggregate_oos"]["trades"], "base aggregate count")
check(stress_count == result["aggregate_stress"]["trades"], "stress aggregate count")
check(result["historical_pass"] == all(result["gates"].values()), "gates")
expected = "TEST NEDOKONCEN: independent forward PAPER evidence required" if result["historical_pass"] else "NEPROSEL"
check(result["status"] == expected, "status")
output = {"checks": checks, "failures": failures, "passed": not failures}
(root / "audit.json").write_text(json.dumps(output, indent=2) + "\n")
print(json.dumps(output))
raise SystemExit(bool(failures))
