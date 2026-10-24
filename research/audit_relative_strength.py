"""Independent ledger arithmetic and chronological validation (no strategy import)."""
import gzip,json,pathlib,sys,math

def audit(folder):
    root=pathlib.Path(folder);r=json.loads((root/'results.json').read_text())
    with gzip.open(root/'trades.json.gz','rt') as f:ledger=json.load(f)
    counts={}
    for name,ts in ledger.items():
        fee=.0019 if name.endswith('_stress') else .00095
        slip=.0004 if name.endswith('_stress') else .0002
        cash=10000.;last=-1
        for t in ts:
            assert t['entry_index']>last
            assert t['signal_index']+1==t['entry_index']<=t['exit_index']
            assert t['entry_timestamp']%86400000==0
            assert t['exit_timestamp']>=t['entry_timestamp']
            assert t['qty']*t['entry']<=cash*.2+1e-7
            assert t['qty']*(t['entry']-t['stop'])<=cash*.005+1e-7
            charged=fee*t['qty']*(t['entry']+t['exit'])
            net=t['qty']*(t['exit']-t['entry'])-charged
            gross=t['qty']*(t['exit']/(1-slip)-t['entry']/(1+slip))
            assert math.isclose(charged,t['fees'],abs_tol=1e-8)
            assert math.isclose(net,t['pnl'],abs_tol=1e-8)
            assert math.isclose(gross,t['gross'],abs_tol=1e-8)
            cash+=net
            assert math.isclose(cash,t['equity'],abs_tol=1e-8)
            last=t['exit_index']
        assert math.isclose(cash-10000,r['runs'][name]['net_pnl'],abs_tol=1e-7)
        assert len(ts)==r['runs'][name]['trades']
        counts[name]=len(ts)
    report=dict(status='PASS',checks=['chronology and no overlapping positions','daily UTC entry timing','position sizing and stop-distance risk','independent fee, slippage and net equity arithmetic','ledger/report reconciliation'],trades_by_run=counts,note='Continuous and annual runs overlap in observations; counts must not be added as independent trades.')
    (root/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
if __name__=='__main__':audit(sys.argv[1])
