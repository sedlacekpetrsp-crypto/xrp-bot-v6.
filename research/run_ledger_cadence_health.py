import csv,datetime as dt,gzip,hashlib,io,json,pathlib,sys,urllib.request,zipfile
from dataclasses import replace
from research.ledger_cadence_health_v1 import Config,DAY,backtest,make_signals,validate_prices
UTC=dt.timezone.utc;MONTHS=[(y,m) for y in range(2020,2027) for m in range(1,13) if (y,m)<(2026,10)]
URL='https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?assets=xrp&metrics=BlkCnt&frequency=1d&page_size=10000'
def get(url,p):
 if not p.exists():
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'xrp-research/1.0'}),timeout=120) as r:p.write_bytes(r.read())
 return p.read_bytes()
def stamp(y,m=1):return int(dt.datetime(y,m,1,tzinfo=UTC).timestamp()*1000)
def metric(cache):
 p=get(URL,cache/'cm-xrp-blkcnt.json');raw=json.loads(p)['data'];rows=[dict(timestamp=int(dt.datetime.fromisoformat(x['time'].replace('Z','+00:00')).timestamp()*1000),block_count=float(x['BlkCnt'])) for x in raw]
 return rows,dict(kind='coinmetrics_xrp_BlkCnt',url=URL,sha256=hashlib.sha256(p).hexdigest(),bytes=len(p),rows=len(raw))
def prices(cache):
 out=[];man=[]
 for y,m in MONTHS:
  n=f'XRPUSDT-1d-{y}-{m:02d}.zip';u=f'https://data.binance.vision/data/spot/monthly/klines/XRPUSDT/1d/{n}';p=get(u,cache/n)
  with zipfile.ZipFile(io.BytesIO(p)) as z:raw=list(csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]))))
  rows=[]
  for x in raw:
   if x[0].lower().startswith('open'):continue
   t=int(x[0]);t=t//1000 if t>10**14 else t;rows.append(dict(timestamp=t,open=float(x[1]),high=float(x[2]),low=float(x[3]),close=float(x[4])))
  out+=rows;man.append(dict(kind='binance_XRPUSDT_1d',url=u,sha256=hashlib.sha256(p).hexdigest(),bytes=len(p),rows=len(rows)))
 return out,man
def uniq(rows,name):
 d={};dups=0
 for x in rows:
  if x['timestamp'] in d:
   if d[x['timestamp']]!=x:raise ValueError(name+' conflict')
   dups+=1
  d[x['timestamp']]=x
 return [d[t] for t in sorted(d)],dups
def metrics(t,c,initial=10000):
 g=sum(max(0,x['pnl']) for x in t);l=-sum(min(0,x['pnl']) for x in t);n=sum(x['pnl'] for x in t);peak=initial;dd=0
 for x in c:peak=max(peak,x['equity']);dd=max(dd,(peak-x['equity'])/peak*100)
 return dict(trades=len(t),net_pnl=n,net_return_pct=n/initial*100,profit_factor=g/l if l else None,expectancy=n/len(t) if t else None,max_drawdown_pct=dd,fees=sum(x['fees'] for x in t),slippage_cost=sum(x['slippage_cost'] for x in t))
