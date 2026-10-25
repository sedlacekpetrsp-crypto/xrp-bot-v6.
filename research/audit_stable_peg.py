"""Independent stable-peg ledger audit without strategy imports."""
import gzip,json,math,pathlib,sys
def main():
    root=pathlib.Path(sys.argv[1]);r=json.loads((root/'results.json').read_text());initial=10000/3
    with gzip.open(root/'trades.json.gz','rt') as f:led=json.load(f)
    counts={}
    for name,ts in led.items():
        fee=.0019 if name.endswith('_stress') else .00095;slip=.0004 if name.endswith('_stress') else .0002;cash=initial;last=-1
        for t in ts:
            assert t['signal_index']+1==t['entry_index']<=t['exit_index'] and t['entry_index']>last
            assert t['entry_timestamp']%900000==0 and t['exit_timestamp']>=t['entry_timestamp']
            assert t['entry']*t['qty']<=cash*.2+1e-8 and (t['entry']-t['stop'])*t['qty']<=cash*.005+1e-8
            fees=fee*t['qty']*(t['entry']+t['exit']);pnl=t['qty']*(t['exit']-t['entry'])-fees;gross=t['qty']*(t['exit']/(1-slip)-t['entry']/(1+slip))
            assert math.isclose(fees,t['fees'],abs_tol=1e-8) and math.isclose(pnl,t['pnl'],abs_tol=1e-8) and math.isclose(gross,t['gross'],abs_tol=1e-8)
            cash+=pnl;assert math.isclose(cash,t['equity'],abs_tol=1e-8);last=t['exit_index']
        assert len(ts)==r['runs'][name]['trades'] and math.isclose(cash-initial,r['runs'][name]['net_pnl'],abs_tol=1e-7);counts[name]=len(ts)
    report=dict(status='PASS',checks=['chronology and no overlap per sleeve','next-open timing','sleeve notional and risk','fees/slippage/P&L/equity','ledger/report reconciliation'],trades_by_run=counts,note='Quarter and continuous runs reuse observations; do not add them.')
    (root/'audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
