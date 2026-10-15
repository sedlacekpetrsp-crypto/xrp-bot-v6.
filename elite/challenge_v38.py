"""Single frozen survivor, reserved 2022 backward challenge; never live execution."""
import argparse,bisect,json,hashlib
from pathlib import Path
from elite.research_data import load_cached
from elite.cross_market_v18 import decisions,align
from elite.loss_overlay_v38 import LossOverlay
from elite.batch_v38 import evaluate,pack,benchmark
from elite.research_run import timestamp


def run(cache,out,discovery):
    dest=Path(out);dest.mkdir(parents=True,exist_ok=True)
    p=Path(discovery);d=json.loads(p.read_text())
    if d['candidates']['v38']['discovery_failed_gates'] or 'v38' not in d['challenge_candidates']:
        raise ValueError('V38 has not passed discovery')
    for f,sha in d['code_sha256'].items():
        if hashlib.sha256(Path(f).read_bytes()).hexdigest()!=sha:raise ValueError('frozen source mismatch: '+f)
    report=dict(candidate='v38',phase='RESERVED_2022_BACKWARD_CHALLENGE',paper_eligible=[],
                discovery_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),frozen_code_sha256=d['code_sha256'],
                protocol_sha256=hashlib.sha256(Path('elite/PROTOCOL_CHALLENGE_V38.md').read_bytes()).hexdigest())
    try:
        rows,xm=load_cached(cache,'2022-01','2022-12')
        btc,bm=load_cached(cache,'2022-01','2022-12',symbol='BTCUSDT');align(rows,btc)
    except Exception as exc:
        report.update(status='BLOCKED_DATA_INTEGRITY',error=str(exc))
        (dest/'summary.json').write_text(json.dumps(report,indent=2));raise
    # V38 never uses strict signals; exact frozen class and V18 base, no V39 test.
    router=LossOverlay(rows,decisions(rows,btc,'v18'),{},'v38');times=[r[0] for r in rows]
    periods={};ev={};bench={}
    for label,a,b in [('H1','2022-01-01','2022-07-01'),('H2','2022-07-01','2023-01-01')]:
        lo=bisect.bisect_left(times,timestamp(a));hi=bisect.bisect_left(times,timestamp(b))
        periods[label],ev[label]=evaluate(rows,router,lo,hi)
        bench[label]=dict(cash=0,buy_hold_35pct=benchmark(rows[lo:hi],.35),buy_hold_100pct=benchmark(rows[lo:hi],1))
    continuous,ev['continuous']=evaluate(rows,router,0,len(rows));fail=[]
    for label,x in periods.items():
        if x['base']['net_pnl']<=0:fail.append(label+'_nonpositive_net')
        if x['stress']['net_pnl']<=0:fail.append(label+'_nonpositive_stress')
        if x['base']['profit_factor'] is None or x['base']['profit_factor']<1.2:fail.append(label+'_PF_below_1.2')
    if sum(x['base']['trades'] for x in periods.values())<30:fail.append('fewer_than_30_combined_trades')
    for label,x in {**periods,'continuous':continuous}.items():
        if x['base']['close_mtm_drawdown_pct']>10:fail.append(label+'_close_DD_above_10')
        if x['base']['intrabar_drawdown_bound_pct']>12:fail.append(label+'_intrabar_above_12')
    ci=continuous['mean_daily_pnl_95pct_block_bootstrap']
    if ci[0] is None or ci[0]<=0:fail.append('uncertain_continuous_daily_mean')
    report.update(status='FAIL' if fail else 'PASS_REQUIRES_PROSPECTIVE_VALIDATION',failed_gates=fail,
                  data_manifest=dict(XRPUSDT=xm,BTCUSDT=bm),dataset_bars=len(rows),periods=periods,
                  continuous=continuous,benchmarks=bench)
    pack(dest,{'v38':ev});(dest/'summary.json').write_text(json.dumps(report,indent=2,allow_nan=False))
    print(json.dumps(dict(status=report['status'],failed_gates=fail,periods={k:v['base'] for k,v in periods.items()},continuous=continuous['base'])),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cache',required=True);p.add_argument('--out',required=True)
    p.add_argument('--discovery',default='elite/results/20261015_v38/summary.json')
    a=p.parse_args();run(a.cache,a.out,a.discovery)
