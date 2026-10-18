import csv,json
from collections import Counter
from elite.evaluate import evaluate
from elite.backtest import backtest
from elite.research_engine import decisions,simulate
import argparse
p=argparse.ArgumentParser(); p.add_argument('--csv',required=True); p.add_argument('--output',required=True)
args=p.parse_args()
with open(args.csv) as f:
 rows=[(int(r['timestamp_ms']),*[float(r[x]) for x in ('open','high','low','close')]) for r in csv.DictReader(f)]
original=evaluate(rows,'v4')
print('Original',json.dumps(original),flush=True)
signals=decisions(rows,'v4'); n=len(rows);cuts=[0,int(n*.6),int(n*.8),n];detail={}
for j,name in enumerate(('development','validation','reused_holdout')):
 lo,hi=cuts[j:j+2]; segment=[tuple(r[1:]) for r in rows[max(0,lo-101):hi]]
 legacy=backtest(segment,strategy='v4'); zero=backtest(segment,strategy='v4',fee_rate=0,slippage_rate=0)
 audited=simulate(rows,signals,lo,hi,fee=.0005,slip=.0002,half_spread=0)
 detail[name]={'original_exit_reasons':dict(Counter(t.reason for t in legacy['trade_log'])),
               'original_zero_cost_pnl':zero['net_pnl'],'audited_engine':{k:v for k,v in audited.items() if k not in ('trade_log','daily_equity')}}
result={'original_reproduced':original,'diagnostics':detail,'note':'Audited engine includes costs in risk sizing; original kept for exact reproduction. Not an independent holdout.'}
open(args.output,'w').write(json.dumps(result,indent=2))
print(json.dumps(detail),flush=True)
