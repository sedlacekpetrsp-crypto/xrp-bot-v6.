"""Fixed discovery batch with locked historical challenge, never live execution."""
import argparse,bisect,json,hashlib,tarfile,io,gzip
from pathlib import Path
from datetime import datetime,timezone
from elite.research_data import load_cached
from elite.research_engine import simulate
from elite.candidates_v12 import decisions
from elite.research_run import bootstrap,compact,timestamp


def quarters(curve):
    prev=10000.;out={}
    for day,value in curve.items():
        d=datetime.fromtimestamp(int(day)*86400,tz=timezone.utc)
        key=f'{d.year}-Q{(d.month-1)//3+1}'
        out[key]=out.get(key,0)+value-prev;prev=value
    return out


def benchmark(rows,allocation):
    # Cash held idle; one buy at first open and sale at final close.
    fee=.001;adverse=.0004
    qty=10000*allocation/(rows[0][1]*(1+adverse)*(1+fee))
    equity=10000*(1-allocation)+qty*rows[-1][4]*(1-adverse)*(1-fee)
    return equity-10000


def evaluate(rows,signals,start,end):
    base=simulate(rows,signals,start,end)
    stress=simulate(rows,signals,start,end,fee=.002,slip=.0006,half_spread=.0002)
    return dict(base=compact(base),stress=compact(stress),
                mean_daily_pnl_95pct_block_bootstrap=bootstrap(base['daily_equity']),
                quarterly_mtm_pnl=quarters(base['daily_equity'])),dict(base=base,stress=stress)


def discovery_failures(periods,continuous):
    b=continuous['base'];ci=continuous['mean_daily_pnl_95pct_block_bootstrap'];fail=[]
    if sum(p['base']['net_pnl']>0 for p in periods.values())<3:fail.append('fewer_than_3_profitable_blocks')
    if b['trades']<60:fail.append('fewer_than_60_trades')
    if b['profit_factor'] is None or b['profit_factor']<1.2:fail.append('profit_factor_below_1.2')
    if b['close_mtm_drawdown_pct']>10:fail.append('close_drawdown_above_10pct')
    if b['intrabar_drawdown_bound_pct']>12:fail.append('intrabar_bound_above_12pct')
    if continuous['stress']['net_pnl']<=0:fail.append('nonpositive_stress_pnl')
    if ci[0] is None or ci[0]<=0:fail.append('uncertain_daily_expectancy')
    return fail


def pack(dest,evidence):
    buf=io.BytesIO()
    payload=json.dumps(evidence,separators=(',',':'),allow_nan=False).encode()
    with tarfile.open(fileobj=buf,mode='w') as tar:
        info=tarfile.TarInfo('full_evidence.json');info.size=len(payload);info.mtime=0
        tar.addfile(info,io.BytesIO(payload))
    (dest/'evidence.tar.gz').write_bytes(gzip.compress(buf.getvalue(),mtime=0))


def run(cache,out):
    dest=Path(out);dest.mkdir(parents=True,exist_ok=True)
    rows,manifest=load_cached(cache)
    times=[r[0] for r in rows];periods=[('2023','2023-04-01','2024-01-01'),('2024_H1','2024-01-01','2024-07-01'),
                                      ('2024_H2','2024-07-01','2025-01-01'),('2025_2026','2025-01-01','2026-10-01')]
    report=dict(protocol_sha256=hashlib.sha256(Path('elite/PROTOCOL_V12_V14.md').read_bytes()).hexdigest(),
                code_sha256={n:hashlib.sha256(Path(n).read_bytes()).hexdigest() for n in ['elite/candidates_v12.py','elite/candidates_v8.py','elite/research_engine.py','elite/research_data.py','elite/research_run.py','elite/batch_v12.py']},
                dataset_bars=len(rows),data_manifest=manifest,phase='DEVELOPMENT_ONLY',candidates={},benchmarks={},
                challenge_status='LOCKED',paper_eligible=[])
    for label,a,b in periods:
        lo=bisect.bisect_left(times,timestamp(a));hi=bisect.bisect_left(times,timestamp(b))
        report['benchmarks'][label]=dict(cash=0,buy_hold_35pct=benchmark(rows[lo:hi],.35),buy_hold_100pct=benchmark(rows[lo:hi],1))
    evidence={}
    for name in ('v12','v13','v14'):
        sig=decisions(rows,name);pr={};ev={}
        for label,a,b in periods:
            lo=bisect.bisect_left(times,timestamp(a));hi=bisect.bisect_left(times,timestamp(b))
            pr[label],ev[label]=evaluate(rows,sig,lo,hi)
        continuous,ev['continuous']=evaluate(rows,sig,0,len(rows))
        failures=discovery_failures(pr,continuous)
        report['candidates'][name]=dict(periods=pr,continuous=continuous,discovery_failed_gates=failures)
        evidence[name]=ev
        print(name,json.dumps(dict(period_pnl={p:round(v['base']['net_pnl'],2) for p,v in pr.items()},
                                     continuous=continuous['base'],failed_gates=failures)),flush=True)
    survivors=[n for n,r in report['candidates'].items() if not r['discovery_failed_gates']]
    report['challenge_candidates']=survivors
    # Materialize discovery decision before accessing any challenge data.
    (dest/'summary.json').write_text(json.dumps(report,indent=2,allow_nan=False))
    pack(dest,evidence)
    if survivors:
        # Explicit later run required: permits auditing frozen discovery before
        # the 2022 challenge is opened; this is NOT a PAPER acceptance signal.
        report['challenge_status']='READY_TO_EVALUATE_FROZEN_SURVIVORS'
        (dest/'summary.json').write_text(json.dumps(report,indent=2,allow_nan=False))
    print('CHALLENGE CANDIDATES',survivors,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cache',required=True);p.add_argument('--out',required=True)
    args=p.parse_args();run(args.cache,args.out)
