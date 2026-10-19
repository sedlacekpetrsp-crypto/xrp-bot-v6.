import datetime,hashlib,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from research.candle_validation_20261019 import engine
from research.retest_cost_review_20261019.variant import cost_target
H=pathlib.Path(__file__).parent;p=json.loads((H/'protocol.json').read_text())
raw=pathlib.Path(sys.argv[1]).read_bytes();rows=json.loads(raw)
manifest=json.loads((H/'data_manifest.json').read_text());assert hashlib.sha256(raw).hexdigest()==manifest['sha256']
ms=lambda s:int(datetime.datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()*1000)
a,b=map(ms,p['evaluation']);signal,atr=engine.signals(rows,'breakout_retest',p)
original=engine.open_position;out={}
try:
 for name,opener in [('original',original),('net_target',cost_target)]:
  engine.open_position=opener;out[name]={}
  for label,m in [('base',1),('double_slippage',2)]:
   result,trades=engine.replay(rows,signal,atr,a,b,p,p['slippage_per_side']*m)
   result['gross_after_slippage']=sum(t['gross_pnl'] for t in trades)
   out[name][label]=result
finally:engine.open_position=original
v=out['net_target'];r=v['base'];g=p['gate']
out['checks']={'min_trades':r['trades']>=g['holdout_min_trades'],'profit_factor':(r['profit_factor'] or 0)>=g['holdout_profit_factor'],'positive_net':r['net_pnl']>0,'stress_positive':v['double_slippage']['net_pnl']>0,'drawdown':r['max_close_marked_drawdown_pct']<=g['max_marked_drawdown_pct'],'improves_original':r['net_pnl']>out['original']['base']['net_pnl']}
out['passes']=all(out['checks'].values());out['deployment_authorized_by_study']=False
(H/'results.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
