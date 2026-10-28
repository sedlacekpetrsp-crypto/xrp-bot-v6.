"""Direct stablecoin-supply/Binance validation of frozen liquidity rules."""
import csv,gzip,hashlib,io,json,pathlib,sys,urllib.parse,urllib.request,zipfile,datetime as dt
from dataclasses import replace
from research.stablecoin_liquidity_impulse_v1 import Config,DAY,backtest,validate
MONTHS=[(y,m)for y in range(2020,2027)for m in range(1,13)if(y,m)<(2026,10)];UTC=dt.timezone.utc
def get(u,p):
 if not p.exists():
  with urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'xrp-research/1.0'}),timeout=120)as r:p.write_bytes(r.read())
 return p.read_bytes()
def stamp(y,m=1):return int(dt.datetime(y,m,1,tzinfo=UTC).timestamp()*1000)
def supply(cache):
 q=urllib.parse.urlencode(dict(assets='usdt,usdc',metrics='SplyCur',frequency='1d',start_time='2020-01-01',end_time='2026-10-01',page_size=10000));u=f'https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?{q}';p=get(u,cache/'coinmetrics-stable-supply.json');o=json.loads(p)
 if'error'in o or o.get('next_page_token'):raise ValueError('incomplete CoinMetrics response')
 by={}
 for x in o['data']:
  t=int(dt.datetime.fromisoformat(x['time'].replace('Z','+00:00')).timestamp()*1000);by.setdefault(t,{})[x['asset']]=float(x['SplyCur'])
 rows=[];partial=[]
 for t,x in sorted(by.items()):
  if set(x)=={'usdt','usdc'}:rows.append(dict(timestamp=t,stable_supply=x['usdt']+x['usdc']))
  else:partial.append(dict(timestamp=t,assets=sorted(x)))
 return rows,dict(kind='coinmetrics_USDT_USDC_SplyCur',url=u,sha256=hashlib.sha256(p).hexdigest(),bytes=len(p),raw_rows=len(o['data']),combined_rows=len(rows),partial_dates=partial)
def prices(cache):
 out=[];man=[]
 for y,m in MONTHS:
  n=f'XRPUSDT-1d-{y}-{m:02d}.zip';u=f'https://data.binance.vision/data/spot/monthly/klines/XRPUSDT/1d/{n}';p=get(u,cache/n)
  with zipfile.ZipFile(io.BytesIO(p))as z:rr=list(csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]))))
  a=[]
  for x in rr:
   if x[0].lower().startswith('open'):continue
   t=int(x[0]);t=t//1000 if t>10**14 else t;a.append(dict(timestamp=t,open=float(x[1]),high=float(x[2]),low=float(x[3]),close=float(x[4])))
  out+=a;man.append(dict(kind='binance_XRPUSDT_1d',url=u,sha256=hashlib.sha256(p).hexdigest(),bytes=len(p),rows=len(a)))
 return out,man
def uniq(r,n):
 d={};dup=0
 for x in r:
  if x['timestamp']in d:
   if d[x['timestamp']]!=x:raise ValueError('conflict '+n)
   dup+=1
  d[x['timestamp']]=x
 return d,dup
def folds():return[('2020_2021_control',stamp(2020),stamp(2022)),('2022',stamp(2022),stamp(2023)),('2023',stamp(2023),stamp(2024)),('2024',stamp(2024),stamp(2025)),('2025',stamp(2025),stamp(2026)),('2026',stamp(2026),stamp(2026,10)),('continuous_oos',stamp(2022),stamp(2026,10))]
def met(t,c,initial=10000):
 g=sum(max(0,x['pnl'])for x in t);l=-sum(min(0,x['pnl'])for x in t);net=sum(x['pnl']for x in t);peak=initial;dd=0
 for x in c:peak=max(peak,x['equity']);dd=max(dd,(peak-x['equity'])/peak*100)
 return dict(trades=len(t),net_pnl=net,net_return_pct=net/initial*100,profit_factor=g/l if l else None,expectancy=net/len(t)if t else None,max_drawdown_pct=dd,fees=sum(x['fees']for x in t),slippage_cost=sum(x['slippage_cost']for x in t))
