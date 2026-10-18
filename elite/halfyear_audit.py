"""Frozen equal-duration diagnostic; never changes candidate gates or parameters."""
import argparse,bisect,json,hashlib
from pathlib import Path
from elite.research_data import load_cached
from elite.research_engine import simulate,decisions as original
from elite.cross_market_v18 import decisions as cross
from elite.exit_v21 import decisions as exits
from elite.flow_v28 import load_flow
from elite.candidates_v28 import decisions as flow_decisions
from elite.selector_v30 import prepare
from elite.research_run import compact,timestamp
from elite.batch_v24 import pack

BOUNDARIES=('2023-04-01','2023-10-01','2024-04-01','2024-10-01',
            '2025-04-01','2025-10-01','2026-04-01','2026-10-01')
NAMES=('v5','v18','v22','v28','v30','v31')

def run(cache,out):
    dest=Path(out);dest.mkdir(parents=True,exist_ok=True)
    rows,manifest=load_cached(cache);btc,bm=load_cached(cache,symbol='BTCUSDT')
    flows=load_flow(cache,rows,manifest);routers,records=prepare(rows,btc)
    streams={'v5':original(rows,'v5'),'v18':cross(rows,btc,'v18'),
             'v22':exits(rows,btc,'v22'),'v28':flow_decisions(rows,flows,'v28'),**routers}
    files=['elite/halfyear_audit.py','elite/research_engine.py','elite/research_data.py',
           'elite/cross_market_v18.py','elite/exit_v21.py','elite/candidates_v28.py',
           'elite/flow_v28.py','elite/selector_v30.py','elite/portfolio_v15.py',
           'elite/candidates_v8.py','elite/candidates_v24.py','elite/batch_v24.py',
           'elite/research_run.py','elite/PROTOCOL_HALFYEAR_AUDIT.md']
    report=dict(purpose='DEVELOPMENT_DIAGNOSTIC_ONLY_NO_PROMOTION',
                code_sha256={f:hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in files},
                data_manifest=dict(XRPUSDT=manifest,BTCUSDT=bm),candidates={},paper_eligible=[])
    times=[r[0] for r in rows];evidence={}
    for n in NAMES:
        blocks={};ev={}
        for a,b in zip(BOUNDARIES,BOUNDARIES[1:]):
            lo=bisect.bisect_left(times,timestamp(a));hi=bisect.bisect_left(times,timestamp(b))
            base=simulate(rows,streams[n],lo,hi)
            stress=simulate(rows,streams[n],lo,hi,fee=.002,slip=.0006,half_spread=.0002)
            blocks[a]=dict(end_exclusive=b,base=compact(base),stress=compact(stress),
                           selector_initialization=(n in ('v30','v31') and a=='2023-04-01'))
            ev[a]=dict(base=base,stress=stress)
        common=[v for a,v in blocks.items() if a!='2023-04-01']
        report['candidates'][n]=dict(blocks=blocks,common_six=dict(
            positive_base=sum(v['base']['net_pnl']>0 for v in common),
            positive_stress=sum(v['stress']['net_pnl']>0 for v in common),
            worst_base_pct=min(v['base']['return_pct'] for v in common),
            best_base_pct=max(v['base']['return_pct'] for v in common),
            worst_close_drawdown_pct=max(v['base']['close_mtm_drawdown_pct'] for v in common)))
        evidence[n]=ev
        print(n,json.dumps(dict(halfyear_pnl={a:round(v['base']['net_pnl'],2) for a,v in blocks.items()},
                               common_six=report['candidates'][n]['common_six'])),flush=True)
    pack(dest,evidence)
    (dest/'summary.json').write_text(json.dumps(report,indent=2,allow_nan=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cache',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();run(a.cache,a.out)
