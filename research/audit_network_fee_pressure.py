"""Independent fee-pressure ledger audit; no strategy import."""
import gzip,json,pathlib,sys
r=pathlib.Path(sys.argv[1]);res=json.loads((r/'results.json').read_text())
with gzip.open(r/'trades.json.gz','rt')as h:led=json.load(h)
n=0;fail=[]
def ck(x,m):
 global n;n+=1
 if not x:fail.append(m)
for key,ts in led.items():
 prev=None;fee=.0019 if key.endswith('_stress')else .00095
 for i,t in enumerate(ts):
  p=f'{key}[{i}]';ck(t['signal_timestamp']-t['metric_timestamp']==86400000,p+' metric lag');ck(t['entry_timestamp']-t['metric_timestamp']==172800000,p+' entry lag');ck(prev is None or t['entry_timestamp']>prev,p+' overlap');prev=t['exit_timestamp'];ck(t['leg_notional']<=t['entry_equity']*.2+1e-7,p+' cap');f=fee*t['qty']*(t['entry']+t['exit']);ck(abs(f-t['fees'])<1e-7,p+' fees');fill=t['qty']*(t['exit']-t['entry']);ck(abs(fill-t['fees']-t['pnl'])<1e-7,p+' pnl');ck(abs(t['gross']-fill-t['slippage_cost'])<1e-7,p+' slippage')
ck(res['historical_pass']==all(res['gates'].values()),'gates');ck(res['status']==('TEST NEDOKONCEN: independent forward PAPER evidence required'if res['historical_pass']else'NEPROSEL'),'status');out={'checks':n,'failures':fail,'passed':not fail};(r/'audit.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out));raise SystemExit(bool(fail))