def main():
 cache=pathlib.Path(sys.argv[1]);cache.mkdir(parents=True,exist_ok=True);dest=pathlib.Path(sys.argv[2]);dest.mkdir(parents=True,exist_ok=True);sr,sm=supply(cache);pr,pm=prices(cache);sd,sdup=uniq(sr,'supply');pd,pdup=uniq(pr,'price');common=sorted(set(sd)&set(pd));rows=[{**pd[t],**sd[t]}for t in common];validate(rows);quality=dict(supply_rows=len(sd),price_rows=len(pd),aligned_days=len(rows),supply_duplicates=sdup,price_duplicates=pdup,supply_only=len(set(sd)-set(pd)),price_only=len(set(pd)-set(sd)),gaps=[dict(after=a['timestamp'],before=b['timestamp'],missing_days=(b['timestamp']-a['timestamp'])//DAY-1)for a,b in zip(rows,rows[1:])if b['timestamp']-a['timestamp']!=DAY]);runs={};led={}
 for name,start,end in folds():
  for label,mult in(('base',1),('stress',2)):
   b=Config();c=replace(b,fee=b.fee*mult,slippage=b.slippage*mult);t,curve=backtest(rows,start,end,c);k=f'{name}_{label}';led[k]=t;runs[k]=met(t,curve);print(k,runs[k],flush=True)
 ys=['2022','2023','2024','2025','2026'];bt=[x for y in ys for x in led[f'{y}_base']];st=[x for y in ys for x in led[f'{y}_stress']];bm=met(bt,[{'equity':10000},{'equity':10000+sum(x['pnl']for x in bt)}]);xm=met(st,[{'equity':10000},{'equity':10000+sum(x['pnl']for x in st)}]);by={y:runs[f'{y}_base']['net_pnl']for y in ys};sy={y:runs[f'{y}_stress']['net_pnl']for y in ys};monthly={}
 for x in bt:
  k=dt.datetime.fromtimestamp(x['exit_timestamp']/1000,UTC).strftime('%Y-%m');monthly[k]=monthly.get(k,0)+x['pnl']
 pos=sum(max(0,x)for x in monthly.values());gates=dict(sample=bm['trades']>=75,base_net=bm['net_pnl']>0,base_expectancy=(bm['expectancy']or 0)>0,base_pf=(bm['profit_factor']or 0)>1.15,stress_net=xm['net_pnl']>0,stress_expectancy=(xm['expectancy']or 0)>0,stress_pf=(xm['profit_factor']or 0)>1.02,four_positive_years=sum(x>0 for x in by.values())>=4,four_positive_stress_years=sum(x>0 for x in sy.values())>=4,final_year=by['2026']>0 and sy['2026']>0,drawdown=max(runs['continuous_oos_base']['max_drawdown_pct'],runs['continuous_oos_stress']['max_drawdown_pct'])<=10,concentration=bm['net_pnl']>0 and pos>0 and max(monthly.values(),default=0)<=.25*pos);hp=all(gates.values());prot=pathlib.Path('research/stablecoin_liquidity_impulse_protocol.md');res=dict(strategy='STABLECOIN_LIQUIDITY_IMPULSE_XRP_V1',status='TEST NEDOKONCEN: independent forward PAPER evidence required'if hp else'NEPROSEL',protocol_sha256=hashlib.sha256(prot.read_bytes()).hexdigest(),manifest=[sm]+pm,data_quality=quality,runs=runs,aggregate_oos=bm,aggregate_stress=xm,by_year=by,stress_by_year=sy,monthly_base=monthly,gates=gates,historical_pass=hp,limitations=['CoinMetrics supply is third-party derived and may reflect multi-chain methodology changes; response bytes are locally hashed, not publisher-signed.','Both stablecoin assets must exist on an exact date; no carry-forward or interpolation.','A full-day lag prevents same-day supply leakage.','Daily OHLC is not tick execution; historical dates are exploratory and no forward PAPER evidence exists.']);(dest/'results.json').write_text(json.dumps(res,indent=2,allow_nan=False)+'\n')
 with gzip.open(dest/'trades.json.gz','wt')as h:json.dump(led,h)
 print(res['status'],gates,flush=True)
if __name__=='__main__':main()
