"""Independent ledger arithmetic audit; no strategy import."""
import gzip,json,sys
def close(a,b): return abs(a-b)<=1e-7*max(1,abs(a),abs(b))
def main():
    root=sys.argv[1]; r=json.load(open(root+'/results.json')); ledger=json.load(gzip.open(root+'/trades.json.gz','rt')); checks=0; bad=[]
    for key,trades in ledger.items():
        fee=.00095*(2 if key.endswith('_stress') else 1); eq=10000.; prev=-1
        for n,t in enumerate(trades):
            def check(ok,label):
                nonlocal checks; checks+=1
                if not ok: bad.append(f'{key}[{n}] {label}')
            check(t['signal_timestamp']<t['entry_timestamp']<=t['exit_timestamp'],'chronology'); check(t['entry_timestamp']>prev,'overlap'); check(close(t['fees'],fee*t['qty']*(t['entry']+t['exit'])),'fees'); check(close(t['pnl'],t['qty']*(t['exit']-t['entry'])-t['fees']),'pnl'); check(t['qty']*t['entry']<=eq*.20+1e-6,'cap'); check(t['qty']*(t['entry']-t['stop'])<=eq*.005+1e-6,'risk'); eq+=t['pnl']; check(close(eq,t['equity']),'equity'); prev=t['exit_timestamp']
        checks+=2
        if r['runs'][key]['trades']!=len(trades): bad.append(key+' count')
        if not close(r['runs'][key]['net_pnl'],sum(t['pnl'] for t in trades)): bad.append(key+' total')
    checks+=2
    if len(r['manifest'])!=57: bad.append('manifest count')
    if any(len(x['sha256'])!=64 for x in r['manifest']): bad.append('hash')
    out=dict(checks=checks,failures=bad,passed=not bad); open(root+'/audit.json','w').write(json.dumps(out,indent=2)+'\n'); print(json.dumps(out))
    if bad: raise SystemExit(1)
if __name__=='__main__': main()

