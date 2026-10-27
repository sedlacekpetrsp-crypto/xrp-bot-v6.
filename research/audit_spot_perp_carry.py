"""Independent arithmetic and invariant audit; does not import strategy code."""
import gzip,json,sys

def close(a,b,tol=1e-7): return abs(a-b)<=tol*max(1,abs(a),abs(b))

def main():
    root=sys.argv[1]; results=json.load(open(root+"/results.json")); ledger=json.load(gzip.open(root+"/trades.json.gz","rt"))
    checks=0; failures=[]
    for key,trades in ledger.items():
        prior=-1
        for n,t in enumerate(trades):
            def check(ok,label):
                nonlocal checks; checks+=1
                if not ok: failures.append(f"{key}[{n}] {label}")
            check(t["signal_timestamp"]<t["entry_timestamp"]<=t["exit_timestamp"],"chronology")
            check(t["entry_timestamp"]>prior,"overlap")
            check(close(t["leg_notional"],0.10*t["entry_equity"]),"position cap")
            fill=t["spot_qty"]*(t["spot_exit"]-t["spot_entry"])+t["mark_qty"]*(t["mark_entry"]-t["mark_exit"])
            check(close(t["gross"]-fill,t["slippage_cost"]),"slippage")
            check(close(fill+t["funding_cash"]-t["fees"],t["pnl"]),"pnl")
            check(t["fees"]>=0 and t["slippage_cost"]>=-1e-8,"cost signs")
            check(t["funding_count"]>=0,"funding count")
            prior=t["exit_timestamp"]
        run=results["runs"][key]
        checks+=2
        if run["trades"]!=len(trades): failures.append(key+" count")
        if not close(run["net_pnl"],sum(t["pnl"] for t in trades)): failures.append(key+" total")
    checks+=2
    if len(results["manifest"])!=171: failures.append("manifest count")
    if any(len(x["sha256"])!=64 for x in results["manifest"]): failures.append("sha256")
    output={"checks":checks,"failures":failures,"passed":not failures}
    open(root+"/audit.json","w").write(json.dumps(output,indent=2)+"\n"); print(json.dumps(output))
    if failures: raise SystemExit(1)

if __name__=="__main__": main()

