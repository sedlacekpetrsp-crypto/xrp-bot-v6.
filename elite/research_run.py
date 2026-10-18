"""Frozen V5–V7 experiment; saves full ledgers, provenance and honest gates."""
import argparse, json, hashlib, random
from pathlib import Path
from datetime import datetime,timezone
from statistics import mean
from elite.research_data import load_cached
from elite.research_engine import decisions,simulate


def timestamp(date):
    return int(datetime.fromisoformat(date).replace(tzinfo=timezone.utc).timestamp()*1000)


def bootstrap(daily):
    levels=list(daily.values()); prev=10000.; changes=[]
    for x in levels: changes.append(x-prev); prev=x
    if not changes:return [None,None]
    rng=random.Random(713); n=len(changes); samples=[]
    for _ in range(2000):
        selected=[]
        while len(selected)<n:
            start=rng.randrange(n)
            selected.extend(changes[(start+j)%n] for j in range(7))
        samples.append(mean(selected[:n]))
    samples.sort()
    return [samples[49],samples[1949]]


def compact(result):
    return {k:v for k,v in result.items() if k not in ('daily_equity','trade_log')}


def run(cache,out):
    dest=Path(out); dest.mkdir(parents=True,exist_ok=True)
    rows,manifest=load_cached(cache)
    (dest/'data_manifest.json').write_text(json.dumps(manifest,indent=2))
    report=dict(protocol_sha256=hashlib.sha256(Path('elite/RESEARCH_PROTOCOL_V5.md').read_bytes()).hexdigest(),
                dataset_bars=len(rows),costs_per_side=dict(fee=.001,slippage=.0003,half_spread=.0001),
                warning='Historical screening only; diagnostic period already reused; no profitability guarantee.',candidates={})
    periods=[('development','2023-04-01','2024-01-01'),('validation','2024-01-01','2024-07-01'),
             ('holdout','2024-07-01','2025-01-01'),('diagnostic','2025-01-01','2026-10-01')]
    import bisect
    times=[r[0] for r in rows]
    for name in ('v5','v6','v7'):
        signals=decisions(rows,name); result={}; ledgers={}; daily={}
        for label,a,b in periods:
            lo=bisect.bisect_left(times,timestamp(a)); hi=bisect.bisect_left(times,timestamp(b))
            base=simulate(rows,signals,lo,hi)
            stress=simulate(rows,signals,lo,hi,fee=.002,slip=.0006,half_spread=.0002)
            ci=bootstrap(base['daily_equity'])
            failures=[]
            if base['trades']<30:failures.append('fewer_than_30_trades')
            if base['net_pnl']<=0:failures.append('nonpositive_net_pnl')
            if base['profit_factor'] is None or base['profit_factor']<1.2:failures.append('profit_factor_below_1.2')
            if base['close_mtm_drawdown_pct']>10:failures.append('close_drawdown_above_10pct')
            if base['intrabar_drawdown_bound_pct']>12:failures.append('intrabar_bound_above_12pct')
            if stress['net_pnl']<=0:failures.append('nonpositive_stress_pnl')
            if ci[0] is None or ci[0]<=0:failures.append('uncertain_daily_expectancy')
            result[label]=dict(start=a,end_exclusive=b,base=compact(base),stress=compact(stress),
                               mean_daily_pnl_95pct_block_bootstrap=ci,failed_gates=failures)
            ledgers[label]=dict(base=base['trade_log'],stress=stress['trade_log'])
            daily[label]=base['daily_equity']
        # Quarterly marked-to-market P/L, continuous within each evaluated period.
        quarters={}
        for label,curve in daily.items():
            prev=10000.
            for day,equity in curve.items():
                date=datetime.fromtimestamp(day*86400,tz=timezone.utc)
                q=f'{date.year}-Q{(date.month-1)//3+1}'
                quarters[q]=quarters.get(q,0)+equity-prev; prev=equity
        accepted=not result['validation']['failed_gates'] and not result['holdout']['failed_gates'] and result['development']['base']['net_pnl']>0
        report['candidates'][name]=dict(periods=result,quarterly_mtm_pnl=quarters,paper_eligible=accepted)
        (dest/f'{name}_ledgers.json').write_text(json.dumps(ledgers,indent=2))
        (dest/f'{name}_daily_equity.json').write_text(json.dumps(daily,indent=2))
        print(name,json.dumps({p:dict(pnl=round(r['base']['net_pnl'],2),trades=r['base']['trades'],failures=r['failed_gates']) for p,r in result.items()}),flush=True)
    report['paper_eligible']=[n for n,r in report['candidates'].items() if r['paper_eligible']]
    (dest/'summary.json').write_text(json.dumps(report,indent=2,allow_nan=False))
    print('PAPER ELIGIBLE:',report['paper_eligible'],flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cache',required=True);p.add_argument('--out',required=True)
    args=p.parse_args();run(args.cache,args.out)
