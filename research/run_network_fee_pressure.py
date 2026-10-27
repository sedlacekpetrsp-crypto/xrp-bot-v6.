"""Direct CoinMetrics/Binance validation of frozen fee-pressure rules."""
import csv,gzip,hashlib,io,json,pathlib,sys,urllib.parse,urllib.request,zipfile,datetime as dt
from dataclasses import replace
from research.network_fee_pressure_v1 import Config,DAY,backtest,validate
MONTHS=[(y,m) for y in range(2022,2027) for m in range(1,13) if (y,m)<(2026,10)];UTC=dt.timezone.utc
def get(url,path):
 if not path.exists():
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'xrp-research/1.0'}),timeout=120) as r:path.write_bytes(r.read())
 return path.read_bytes()
def stamp(y,m=1):return int(dt.datetime(y,m,1,tzinfo=UTC).timestamp()*1000)
def fetch_metrics(cache):
 q=urllib.parse.urlencode(dict(assets='xrp',metrics='FeeTotNtv,TxTfrCnt',frequency='1d',start_time='2022-01-01',end_time='2026-10-01',page_size=10000));url=f'https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?{q}';p=get(url,cache/'coinmetrics-xrp-fees.json');o=json.loads(p)
 if 'error'in o or o.get('next_page_token'):raise ValueError('incomplete CoinMetrics response')
 rows=[]
 for x in o['data']:rows.append(dict(timestamp=int(dt.datetime.fromisoformat(x['time'].replace('Z','+00:00')).timestamp()*1000),fee_total=float(x['FeeTotNtv']),transfer_count=float(x['TxTfrCnt'])))
 return rows,dict(kind='coinmetrics_xrp_fee_pressure',url=url,sha256=hashlib.sha256(p).hexdigest(),bytes=len(p),rows=len(rows))
def fetch_prices(cache):
 out=[];man=[]
 for y,m in MONTHS:
  n=f'XRPUSDT-1d-{y}-{m:02d}.zip';u=f'https://data.binance.vision/data/spot/monthly/klines/XRPUSDT/1d/{n}';p=get(u,cache/n)
  with zipfile.ZipFile(io.BytesIO(p))as z:rr=list(csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]))))
  rows=[]
  for x in rr:
   if x[0].lower().startswith('open'):continue
   t=int(x[0]);t=t//1000 if t>10**14 else t;rows.append(dict(timestamp=t,open=float(x[1]),high=float(x[2]),low=float(x[3]),close=float(x[4])))
  out+=rows;man.append(dict(kind='binance_XRPUSDT_1d',url=u,sha256=hashlib.sha256(p).hexdigest(),bytes=len(p),rows=len(rows)))
 return out,man
def uniq(rows,label):
 d={};dup=0
 for x in rows:
  if x['timestamp']in d:
   if d[x['timestamp']]!=x:raise ValueError('conflict '+label)
   dup+=1
  d[x['timestamp']]=x
 return d,dup
def folds():return [('2022_control',stamp(2022),stamp(2023)),('2023',stamp(2023),stamp(2024)),('2024',stamp(2024),stamp(2025)),('2025',stamp(2025),stamp(2026)),('2026',stamp(2026),stamp(2026,10)),('continuous_oos',stamp(2023),stamp(2026,10))]
def met(t,c,initial=10000):
 g=sum(max(0,x['pnl'])for x in t);l=-sum(min(0,x['pnl'])for x in t);n=sum(x['pnl']for x in t);peak=initial;dd=0
 for x in c:peak=max(peak,x['equity']);dd=max(dd,(peak-x['equity'])/peak*100)
 return dict(trades=len(t),net_pnl=n,net_return_pct=n/initial*100,profit_factor=g/l if l else None,expectancy=n/len(t)if t else None,max_drawdown_pct=dd,fees=sum(x['fees']for x in t),slippage_cost=sum(x['slippage_cost']for x in t))
