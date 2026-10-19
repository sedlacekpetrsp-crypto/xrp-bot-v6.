import datetime,gzip,hashlib,json,pathlib,sys
from engine import signals,replay
HERE=pathlib.Path(__file__).parent
p=json.loads((HERE/'protocol.json').read_text());raw=pathlib.Path(sys.argv[1]).read_bytes()
if hashlib.sha256(raw).hexdigest()!=json.loads((HERE/'data_manifest.json').read_text())['sha256']:raise ValueError('Data hash mismatch')
rows=json.loads(raw);ms=lambda s:int(datetime.datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()*1000)
period=sys.argv[2]
if period not in ('development','holdout'):raise ValueError('Choose a frozen period')
start,end=map(ms,p[period]);result=[];all_trades={}
for name in p['strategies']:
 sig,atr=signals(rows,name,p);r,t=replay(rows,sig,atr,start,end,p,p['slippage_per_side']);stress,st=replay(rows,sig,atr,start,end,p,p['slippage_per_side']*2)
 g=p['gate'];passed=r['trades']>=g['holdout_min_trades'] and r['net_pnl']>0 and (r['profit_factor'] or 0)>=g['holdout_profit_factor'] and stress['net_pnl']>0 and r['max_close_marked_drawdown_pct']<=g['max_marked_drawdown_pct']
 result.append(dict(strategy=name,period=period,base=r,double_slippage=stress,numeric_gate=passed));all_trades[name]=dict(base=t,stress=st)
 print(json.dumps(result[-1]),flush=True)
(HERE/(period+'_results.json')).write_text(json.dumps(result,indent=2))
(HERE/(period+'_trades.json.gz')).write_bytes(gzip.compress(json.dumps(all_trades,separators=(',',':')).encode(),mtime=0))
