"""Cost and activity diagnostics; no post-result parameter selection."""
import argparse,json,tarfile,math,statistics
from datetime import datetime,timezone
from pathlib import Path
from elite.research_data import load_cached
from elite.buffered_v59 import decisions
from elite.research_engine import simulate
from elite.research_run import compact


def run(cache,out):
    dest=Path(out)
    with tarfile.open(dest/'evidence.tar.gz') as archive:
        evidence=json.load(archive.extractfile('full_evidence.json'))
    summary=json.loads((dest/'summary.json').read_text())
    original=json.loads(Path('elite/results/20261017_v57/summary.json').read_text())
    assert summary['candidates']['v57_control']==original['candidates']['v57']
    rows,_=load_cached(cache)
    days=len(rows)/288
    report={'phase':'POST_RESULT_DIAGNOSTICS_NOT_SELECTION','control_summary_exact':True,
            'ledgers_reconciled':0,'dataset_days':days,'candidates':{}}
    period_days={'2023':275,'2024_H1':182,'2024_H2':184,'2025_2026':638}
    assert sum(period_days.values())==days
    for name,periods in evidence.items():
        for runs in periods.values():
            for result in runs.values():
                trades=result['trade_log']
                assert math.isclose(sum(t['pnl'] for t in trades),result['net_pnl'],abs_tol=1e-7)
                assert all(a['exit_index']<b['entry_index'] for a,b in zip(trades,trades[1:]))
                interval=3600000
                assert all(t['entry_timestamp']%interval==0 for t in trades)
                report['ledgers_reconciled']+=1
        trades=periods['continuous']['base']['trade_log']
        entries=[t['entry_timestamp'] for t in trades]
        boundaries=[rows[0][0],*entries,rows[-1][0]+300000]
        r={
            'exit_reasons':{reason:{'trades':sum(t['reason']==reason for t in trades),'net_pnl':sum(t['pnl'] for t in trades if t['reason']==reason)} for reason in sorted({t['reason'] for t in trades})},
            'trades_per_week':len(trades)*7/days,
            'trades_per_month':len(trades)/42,
            'period_trades_per_week':{p:periods[p]['base']['trades']*7/d for p,d in period_days.items()},
            'active_entry_months':len({datetime.fromtimestamp(t/1000,timezone.utc).strftime('%Y-%m') for t in entries}),
            'total_months':42,
            'max_between_entries_days':max((b-a for a,b in zip(entries,entries[1:])),default=0)/86400000 if len(entries)>1 else None,
            'max_entry_gap_including_boundaries_days':max(b-a for a,b in zip(boundaries,boundaries[1:]))/86400000,
            'median_holding_hours':statistics.median((t['exit_timestamp']-t['entry_timestamp'])/3600000 for t in trades) if trades else None,
            'net_minus_top3':sum(t['pnl'] for t in trades)-sum(sorted((t['pnl'] for t in trades),reverse=True)[:3])}
        if name!='v57_control':
            zero=simulate(rows,decisions(rows),fee=0,slip=0,half_spread=0)
            r['zero_cost_continuous']=compact(zero)
        report['candidates'][name]=r
    (dest/'diagnostics.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps(report))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cache',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();run(a.cache,a.out)