def main():
 cache=pathlib.Path(sys.argv[1]);cache.mkdir(parents=True,exist_ok=True);dest=pathlib.Path(sys.argv[2]);dest.mkdir(parents=True,exist_ok=True);mr,mm=metric(cache);pr,pm=prices(cache);mr,mdup=uniq(mr,'metric');rows,pdup=uniq(pr,'price');validate_prices(rows)
 signals=make_signals(mr)
 for x in rows:
  if x['timestamp'] in signals:x['cadence_signal']=signals[x['timestamp']]
 gaps=[dict(after=a['timestamp'],before=b['timestamp'],missing_days=(b['timestamp']-a['timestamp'])//DAY-1) for a,b in zip(rows,rows[1:]) if b['timestamp']-a['timestamp']!=DAY]
 folds=[('2020_2021_control',stamp(2020),stamp(2022))]+[(str(y),stamp(y),stamp(y+1) if y<2026 else stamp(2026,10)) for y in range(2022,2027)]+[('continuous_oos',stamp(2022),stamp(2026,10))];runs={};ledgers={}
 for name,start,end in folds:
  for label,mul in (('base',1),('stress',2)):
   c=Config();c=replace(c,fee=c.fee*mul,slippage=c.slippage*mul);t,curve=backtest(rows,start,end,c);k=f'{name}_{label}';ledgers[k]=t;runs[k]=metrics(t,curve);print(k,runs[k])
 years=[str(y) for y in range(2022,2027)];base=[x for y in years for x in ledgers[y+'_base']];stress=[x for y in years for x in ledgers[y+'_stress']];agg=metrics(base,[{'equity':10000},{'equity':10000+sum(x['pnl'] for x in base)}]);aggs=metrics(stress,[{'equity':10000},{'equity':10000+sum(x['pnl'] for x in stress)}]);agg['max_drawdown_pct']=None;aggs['max_drawdown_pct']=None
 by={y:runs[y+'_base']['net_pnl'] for y in years};bys={y:runs[y+'_stress']['net_pnl'] for y in years};monthly={}
 for x in base:
  k=dt.datetime.fromtimestamp(x['exit_timestamp']/1000,UTC).strftime('%Y-%m');monthly[k]=monthly.get(k,0)+x['pnl']
 pos=sum(max(0,v) for v in monthly.values());gates=dict(sample=agg['trades']>=150,base_net=agg['net_pnl']>0,base_expectancy=(agg['expectancy'] or 0)>0,base_pf=(agg['profit_factor'] or 0)>1.2,stress_net=aggs['net_pnl']>0,stress_expectancy=(aggs['expectancy'] or 0)>0,stress_pf=(aggs['profit_factor'] or 0)>1.05,four_years=sum(v>0 for v in by.values())>=4,four_years_stress=sum(v>0 for v in bys.values())>=4,final_year=by['2026']>0 and bys['2026']>0,drawdown=max(runs['continuous_oos_base']['max_drawdown_pct'],runs['continuous_oos_stress']['max_drawdown_pct'])<=10,concentration=agg['net_pnl']>0 and pos>0 and max(monthly.values(),default=0)<=.25*pos,audit=False,forward_paper=False)
 historical=all(v for k,v in gates.items() if k not in ('audit','forward_paper'));proto=pathlib.Path('research/ledger_cadence_health_protocol_20261029.md');result=dict(strategy='XRP_LEDGER_CADENCE_HEALTH_V1',status='TEST NEDOKONCEN: audit and forward PAPER required' if historical else 'NEPROSEL',protocol_sha256=hashlib.sha256(proto.read_bytes()).hexdigest(),manifest=[mm]+pm,data_quality=dict(metric_rows=len(mr),metric_duplicates=mdup,metric_start=mr[0]['timestamp'],metric_end=mr[-1]['timestamp'],price_rows=len(rows),price_duplicates=pdup,price_start=rows[0]['timestamp'],price_end=rows[-1]['timestamp'],price_gaps=gaps,eligible_signal_days=len(signals)),runs=runs,aggregate_oos=agg,aggregate_stress=aggs,by_year=by,stress_by_year=bys,monthly_base=monthly,gates=gates,historical_pass_before_audit=historical,limitations=['CoinMetrics Community is a third-party metric source and can revise history; hashes are local.','Ledger count is an average daily cadence proxy, not a direct latency distribution.','Daily OHLC is not tick execution; conservative stop-first and candle-low rules apply.','No independent forward PAPER evidence exists.']);(dest/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');
 with gzip.open(dest/'trades.json.gz','wt') as h:json.dump(ledgers,h)
 print(result['status'],gates)
if __name__=='__main__':main()
