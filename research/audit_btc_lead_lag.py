"""Independent ledger arithmetic and chronology audit; does not import strategy code."""
import gzip,json,math,pathlib,sys

def main():
    root=pathlib.Path(sys.argv[1]);results=json.loads((root/'results.json').read_text())
    with gzip.open(root/'trades.json.gz','rt') as f:ledger=json.load(f)
    counts={}
    for name,trades in ledger.items():
        fee=.0019 if name.endswith('_stress') else .00095
        slip=.0004 if name.endswith('_stress') else .0002
        cash=10_000.;last_exit=-1
        for t in trades:
            assert t['signal_index']+1==t['entry_index']<=t['exit_index']
            assert t['entry_index']>last_exit
            assert t['entry_timestamp'] % 3_600_000 == 0
            assert t['exit_timestamp']>=t['entry_timestamp']
            assert t['qty']*t['entry']<=cash*.2+1e-7
            assert t['qty']*(t['entry']-t['stop'])<=cash*.005+1e-7
            fees=fee*t['qty']*(t['entry']+t['exit'])
            pnl=t['qty']*(t['exit']-t['entry'])-fees
            gross=t['qty']*(t['exit']/(1-slip)-t['entry']/(1+slip))
            assert math.isclose(fees,t['fees'],abs_tol=1e-8)
            assert math.isclose(pnl,t['pnl'],abs_tol=1e-8)
            assert math.isclose(gross,t['gross'],abs_tol=1e-8)
            assert math.isclose(gross-fees-pnl,t['slippage_cost'],abs_tol=1e-8)
            cash+=pnl;assert math.isclose(cash,t['equity'],abs_tol=1e-8)
            last_exit=t['exit_index']
        assert len(trades)==results['runs'][name]['trades']
        assert math.isclose(cash-10_000,results['runs'][name]['net_pnl'],abs_tol=1e-7)
        counts[name]=len(trades)
    report=dict(status='PASS',checks=['chronology and next-open timing','no overlapping positions',
        'notional and stop-distance risk limits','independent fees, slippage, P/L and equity arithmetic',
        'ledger/report reconciliation'],trades_by_run=counts,
        note='Annual folds and continuous run share observations and are not independent samples.')
    (root/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))

if __name__=='__main__':main()
