"""Independent ledger audit; imports no strategy code."""
import gzip,json,pathlib,sys
def close(a,b): return abs(a-b)<=1e-7*max(1.,abs(a),abs(b))
def main():
    root=pathlib.Path(sys.argv[1]); result=json.loads((root/'results.json').read_text()); ledger=json.load(gzip.open(root/'trades.json.gz','rt')); checks=[]
    for key,trades in ledger.items():
        fee=.00095*(2 if key.endswith('_stress') else 1); equity=10_000.; prev=None
        for n,t in enumerate(trades):
            checks += [(t['entry_timestamp']==t['signal_timestamp']+3_600_000,key,n,'entry'),(prev is None or t['entry_timestamp']>prev,key,n,'overlap'),(close(t['fees'],fee*t['qty']*(t['entry']+t['exit'])),key,n,'fees'),(close(t['pnl'],t['qty']*(t['exit']-t['entry'])-t['fees']),key,n,'pnl'),(t['qty']*t['entry']<=equity*.20+1e-6,key,n,'cap'),(t['qty']*(t['entry']-t['stop'])<=equity*.005+1e-6,key,n,'risk')]
            prev=t['exit_timestamp']; equity+=t['pnl']; checks.append((close(t['equity'],equity),key,n,'equity'))
    failures=[dict(run=k,trade=n,check=c) for ok,k,n,c in checks if not ok]; out=dict(independent=True,imports_strategy=False,ledger_checks=len(checks),failures=failures,passed=not failures,manifest_entries=len(result['manifest']),manifest_sha256_count=sum('sha256' in x for x in result['manifest']),missing_entries=sum(x.get('missing_http_404',False) for x in result['manifest'])); (root/'audit.json').write_text(json.dumps(out,indent=2)+'\n'); print(out)
    if failures: raise SystemExit(1)
if __name__=='__main__': main()
