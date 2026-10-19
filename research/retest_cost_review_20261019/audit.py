"""Descriptive cohorts of already-observed development trades, never a holdout."""
import collections,gzip,json,pathlib,sys
root=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(root))
from research.candle_validation_20261019.engine import features
h=pathlib.Path(__file__).parent;p=json.loads((root/'research/candle_validation_20261019/protocol.json').read_text())
rows=json.loads(pathlib.Path(sys.argv[1]).read_text());f=features(rows);index={int(r[0]):i for i,r in enumerate(rows)}
trades=json.loads(gzip.decompress((root/'research/candle_validation_20261019/development_trades.json.gz').read_bytes()))['breakout_retest']['base']
groups=collections.defaultdict(list)
for t in trades:
 i=index[t['opened_at']]-1;c=f['close'][i];atr=f['atr'][i]
 cost=2*(p['fee_per_side']+p['slippage_per_side']);coverage=atr*p['stop_atr']*p['gross_reward_multiple']/c/cost
 # Efficiency uses only the preceding 20 closed candles, not future returns.
 path=sum(abs(f['close'][j]-f['close'][j-1]) for j in range(i-19,i+1))
 efficiency=abs(c-f['close'][i-20])/path if path else 0
 for key in ['ALL','LONG' if t['side']==1 else 'SHORT', 'target/cost < 3' if coverage<3 else 'target/cost >= 3','efficiency < .3' if efficiency<.3 else 'efficiency >= .3']:
  groups[key].append(t)
out={k:dict(trades=len(v),net=sum(t['net_pnl'] for t in v),gross_after_slippage=sum(t['gross_pnl'] for t in v),fees=sum(t['fees'] for t in v),wins=sum(t['net_pnl']>0 for t in v)) for k,v in groups.items()}
(h/'development_cohorts.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
