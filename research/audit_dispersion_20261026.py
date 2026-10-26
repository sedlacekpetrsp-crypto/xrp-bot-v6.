import gzip,json,math,hashlib
from pathlib import Path
root=Path('research/cross_market_dispersion_20261026')
r=json.loads((root/'results.json').read_text())
checks={}
checks['228_verified_archives']=sum(len(x) for x in r['sources'].values())==228 and all(x['checksum_verified'] for xs in r['sources'].values() for x in xs)
for key in ('base','stress'):
 ts=json.loads(gzip.open(root/f'trades_{key}.json.gz','rt').read())
 equity=10000;previous=-1
 for t in ts:
  assert t['entry_timestamp']>=previous
  previous=t['exit_timestamp']
  gross=t['qty_long']*(t['fill_long']-t['entry_long'])+t['qty_short']*(t['entry_short']-t['fill_short'])
  assert math.isclose(t['pnl'],gross-t['fees']-t['borrow'],abs_tol=1e-8)
  assert math.isclose(t['equity_before'],equity,abs_tol=1e-8)
  assert math.isclose(t['qty_long']*t['entry_long'],equity*.1,abs_tol=1e-8)
  assert math.isclose(t['qty_short']*t['entry_short'],equity*.1,abs_tol=1e-8)
  equity+=t['pnl']
  assert math.isclose(t['equity'],equity,abs_tol=1e-8)
  assert t['fees']>=0 and t['borrow']>=0
 assert math.isclose(equity-10000,r['results'][key]['all']['net_pnl'],abs_tol=1e-7)
 checks[key+'_ledger_reconciled']=True
 checks[key+'_trade_count']=len(ts)
checks['files_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in root.glob('trades_*.json.gz')}
(root/'audit.json').write_text(json.dumps(checks,indent=2)+'\n')
print(json.dumps(checks,indent=2))
