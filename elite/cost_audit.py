"""Fixed-cost sensitivity of frozen strategies. Never changes acceptance or deploys."""
import argparse,bisect,hashlib,json,math
from pathlib import Path
from elite.research_data import load_cached
from elite.cross_market_v18 import align,decisions as cross_decisions
from elite.session_v49 import decisions as session_decisions
from elite.research_engine import simulate
from elite.research_run import compact,bootstrap,timestamp
from elite.batch_v38 import pack
SCALES=(0.,.25,.5,.75,1.,2.)
PERIODS=(('2023','2023-04-01','2024-01-01'),('2024_H1','2024-01-01','2024-07-01'),
         ('2024_H2','2024-07-01','2025-01-01'),('2025_2026','2025-01-01','2026-10-01'))


def run(cache,out):
    dest=Path(out);dest.mkdir(parents=True,exist_ok=True)
    rows,xmanifest=load_cached(cache);btc,bmanifest=load_cached(cache,symbol='BTCUSDT');align(rows,btc)
    times=[r[0] for r in rows]
    slices=[(n,bisect.bisect_left(times,timestamp(a)),bisect.bisect_left(times,timestamp(b))) for n,a,b in PERIODS]
    slices.append(('continuous',0,len(rows)))
    sources=['elite/cost_audit.py','elite/cross_market_v18.py','elite/session_v49.py','elite/research_engine.py','elite/research_data.py','elite/research_run.py','elite/batch_v38.py']
    report=dict(phase='COST_DIAGNOSTICS_NOT_SELECTION',paper_eligible=[],
                code_sha256={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in sources},
                protocol_sha256=hashlib.sha256(Path('elite/PROTOCOL_COST_AUDIT.md').read_bytes()).hexdigest(),
                data_manifest={'XRPUSDT':xmanifest,'BTCUSDT':bmanifest},candidates={},ledgers_reconciled=0)
    evidence={}
    for name in ('v18','v49'):
        sig=cross_decisions(rows,btc,name) if name=='v18' else session_decisions(rows,name)
        report['candidates'][name]={};evidence[name]={}
        for scale in SCALES:
            key=str(scale);summary={};full={}
            for label,lo,hi in slices:
                r=simulate(rows,sig,lo,hi,fee=.001*scale,slip=.0003*scale,half_spread=.0001*scale)
                trades=r['trade_log']
                assert math.isclose(sum(t['pnl'] for t in trades),r['net_pnl'],abs_tol=1e-7)
                assert all(a['exit_index']<b['entry_index'] for a,b in zip(trades,trades[1:]))
                report['ledgers_reconciled']+=1
                summary[label]=compact(r);full[label]=r
            summary['positive_blocks']=sum(summary[n]['net_pnl']>0 for n,_,_ in PERIODS)
            summary['continuous_daily_mean_95pct']=bootstrap(full['continuous']['daily_equity'])
            report['candidates'][name][key]=summary;evidence[name][key]=full
            print(name,key,json.dumps({'net':summary['continuous']['net_pnl'],'dd':summary['continuous']['close_mtm_drawdown_pct'],
                  'trades':summary['continuous']['trades'],'positive_blocks':summary['positive_blocks']}),flush=True)
    (dest/'summary.json').write_text(json.dumps(report,indent=2,allow_nan=False));pack(dest,evidence)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cache',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();run(a.cache,a.out)
