"""Post-result explanation only; never changes acceptance or strategy parameters."""
import argparse,json,tarfile,math
from pathlib import Path
from elite.research_data import load_cached
from elite.session_v49 import decisions
from elite.research_engine import simulate
from elite.research_run import compact

def run(cache,out):
    dest=Path(out)
    with tarfile.open(dest/'evidence.tar.gz') as archive:
        evidence=json.load(archive.extractfile('full_evidence.json'))
    rows,_=load_cached(cache)
    report={'phase':'POST_RESULT_DIAGNOSTICS_NOT_SELECTION','ledgers_reconciled':0,'candidates':{}}
    for name,periods in evidence.items():
        for period,runs in periods.items():
            for mode,result in runs.items():
                trades=result['trade_log']
                assert math.isclose(sum(t['pnl'] for t in trades),result['net_pnl'],abs_tol=1e-7)
                assert all(a['exit_index']<b['entry_index'] for a,b in zip(trades,trades[1:]))
                assert all(t['entry_timestamp']%3600000==0 for t in trades)
                assert len({t['entry_timestamp']//86400000 for t in trades})==len(trades)
                assert all(t['exit_timestamp']<=((t['entry_timestamp']//86400000)+1)*86400000 for t in trades)
                report['ledgers_reconciled']+=1
        sig=decisions(rows,name)
        zero=simulate(rows,sig,fee=0,slip=0,half_spread=0)
        trades=periods['continuous']['base']['trade_log']
        report['candidates'][name]={
            'zero_cost_continuous':compact(zero),
            'net_minus_top_3_trade_pnl':sum(t['pnl'] for t in trades)-sum(sorted((t['pnl'] for t in trades),reverse=True)[:3]),
            'exit_reasons':{reason:{'trades':sum(t['reason']==reason for t in trades), 'net_pnl':sum(t['pnl'] for t in trades if t['reason']==reason)} for reason in sorted({t['reason'] for t in trades})},
            'median_holding_hours':__import__('statistics').median((t['exit_timestamp']-t['entry_timestamp'])/3600000 for t in trades),
        }
    (dest/'diagnostics.json').write_text(json.dumps(report,indent=2,allow_nan=False))
    print(json.dumps(report))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cache',required=True);p.add_argument('--out',required=True)
    args=p.parse_args();run(args.cache,args.out)
