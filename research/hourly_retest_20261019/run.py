import datetime,hashlib,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from research.candle_validation_20261019.engine import signals,replay
from research.hourly_retest_20261019.strategy import hourly_signals
H=pathlib.Path(__file__).parent;p=json.loads((H/'protocol.json').read_text());ms=lambda s:int(datetime.datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()*1000)
merged={};inputs=[]
for arg in sys.argv[1:]:
 raw=pathlib.Path(arg).read_bytes();data=json.loads(raw);inputs.append(dict(sha256=hashlib.sha256(raw).hexdigest(),bars=len(data)))
 for r in data:
  t=int(r[0])
  if t in merged and merged[t]!=r:raise ValueError('Conflicting input overlap')
  merged[t]=r
rows=[merged[k] for k in sorted(merged)]
assert rows[0][0]==ms(p['data_start']) and rows[-1][6]+1==ms(p['periods']['seen_recent'][1])
assert all(r[0]==rows[0][0]+i*900000 and r[6]==r[0]+899999 for i,r in enumerate(rows))
variants={'reference_15m':signals(rows,'breakout_retest',p),'candidate_1h':hourly_signals(rows,p)}
out={'inputs':inputs,'periods':{}}
# Now-seen periods first; no adaptation before opening new older period.
for period in ('seen_older','seen_recent','new_older'):
 a,b=map(ms,p['periods'][period]);out['periods'][period]={}
 for name,(sig,atr) in variants.items():
  out['periods'][period][name]={}
  for label,m in [('base',1),('double_slippage',2)]:
   result,trades=replay(rows,sig,atr,a,b,p,p['slippage_per_side']*m)
   result['gross_after_slippage']=sum(t['gross_pnl'] for t in trades)
   result['long_trades']=sum(t['side']==1 for t in trades)
   result['short_trades']=sum(t['side']==-1 for t in trades)
   out['periods'][period][name][label]=result
checks={};g=p['gate']
for period,d in out['periods'].items():
 v=d['candidate_1h'];r=v['base'];checks[period]={'trades':r['trades']>=g['holdout_min_trades'],'profit_factor':(r['profit_factor'] or 0)>=g['holdout_profit_factor'],'net':r['net_pnl']>0,'stress_net':v['double_slippage']['net_pnl']>0,'drawdown':r['max_close_marked_drawdown_pct']<=g['max_marked_drawdown_pct']}
out['checks']=checks;out['total_improvement']=sum(d['candidate_1h']['base']['net_pnl']-d['reference_15m']['base']['net_pnl'] for d in out['periods'].values())
out['passes']=all(all(c.values()) for c in checks.values()) and out['total_improvement']>0
out['deployment_authorized_by_study']=False
(H/'results.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
