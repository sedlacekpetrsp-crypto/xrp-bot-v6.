"""Post-screen diagnostics; no parameter fitting or changes to frozen gates."""
import argparse,json,tarfile
from pathlib import Path
from elite.research_data import load_cached
from elite.research_engine import simulate
from elite.candidates_v34 import decisions
from elite.turnover_v34 import load_turnover
from elite.research_run import compact


def run(cache,out):
    dest=Path(out);summary=json.loads((dest/'summary.json').read_text())
    rows,manifest=load_cached(cache)
    turnover=load_turnover(cache,rows,manifest)
    with tarfile.open(dest/'evidence.tar.gz') as tar:
        evidence=json.load(tar.extractfile('full_evidence.json'))
    result={}
    for name in ('v34','v35'):
        sig=decisions(rows,turnover,name)
        free=simulate(rows,sig,fee=0,slip=0,half_spread=0)
        delayed=simulate(rows,{i+1:s for i,s in sig.items()})
        base=evidence[name]['continuous']['base']
        wins=sorted((t['pnl'] for t in base['trade_log'] if t['pnl']>0),reverse=True)
        result[name]=dict(zero_cost_counterfactual=compact(free),one_5m_bar_delayed_signals=compact(delayed),
                          largest_win=wins[0] if wins else 0,largest_three_wins=sum(wins[:3]),
                          pnl_minus_largest_win=base['net_pnl']-sum(wins[:1]),
                          pnl_minus_largest_three_wins=base['net_pnl']-sum(wins[:3]))
    report=dict(warning='Diagnostic scenarios only, not new strategies or acceptance gates. Zero costs change risk sizing and fills; winner subtraction is arithmetic, not a causal rerun.',results=result)
    (dest/'robustness.json').write_text(json.dumps(report,indent=2,allow_nan=False))
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cache',required=True);p.add_argument('--out',required=True)
    args=p.parse_args();run(args.cache,args.out)
