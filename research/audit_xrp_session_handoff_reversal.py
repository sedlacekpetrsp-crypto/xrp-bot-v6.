import csv,datetime as dt,gzip,hashlib,io,json,pathlib,sys,zipfile
STEP=3_600_000; UTC=dt.timezone.utc
def close(a,b,t=1e-8): return abs(a-b)<=t*max(1,abs(a),abs(b))
def main():
 cache,dest=map(pathlib.Path,sys.argv[1:3]); r=json.loads((dest/'results.json').read_text()); checks=[]
 def check(n,v): checks.append(dict(name=n,passed=bool(v)))
 raw=[]
 for x in r['manifest']:
  payload=(cache/x['cache_file']).read_bytes(); check('hash_'+x['cache_file'],hashlib.sha256(payload).hexdigest()==x['sha256'] and len(payload)==x['bytes']); z=zipfile.ZipFile(io.BytesIO(payload)); rows=list(csv.reader(io.TextIOWrapper(z.open(x['archive_member']))));
  if rows and not rows[0][0].isdigit(): rows=rows[1:]
  check('rows_'+x['cache_file'],len(rows)==x['rows'])
  for q in rows:
   ts=int(q[0]); ts=ts//1000 if ts>10**14 else ts; raw.append(dict(timestamp=ts,open=float(q[1]),high=float(q[2]),low=float(q[3]),close=float(q[4])))
 by={}
 for b in raw: check('duplicate_'+str(b['timestamp']),b['timestamp'] not in by or by[b['timestamp']]==b); by[b['timestamp']]=b
 bars=[by[t] for t in sorted(by)]; check('quality_counts',len(raw)==r['data_quality']['raw_rows'] and len(bars)==r['data_quality']['unique_rows']); index={b['timestamp']:i for i,b in enumerate(bars)}; signals={}
 for b in bars:
  d=dt.datetime.fromtimestamp(b['timestamp']/1000,UTC)
  if d.hour: continue
  ss=[by.get(b['timestamp']+h*STEP) for h in range(8)]
  if any(x is None for x in ss): continue
  ret=ss[-1]['close']/ss[0]['open']-1
  if ret<=-.015 and b['timestamp']+8*STEP in by: signals[b['timestamp']+8*STEP]=dict(session_start=b['timestamp'],session_end=b['timestamp']+8*STEP,session_open=ss[0]['open'],session_close=ss[-1]['close'],session_return=ret)
 check('signals_total',len(signals)==r['signals_total'])
 with gzip.open(dest/'trades.json.gz','rt') as h: ledgers=json.load(h)
 tc=0
 for key,trades in ledgers.items():
  fee=.0019 if key.endswith('_stress') else .00095; slip=.0004 if key.endswith('_stress') else .0002; eqs=[10_000.]
  for a,b in zip(trades,trades[1:]): check('nonoverlap_'+key+str(a['entry_timestamp']),a['exit_timestamp']<b['entry_timestamp'])
  for t in trades:
   tc+=1; s=signals[t['entry_timestamp']]; check('signal_'+str(tc),all(close(t[k],v) if isinstance(v,float) else t[k]==v for k,v in s.items())); i=index[t['entry_timestamp']]; check('hour_'+str(tc),dt.datetime.fromtimestamp(t['entry_timestamp']/1000,UTC).hour==8 and t['session_end']==t['entry_timestamp']); av=sum(max(bars[j]['high']-bars[j]['low'],abs(bars[j]['high']-bars[j-1]['close']),abs(bars[j]['low']-bars[j-1]['close'])) for j in range(i-24,i))/24; check('atr_entry_'+str(tc),close(t['atr'],av) and close(t['entry'],bars[i]['open']*(1+slip))); check('brackets_'+str(tc),close(t['stop'],t['entry']-1.5*av) and close(t['target'],t['entry']+2*(t['entry']-t['stop']))); check('limits_'+str(tc),t['leg_notional']<=t['entry_equity']*.2+1e-7 and t['qty']*(t['entry']-t['stop'])<=t['entry_equity']*.005+1e-7)
   j=index[t['exit_timestamp']]; eb=bars[j]; expected=eb['open'] if t['reason']=='GAP_STOP' else t['stop'] if t['reason']=='STOP' else t['target'] if t['reason']=='TARGET' else eb['close']; check('exit_'+str(tc),close(t['raw_exit'],expected) and close(t['exit'],expected*(1-slip))); fees=t['qty']*t['entry']*fee+t['qty']*t['exit']*fee; pnl=t['qty']*(t['exit']-t['entry'])-fees; check('cost_'+str(tc),close(t['fees'],fees) and close(t['pnl'],pnl) and close(t['equity'],t['entry_equity']+pnl)); entry_fee=t['qty']*t['entry']*fee; mend=j+1 if t['reason']=='FOLD_END' else j
   for k in range(i,mend):
    mark=bars[k]['low']*(1-slip); eqs.append(t['entry_equity']+t['qty']*(mark-t['entry'])-entry_fee-t['qty']*mark*fee)
   eqs.append(t['equity'])
  m=r['runs'][key]; w=sum(max(0,x['pnl']) for x in trades); l=-sum(min(0,x['pnl']) for x in trades); net=sum(x['pnl'] for x in trades); peak=10_000.; dd=0
  for e in eqs: peak=max(peak,e); dd=max(dd,(peak-e)/peak*100)
  check('report_'+key,m['trades']==len(trades) and close(m['net_pnl'],net) and close(m['gross_profit'],w) and close(m['gross_loss'],l) and close(m['max_drawdown_pct'],dd) and (m['profit_factor'] is None if not l else close(m['profit_factor'],w/l)))
 passed=all(x['passed'] for x in checks); r['gates']['audit']=passed; hist=all(v for k,v in r['gates'].items() if k!='forward_paper'); r['status']='TEST NEDOKONCEN: forward PAPER required' if hist else 'NEPROSEL'; (dest/'results.json').write_text(json.dumps(r,indent=2,allow_nan=False)+'\n'); audit=dict(strategy=r['strategy'],passed=passed,checks=len(checks),trade_checks=tc,failures=[x['name'] for x in checks if not x['passed']]); (dest/'audit.json').write_text(json.dumps(audit,indent=2)+'\n'); print(audit,flush=True)
 if not passed: raise SystemExit(1)
if __name__=='__main__': main()
