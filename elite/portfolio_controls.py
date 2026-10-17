"""Like-for-like standalone controls for the routed portfolio experiment."""
import argparse,json
from pathlib import Path
from elite.research_data import load_cached
from elite.research_engine import simulate
from elite.portfolio_v15 import streams
from elite.research_run import compact

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cache',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();rows,_=load_cached(a.cache);result={}
    for name,sig in streams(rows).items():
        result[name]=dict(base=compact(simulate(rows,sig)),stress=compact(simulate(rows,sig,fee=.002,slip=.0006,half_spread=.0002)))
    dest=Path(a.out);dest.mkdir(parents=True,exist_ok=True)
    (dest/'standalone_controls.json').write_text(json.dumps(result,indent=2,allow_nan=False))
    print(json.dumps(result,indent=2))
