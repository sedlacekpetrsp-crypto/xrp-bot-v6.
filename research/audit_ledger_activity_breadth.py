"""Independent trade-ledger arithmetic audit; no strategy import."""
import gzip,json,pathlib,sys
root=pathlib.Path(sys.argv[1]);result=json.loads((root/"results.json").read_text())
with gzip.open(root/"trades.json.gz","rt") as h:ledgers=json.load(h)
checks=0;fail=[]
def ck(ok,msg):
 global checks;checks+=1
 if not ok:fail.append(msg)
for key,trades in ledgers.items():
 prev=None;stress=key.endswith("_stress");fee=.0019 if stress else .00095
 for n,t in enumerate(trades):
  p=f"{key}[{n}]";ck(t["signal_timestamp"]-t["metric_timestamp"]==86400000,p+" metric lag");ck(t["entry_timestamp"]-t["metric_timestamp"]==2*86400000,p+" entry lag");ck(prev is None or t["entry_timestamp"]>prev,p+" overlap");prev=t["exit_timestamp"]
  ck(t["leg_notional"]<=t["entry_equity"]*.20+1e-7,p+" cap")
  fees=fee*t["qty"]*(t["entry"]+t["exit"]);ck(abs(fees-t["fees"])<1e-7,p+" fees")
  fill=t["qty"]*(t["exit"]-t["entry"]);ck(abs(fill-t["fees"]-t["pnl"])<1e-7,p+" pnl");ck(abs(t["gross"]-fill-t["slippage_cost"])<1e-7,p+" slippage")
ck(result["historical_pass"]==all(result["gates"].values()),"gate aggregate");ck(result["status"]==("TEST NEDOKONCEN: independent forward PAPER evidence required" if result["historical_pass"] else "NEPROSEL"),"status")
out={"checks":checks,"failures":fail,"passed":not fail};(root/"audit.json").write_text(json.dumps(out,indent=2)+"\n");print(json.dumps(out));raise SystemExit(bool(fail))
