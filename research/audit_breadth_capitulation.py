"""Independent breadth-capitulation ledger audit; no strategy import."""
import gzip
import json
import math
import pathlib
import sys


def main():
    root=pathlib.Path(sys.argv[1]); results=json.loads((root/"results.json").read_text())
    with gzip.open(root/"trades.json.gz","rt") as handle: ledger=json.load(handle)
    counts={}
    for name,trades in ledger.items():
        fee=.0019 if name.endswith("_stress") else .00095
        slip=.0004 if name.endswith("_stress") else .0002
        cash=10_000.; last_exit=-1
        for trade in trades:
            assert trade["entry_timestamp"]==trade["signal_timestamp"]+3_600_000
            assert trade["entry_timestamp"]>last_exit
            assert 0<=trade["exit_timestamp"]-trade["entry_timestamp"]<=23*3_600_000
            assert trade["breadth_count"]>=6
            assert trade["breadth_median"]<=-.02+1e-15
            assert trade["xrp_return"]<=-.025+1e-15
            assert trade["qty"]*trade["entry"]<=cash*.2+1e-7
            assert trade["qty"]*(trade["entry"]-trade["stop"])<=cash*.005+1e-7
            fees=fee*trade["qty"]*(trade["entry"]+trade["exit"])
            pnl=trade["qty"]*(trade["exit"]-trade["entry"])-fees
            gross=trade["qty"]*(trade["exit"]/(1-slip)-trade["entry"]/(1+slip))
            assert math.isclose(fees,trade["fees"],abs_tol=1e-8)
            assert math.isclose(pnl,trade["pnl"],abs_tol=1e-8)
            assert math.isclose(gross,trade["gross"],abs_tol=1e-8)
            assert math.isclose(gross-fees-pnl,trade["slippage_cost"],abs_tol=1e-8)
            cash+=pnl; assert math.isclose(cash,trade["equity"],abs_tol=1e-8)
            last_exit=trade["exit_timestamp"]
        assert len(trades)==results["runs"][name]["trades"]
        assert math.isclose(cash-10_000,results["runs"][name]["net_pnl"],abs_tol=1e-7)
        counts[name]=len(trades)
    report=dict(status="PASS",checks=["next-hour causal entry and frozen breadth thresholds","no overlap and maximum holding time","notional and stop-risk sizing","independent cost, slippage, P/L and equity arithmetic","ledger/report reconciliation"],trades_by_run=counts,note="Quarter folds and continuous OOS share observations and are not independent samples.")
    (root/"audit.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report))


if __name__=="__main__": main()