def main():
 cache=pathlib.Path(sys.argv[1]);cache.mkdir(parents=True,exist_ok=True);dest=pathlib.Path(sys.argv[2]);dest.mkdir(parents=True,exist_ok=True);mr,mm=fetch_metrics(cache);pr,pm=fetch_prices(cache);md,mdup=uniq(mr,'metric');pd,pdup=uniq(pr,'price');common=sorted(set(md)&set(pd));rows=[{**pd[t],**md[t]}for t in common];validate(rows)
 quality=dict(metric_rows=len(md),price_rows=len(pd),aligned_days=len(rows),metric_duplicates=mdup,price_duplicates=pdup,metric_only=len(set(md)-set(pd)),price_only=len(set(pd)-set(md)),gaps=[dict(after=a['timestamp'],before=b['timestamp'],missing_days=(b['timestamp']-a['timestamp'])//DAY-1)for a,b in zip(rows,rows[1:])if b['timestamp']-a['timestamp']!=DAY]);runs={};ledger={}
 for name,start,end in folds():
  for label,mult in(('base',1),('stress',2)):
   b=Config();c=replace(b,fee=b.fee*mult,slippage=b.slippage*mult);t,curve=backtest(rows,start,end,c);k=f'{name}_{label}';ledger[k]=t;runs[k]=met(t,curve);print(k,runs[k],flush=True)
 years=['2023','2024','2025','2026'];bt=[x for y in years for x in ledger[f'{y}_base']];st=[x for y in years for x in ledger[f'{y}_stress']];bm=met(bt,[{'equity':10000},{'equity':10000+sum(x['pnl']for x in bt)}]);sm=met(st,[{'equity':10000},{'equity':10000+sum(x['pnl']for x in st)}]);by={y:runs[f'{y}_base']['net_pnl']for y in years};sy={y:runs[f'{y}_stress']['net_pnl']for y in years};monthly={}
 for x in bt:
  k=dt.datetime.fromtimestamp(x['exit_timestamp']/1000,UTC).strftime('%Y-%m');monthly[k]=monthly.get(k,0)+x['pnl']
 pos=sum(max(0,x)for x in monthly.values());gates=dict(sample=bm['trades']>=100,base_net=bm['net_pnl']>0,base_expectancy=(bm['expectancy']or 0)>0,base_pf=(bm['profit_factor']or 0)>1.15,stress_net=sm['net_pnl']>0,stress_expectancy=(sm['expectancy']or 0)>0,stress_pf=(sm['profit_factor']or 0)>1.02,three_positive_years=sum(x>0 for x in by.values())>=3,three_positive_stress_years=sum(x>0 for x in sy.values())>=3,final_year=by['2026']>0 and sy['2026']>0,drawdown=max(runs['continuous_oos_base']['max_drawdown_pct'],runs['continuous_oos_stress']['max_drawdown_pct'])<=10,concentration=bm['net_pnl']>0 and pos>0 and max(monthly.values(),default=0)<=.25*pos);hp=all(gates.values());prot=pathlib.Path('research/network_fee_pressure_protocol.md')
 res=dict(strategy='XRP_NETWORK_FEE_PRESSURE_V1',status='TEST NEDOKONCEN: independent forward PAPER evidence required'if hp else'NEPROSEL',protocol_sha256=hashlib.sha256(prot.read_bytes()).hexdigest(),manifest=[mm]+pm,data_quality=quality,runs=runs,aggregate_oos=bm,aggregate_stress=sm,by_year=by,stress_by_year=sy,monthly_base=monthly,gates=gates,historical_pass=hp,limitations=['CoinMetrics Community metrics are third-party derived; response bytes are locally hashed, not publisher-signed.','A full-day publication lag prevents same-day aggregate leakage.','Daily OHLC uses adverse stop priority and is not intraday tick execution.','Historical dates are exploratory; no independent forward PAPER evidence exists.']);(dest/'results.json').write_text(json.dumps(res,indent=2,allow_nan=False)+'\n')
 with gzip.open(dest/'trades.json.gz','wt')as h:json.dump(ledger,h)
 print(res['status'],gates,flush=True)
if __name__=='__main__':main()
