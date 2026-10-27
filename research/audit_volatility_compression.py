"""Independent arithmetic/invariant audit without importing strategy code."""
import gzip,json,sys
def close(a,b): return abs(a-b)<=1e-7*max(1,abs(a),abs(b))
def main():
    root=sys.argv[1]; result=json.load(open(root+"/results.json")); ledger=json.load(gzip.open(root+"/trades.json.gz","rt")); checks=0; failures=[]
    for key,trades in ledger.items():
        fee=.00095*(2 if key.endswith("_stress") else 1); eq=10000.; prior=-1
        for n,t in enumerate(trades):
            def check(ok,label):
                nonlocal checks; checks+=1
                if not ok: failures.append(f"{key}[{n}] {label}")
            check(t["signal_timestamp"]<t["entry_timestamp"]<=t["exit_timestamp"],"chronology")
            check(t["entry_timestamp"]>prior,"overlap")
            check(close(t["fees"],fee*t["qty"]*(t["entry"]+t["exit"])),"fees")
            check(close(t["pnl"],t["qty"]*(t["exit"]-t["entry"])-t["fees"]),"pnl")
            check(t["qty"]*t["entry"]<=eq*.20+1e-6,"cap")
            check(t["qty"]*(t["entry"]-t["stop"])<=eq*.005+1e-6,"risk")
            eq+=t["pnl"]; check(close(t["equity"],eq),"equity"); prior=t["exit_timestamp"]
        checks+=2
        if result["runs"][key]["trades"]!=len(trades): failures.append(key+" count")
        if not close(result["runs"][key]["net_pnl"],sum(t["pnl"] for t in trades)): failures.append(key+" total")
    checks+=2
    if len(result["manifest"])!=57: failures.append("manifest count")
    if any(len(x["sha256"])!=64 for x in result["manifest"]): failures.append("hash")
    out={"checks":checks,"failures":failures,"passed":not failures}; open(root+"/audit.json","w").write(json.dumps(out,indent=2)+"\n"); print(json.dumps(out))
    if failures: raise SystemExit(1)
if __name__=="__main__": main()

