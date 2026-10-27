"""Independent ledger arithmetic audit; intentionally does not import strategy code."""
import gzip, json, pathlib, sys

root=pathlib.Path(sys.argv[1]); result=json.loads((root/"results.json").read_text())
with gzip.open(root/"trades.json.gz","rt") as h: ledgers=json.load(h)
fail=[]; checks=0
def check(ok,msg):
    global checks; checks+=1
    if not ok: fail.append(msg)
for key,trades in ledgers.items():
    prev=None
    stress=key.endswith("_stress"); cf=.012 if stress else .006; bf=.001 if stress else .0005
    for n,t in enumerate(trades):
        p=f"{key}[{n}]"
        check(t["entry_timestamp"]-t["signal_timestamp"]==3600000,p+" next open")
        check(t["signal_residual"]<=-.0075+1e-12,p+" signal")
        check(prev is None or t["entry_timestamp"]>prev,p+" overlap"); prev=t["exit_timestamp"]
        check(t["leg_notional"]<=t["entry_equity"]*.10+1e-7,p+" cap")
        fees=cf*(t["coinbase_qty"]*t["coinbase_entry"]+t["coinbase_qty"]*t["coinbase_exit"])+bf*(t["binance_qty"]*t["binance_entry"]+t["binance_qty"]*t["binance_exit"])
        check(abs(fees-t["fees"])<1e-7,p+" fees")
        fill=t["coinbase_qty"]*(t["coinbase_exit"]-t["coinbase_entry"])+t["binance_qty"]*(t["binance_entry"]-t["binance_exit"])
        check(abs(fill+t["funding_cash"]-t["fees"]-t["pnl"])<1e-7,p+" pnl")
        check(abs(t["gross"]-fill-t["slippage_cost"])<1e-7,p+" slippage")
check(result["status"]==("TEST NEDOKONCEN: independent forward PAPER evidence required" if result["historical_pass"] else "NEPROSEL"),"status")
check(result["historical_pass"]==all(result["gates"].values()),"gates")
out={"checks":checks,"failures":fail,"passed":not fail}
(root/"audit.json").write_text(json.dumps(out,indent=2)+"\n")
print(json.dumps(out)); raise SystemExit(bool(fail))
