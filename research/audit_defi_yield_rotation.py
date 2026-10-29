"""Independent ledger/provenance audit; does not import strategy implementation."""
import csv, gzip, hashlib, io, json, pathlib, sys, zipfile

TOL=1e-7

def close(a,b,scale=1.0):
    return abs(a-b) <= TOL*max(scale,abs(a),abs(b))

def main():
    cache=pathlib.Path(sys.argv[1]); dest=pathlib.Path(sys.argv[2])
    result=json.loads((dest/"results.json").read_text())
    with gzip.open(dest/"trades.json.gz","rt") as h: ledgers=json.load(h)
    checks=[]
    def check(name,ok,detail=""):
        checks.append(dict(name=name,pass_=bool(ok),detail=detail))
    for item in result["manifest"]:
        if item["kind"]=="defillama_yields": path=cache/"defillama-aave-v3-ethereum-usdc.json"
        else: path=cache/item["url"].rsplit("/",1)[-1]
        check("sha256:"+path.name,path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()==item["sha256"])
    prices={}
    for p in sorted(cache.glob("XRPUSDT-1d-*.zip")):
        with zipfile.ZipFile(p) as z: raw=csv.reader(io.TextIOWrapper(z.open(z.namelist()[0])))
        for x in raw:
            if x[0].lower().startswith("open"): continue
            ts=int(x[0]); ts=ts//1000 if ts>10**14 else ts
            prices[ts]=dict(open=float(x[1]),high=float(x[2]),low=float(x[3]),close=float(x[4]))
    for key,trades in ledgers.items():
        prior_exit=-1; prior_equity=10000.0
        multiple=2 if key.endswith("stress") else 1
        fee=.00095*multiple; slip=.00020*multiple
        for n,t in enumerate(trades):
            prefix=f"{key}:{n}"
            check(prefix+":causal",t["signal_timestamp"]<t["entry_timestamp"])
            check(prefix+":nonoverlap",t["entry_timestamp"]>prior_exit)
            check(prefix+":indices",t["exit_index"]>=t["entry_index"])
            check(prefix+":raw_entry",close(t["raw_entry"],prices[t["entry_timestamp"]]["open"]))
            check(prefix+":entry_slippage",close(t["entry"],t["raw_entry"]*(1+slip)))
            check(prefix+":exit_slippage",close(t["exit"],t["raw_exit"]*(1-slip)))
            expected_fee=t["qty"]*(t["entry"]+t["exit"])*fee
            check(prefix+":fees",close(t["fees"],expected_fee))
            expected_pnl=t["qty"]*(t["exit"]-t["entry"])-expected_fee
            check(prefix+":pnl",close(t["pnl"],expected_pnl))
            check(prefix+":equity_in",close(t["entry_equity"],prior_equity))
            check(prefix+":equity_out",close(t["equity"],prior_equity+t["pnl"]))
            risk=t["qty"]*(t["entry"]-t["stop"])
            check(prefix+":risk",risk<=t["entry_equity"]*.005+TOL)
            check(prefix+":notional",t["leg_notional"]<=t["entry_equity"]*.20+TOL)
            if t["reason"]=="GAP_STOP": check(prefix+":gap_stop",close(t["raw_exit"],prices[t["exit_timestamp"]]["open"]) and t["raw_exit"]<=t["stop"])
            prior_exit=t["exit_timestamp"]; prior_equity=t["equity"]
        check(key+":net",close(sum(x["pnl"] for x in trades),result["runs"][key]["net_pnl"]))
        check(key+":count",len(trades)==result["runs"][key]["trades"])
    passed=all(x["pass_"] for x in checks)
    audit=dict(passed=passed,checks=len(checks),failed=[x for x in checks if not x["pass_"]],method="Independent raw-hash, chronology, fills, costs, sizing, non-overlap and equity reconciliation; no strategy module imported.")
    (dest/"audit.json").write_text(json.dumps(audit,indent=2).replace('"pass_"','"pass"')+"\n")
    result["gates"]["audit"]=passed
    result["status"]="NEPROSEL" if not all(result["gates"].values()) else "PROSEL"
    (dest/"results.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps(audit,indent=2))
    if not passed: raise SystemExit(1)

if __name__=="__main__": main()
