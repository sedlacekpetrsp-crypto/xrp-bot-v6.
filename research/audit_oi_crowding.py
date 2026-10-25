"""Independent XRP OI-crowding ledger audit; does not import strategy code."""
import gzip
import json
import math
import pathlib
import sys


def main():
    root = pathlib.Path(sys.argv[1])
    results = json.loads((root / "results.json").read_text())
    with gzip.open(root / "trades.json.gz", "rt") as handle:
        ledger = json.load(handle)

    counts = {}
    for name, trades in ledger.items():
        fee = 0.0019 if name.endswith("_stress") else 0.00095
        slip = 0.0004 if name.endswith("_stress") else 0.0002
        cash = 10_000.0
        last_exit = -1
        for trade in trades:
            assert trade["signal_index"] + 1 == trade["entry_index"] <= trade["exit_index"]
            assert trade["entry_index"] > last_exit
            assert trade["entry_timestamp"] % 300_000 == 0
            assert trade["exit_timestamp"] >= trade["entry_timestamp"]
            assert trade["qty"] * trade["entry"] <= cash * 0.2 + 1e-7
            assert trade["qty"] * (trade["entry"] - trade["stop"]) <= cash * 0.005 + 1e-7

            fees = fee * trade["qty"] * (trade["entry"] + trade["exit"])
            pnl = trade["qty"] * (trade["exit"] - trade["entry"]) - fees
            gross = trade["qty"] * (
                trade["exit"] / (1 - slip) - trade["entry"] / (1 + slip)
            )
            assert math.isclose(fees, trade["fees"], abs_tol=1e-8)
            assert math.isclose(pnl, trade["pnl"], abs_tol=1e-8)
            assert math.isclose(gross, trade["gross"], abs_tol=1e-8)
            assert math.isclose(gross - fees - pnl, trade["slippage_cost"], abs_tol=1e-8)
            cash += pnl
            assert math.isclose(cash, trade["equity"], abs_tol=1e-8)
            last_exit = trade["exit_index"]

        assert len(trades) == results["runs"][name]["trades"]
        assert math.isclose(cash - 10_000, results["runs"][name]["net_pnl"], abs_tol=1e-7)
        counts[name] = len(trades)

    report = {
        "status": "PASS",
        "checks": [
            "chronology and next-5m-open timing",
            "no overlapping positions",
            "notional and stop-distance risk limits",
            "independent fees, slippage, P/L and equity arithmetic",
            "ledger/report reconciliation",
        ],
        "trades_by_run": counts,
        "note": "Quarter folds and continuous run share observations and are not independent samples.",
    }
    (root / "audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
