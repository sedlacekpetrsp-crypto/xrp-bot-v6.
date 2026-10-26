"""Independent ledger arithmetic/chronology audit; intentionally imports no strategy code."""
import gzip,json,pathlib,sys

def close(a,b,tol=1e-7): return abs(a-b)<=tol*max(1.,abs(a),abs(b))

def main():
    root=pathlib.Path(sys.argv[1]); results=json.loads((root/'results.json').read_text())
    with gzip.open(root/'trades.json.gz','rt') as handle: ledger=json.load(handle)
    checks=[]
    for key,trades in ledger.items():
        stress=key.endswith('_stress'); fee=.00095*(2 if stress else 1); slip=.0002*(2 if stress else 1); equity=10_000.; previous_exit=None
        for n,t in enumerate(trades):
            checks.append((t['entry_timestamp']==t['signal_timestamp']+3_600_000,key,n,'next-open'))
            checks.append((t['exit_timestamp']>=t['entry_timestamp'],key,n,'chronology'))
            checks.append((previous_exit is None or t['entry_timestamp']>previous_exit,key,n,'overlap')); previous_exit=t['exit_timestamp']
            checks.append((close(t['fees'],fee*t['qty']*(t['entry']+t['exit'])),key,n,'fees'))
            expected=t['qty']*(t['exit']-t['entry'])-t['fees']; checks.append((close(t['pnl'],expected),key,n,'pnl'))
            checks.append((t['qty']*t['entry']<=equity*.20+1e-6,key,n,'notional'))
            checks.append((t['qty']*(t['entry']-t['stop'])<=equity*.005+1e-6,key,n,'risk'))
            equity+=t['pnl']; checks.append((close(t['equity'],equity),key,n,'equity'))
    failures=[dict(run=k,trade=n,check=c) for ok,k,n,c in checks if not ok]
    output=dict(independent=True,imports_strategy=False,checks=len(checks),failures=failures,passed=not failures,manifest_sha256_count=len(results['manifest']))
    (root/'audit.json').write_text(json.dumps(output,indent=2)+'\n'); print(output)
    if failures: raise SystemExit(1)

if __name__=='__main__': main()
