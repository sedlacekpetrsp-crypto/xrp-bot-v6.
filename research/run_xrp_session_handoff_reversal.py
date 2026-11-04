import concurrent.futures,csv,datetime as dt,gzip,hashlib,io,json,pathlib,sys,urllib.request,zipfile
from dataclasses import replace
from research.xrp_session_handoff_reversal_v1 import Config,STEP,backtest,make_signals,validate
UTC=dt.timezone.utc
MONTHS=[(y,m) for y in range(2021,2027) for m in range(1,13) if (y,m)<(2026,10)]
def stamp(y,m=1,d=1): return int(dt.datetime(y,m,d,tzinfo=UTC).timestamp()*1000)
def fetch(job):
 y,m,cache=job; name=f'XRPUSDT-1h-{y}-{m:02d}.zip'; url=f'https://data.binance.vision/data/spot/monthly/klines/XRPUSDT/1h/{name}'; path=cache/name
 if not path.exists():
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'xrp-research/1.0'}),timeout=120) as r: path.write_bytes(r.read())
 raw=path.read_bytes(); z=zipfile.ZipFile(io.BytesIO(raw)); names=z.namelist()
 if len(names)!=1: raise ValueError('zip members')
 rows=list(csv.reader(io.TextIOWrapper(z.open(names[0]))));
 if rows and not rows[0][0].isdigit(): rows=rows[1:]
 out=[]
 for r in rows:
  ts=int(r[0]); ts=ts//1000 if ts>10**14 else ts; out.append(dict(timestamp=ts,open=float(r[1]),high=float(r[2]),low=float(r[3]),close=float(r[4])))
 return out,dict(kind='binance_XRPUSDT_1h',url=url,cache_file=name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),archive_member=names[0],rows=len(out))
def metrics(trades,curve,initial=10_000.):
 w=sum(max(0,x['pnl']) for x in trades); l=-sum(min(0,x['pnl']) for x in trades); net=sum(x['pnl'] for x in trades); peak=initial; dd=0
 for p in curve: peak=max(peak,p['equity']); dd=max(dd,(peak-p['equity'])/peak*100)
 return dict(trades=len(trades),net_pnl=net,net_return_pct=net/initial*100,profit_factor=w/l if l else None,expectancy=net/len(trades) if trades else None,max_drawdown_pct=dd,fees=sum(x['fees'] for x in trades),slippage_cost=sum(x['slippage_cost'] for x in trades),gross_profit=w,gross_loss=l)
def main():
 cache,dest=map(pathlib.Path,sys.argv[1:3]); cache.mkdir(parents=True,exist_ok=True); dest.mkdir(parents=True,exist_ok=True)
 with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool: chunks=list(pool.map(fetch,[(y,m,cache) for y,m in MONTHS]))
 raw=[b for rows,_ in chunks for b in rows]; by={}
 for b in raw:
  if b['timestamp'] in by and by[b['timestamp']]!=b: raise ValueError('conflicting duplicate')
  by[b['timestamp']]=b
 bars=[by[t] for t in sorted(by)]; validate(bars); signals=make_signals(bars)
 gaps=[dict(after=a['timestamp'],before=b['timestamp'],missing_hours=(b['timestamp']-a['timestamp'])//STEP-1) for a,b in zip(bars,bars[1:]) if b['timestamp']-a['timestamp']!=STEP]
 folds=[('2021_control',stamp(2021),stamp(2022))]+[(str(y),stamp(y),stamp(y+1) if y<2026 else stamp(2026,10)) for y in range(2022,2027)]+[('continuous_oos',stamp(2022),stamp(2026,10))]
 runs={}; ledgers={}
 for name,start,end in folds:
  for label,mult in (('base',1),('stress',2)):
   c=replace(Config(),fee=Config().fee*mult,slippage=Config().slippage*mult); trades,curve=backtest(bars,signals,start,end,c); key=name+'_'+label; runs[key]=metrics(trades,curve); ledgers[key]=trades; print(key,runs[key],flush=True)
 years=[str(y) for y in range(2022,2027)]; base=[t for y in years for t in ledgers[y+'_base']]; stress=[t for y in years for t in ledgers[y+'_stress']]; agg=metrics(base,[]); aggs=metrics(stress,[]); agg['max_drawdown_pct']=None; aggs['max_drawdown_pct']=None
 byy={y:runs[y+'_base']['net_pnl'] for y in years}; byys={y:runs[y+'_stress']['net_pnl'] for y in years}; monthly={}
 for t in base:
  k=dt.datetime.fromtimestamp(t['exit_timestamp']/1000,UTC).strftime('%Y-%m'); monthly[k]=monthly.get(k,0)+t['pnl']
 positive=sum(max(0,x) for x in monthly.values()); conc=max((max(0,x)/positive for x in monthly.values()),default=1.)
 gates=dict(sample=agg['trades']>=100,base_net=agg['net_pnl']>0,base_expectancy=(agg['expectancy'] or 0)>0,base_pf=(agg['profit_factor'] or 0)>1.20,stress_net=aggs['net_pnl']>0,stress_expectancy=(aggs['expectancy'] or 0)>0,stress_pf=(aggs['profit_factor'] or 0)>1.05,four_years=sum(x>0 for x in byy.values())>=4,four_years_stress=sum(x>0 for x in byys.values())>=4,final_year=byy['2026']>0 and byys['2026']>0,drawdown=max(runs['continuous_oos_base']['max_drawdown_pct'],runs['continuous_oos_stress']['max_drawdown_pct'])<=10,concentration=agg['net_pnl']>0 and positive>0 and conc<=.25,audit=False,forward_paper=False)
 historical=all(v for k,v in gates.items() if k not in ('audit','forward_paper')); protocol=pathlib.Path('research/xrp_session_handoff_reversal_protocol_20261104.md')
 result=dict(strategy='XRP_ASIA_EUROPE_HANDOFF_REVERSAL_V1',status='TEST NEDOKONCEN: audit and forward PAPER required' if historical else 'NEPROSEL',protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),manifest=[x for _,x in chunks],data_quality=dict(raw_rows=len(raw),unique_rows=len(bars),duplicates=len(raw)-len(bars),start=bars[0]['timestamp'],end=bars[-1]['timestamp'],gaps=gaps),signals_total=len(signals),runs=runs,aggregate_oos=agg,aggregate_stress=aggs,by_year=byy,stress_by_year=byys,monthly_base=monthly,positive_month_profit_concentration=conc,gates=gates,historical_pass_before_audit=historical,limitations=['Previously inspected years are exploratory, not untouched validation.','Exchange archive data can be corrected by its publisher.','Hourly OHLC cannot reconstruct tick ordering; fixed conservative rules apply.','Local SHA256 values are provenance hashes, not publisher signatures.','No independent forward PAPER evidence exists.'])
 (dest/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');
 with gzip.open(dest/'trades.json.gz','wt') as h: json.dump(ledgers,h)
 print(result['status'],gates,flush=True)
if __name__=='__main__': main()
