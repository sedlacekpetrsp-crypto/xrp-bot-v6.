"""Official GitHub/Binance validation for XRP_CORE_DEVELOPMENT_ACTIVITY_V1."""
import csv,datetime as dt,gzip,hashlib,io,json,pathlib,sys,urllib.parse,urllib.request,zipfile
from dataclasses import replace
from research.core_development_activity_v1 import Config,DAY,backtest,daily_signals,validate_prices

UTC=dt.timezone.utc
MONTHS=[(y,m) for y in range(2020,2027) for m in range(1,13) if (y,m)<(2026,10)]
PARTITIONS=[(str(y),f'{y}-01-01',f'{y}-12-31',pages) for y,pages in ((2020,1),(2021,1),(2022,1),(2023,3),(2024,2),(2025,7))]
PARTITIONS += [(f'2026-{m:02d}',f'2026-{m:02d}-01',f'2026-{m:02d}-{[31,28,31,30,31,30,31,31,30][m-1]:02d}',2 if m in (1,3,4,5,6,7,8,9) else 1) for m in range(1,10)]

def get(url,path):
    if not path.exists():
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'xrp-research/1.0','Accept':'application/vnd.github+json'}),timeout=120) as r:path.write_bytes(r.read())
    return path.read_bytes()
def stamp(y,m=1):return int(dt.datetime(y,m,1,tzinfo=UTC).timestamp()*1000)
def search_url(first,last,page):
    q=f'repo:XRPLF/rippled is:pr is:merged merged:{first}..{last}'
    return 'https://api.github.com/search/issues?q='+urllib.parse.quote(q,safe='')+f'&sort=created&order=asc&per_page=100&page={page}'

def development(cache):
    manifest=[]; events={}; partition_counts={}
    for name,first,last,pages in PARTITIONS:
        total=None; seen=0
        for page in range(1,pages+1):
            url=search_url(first,last,page); path=cache/f'rippled-merged-{name}-p{page}.json'; payload=get(url,path); doc=json.loads(payload)
            if total is None:total=doc['total_count']
            if doc['total_count']!=total:raise ValueError('changing total '+name)
            seen+=len(doc['items']);manifest.append(dict(kind='github_XRPLF_rippled_merged_prs',partition=name,page=page,url=url,sha256=hashlib.sha256(payload).hexdigest(),bytes=len(payload),reported_total=total,rows=len(doc['items'])))
            for x in doc['items']:
                merged=x.get('pull_request',{}).get('merged_at')
                if not merged:raise ValueError('unmerged search result')
                if not(first<=merged[:10]<=last):raise ValueError('partition escape')
                ts=int(dt.datetime.fromisoformat(merged.replace('Z','+00:00')).timestamp()*1000); key=x['number']
                if key in events and events[key]!=ts:raise ValueError('conflicting PR')
                events[key]=ts
        if total>1000 or seen!=total:raise ValueError(f'incomplete {name}: {seen}/{total}')
        partition_counts[name]=total
    ordered=sorted(events.values())
    return ordered,manifest,partition_counts

def prices(cache):
    out=[];manifest=[]
    for y,m in MONTHS:
        name=f'XRPUSDT-1d-{y}-{m:02d}.zip';url=f'https://data.binance.vision/data/spot/monthly/klines/XRPUSDT/1d/{name}';payload=get(url,cache/name)
        with zipfile.ZipFile(io.BytesIO(payload)) as z:raw=list(csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]))))
        rows=[]
        for x in raw:
            if x[0].lower().startswith('open'):continue
            ts=int(x[0]);ts=ts//1000 if ts>10**14 else ts;rows.append(dict(timestamp=ts,open=float(x[1]),high=float(x[2]),low=float(x[3]),close=float(x[4])))
        out+=rows;manifest.append(dict(kind='binance_XRPUSDT_1d',url=url,sha256=hashlib.sha256(payload).hexdigest(),bytes=len(payload),rows=len(rows)))
    return out,manifest
def unique(rows):
    d={};dups=0
    for x in rows:
        if x['timestamp'] in d:
            if d[x['timestamp']]!=x:raise ValueError('price conflict')
            dups+=1
        d[x['timestamp']]=x
    return [d[t] for t in sorted(d)],dups
def metrics(trades,curve,initial=10000):
    gains=sum(max(0,x['pnl']) for x in trades);losses=-sum(min(0,x['pnl']) for x in trades);net=sum(x['pnl'] for x in trades);peak=initial;dd=0
    for x in curve:peak=max(peak,x['equity']);dd=max(dd,(peak-x['equity'])/peak*100)
    return dict(trades=len(trades),net_pnl=net,net_return_pct=net/initial*100,profit_factor=gains/losses if losses else None,expectancy=net/len(trades) if trades else None,max_drawdown_pct=dd,fees=sum(x['fees'] for x in trades),slippage_cost=sum(x['slippage_cost'] for x in trades))

def main():
    cache=pathlib.Path(sys.argv[1]);cache.mkdir(parents=True,exist_ok=True);dest=pathlib.Path(sys.argv[2]);dest.mkdir(parents=True,exist_ok=True)
    events,gm,counts=development(cache);raw_prices,pm=prices(cache);rows,pdup=unique(raw_prices);validate_prices(rows)
    signals=daily_signals(events,stamp(2020),stamp(2026,10))
    for x in rows:
        if x['timestamp'] in signals:x['development_signal']=signals[x['timestamp']]
    gaps=[dict(after=a['timestamp'],before=b['timestamp'],missing_days=(b['timestamp']-a['timestamp'])//DAY-1) for a,b in zip(rows,rows[1:]) if b['timestamp']-a['timestamp']!=DAY]
    folds=[('2020_2021_control',stamp(2020),stamp(2022))]+[(str(y),stamp(y),stamp(y+1) if y<2026 else stamp(2026,10)) for y in range(2022,2027)]+[('continuous_oos',stamp(2022),stamp(2026,10))]
    runs={};ledgers={}
    for name,start,end in folds:
        for label,multiple in (('base',1),('stress',2)):
            c=Config();c=replace(c,fee=c.fee*multiple,slippage=c.slippage*multiple);trades,curve=backtest(rows,start,end,c);key=f'{name}_{label}';ledgers[key]=trades;runs[key]=metrics(trades,curve);print(key,runs[key],flush=True)
    years=[str(y) for y in range(2022,2027)];base=[x for y in years for x in ledgers[f'{y}_base']];stress=[x for y in years for x in ledgers[f'{y}_stress']]
    aggregate=metrics(base,[{'equity':10000},{'equity':10000+sum(x['pnl'] for x in base)}]);aggregate_stress=metrics(stress,[{'equity':10000},{'equity':10000+sum(x['pnl'] for x in stress)}]);aggregate['max_drawdown_pct']=None;aggregate_stress['max_drawdown_pct']=None
    by_year={y:runs[f'{y}_base']['net_pnl'] for y in years};stress_by_year={y:runs[f'{y}_stress']['net_pnl'] for y in years};monthly={}
    for x in base:
        k=dt.datetime.fromtimestamp(x['exit_timestamp']/1000,UTC).strftime('%Y-%m');monthly[k]=monthly.get(k,0)+x['pnl']
    positive=sum(max(0,v) for v in monthly.values())
    gates=dict(sample=aggregate['trades']>=75,base_net=aggregate['net_pnl']>0,base_expectancy=(aggregate['expectancy'] or 0)>0,base_pf=(aggregate['profit_factor'] or 0)>1.20,stress_net=aggregate_stress['net_pnl']>0,stress_expectancy=(aggregate_stress['expectancy'] or 0)>0,stress_pf=(aggregate_stress['profit_factor'] or 0)>1.05,four_years=sum(v>0 for v in by_year.values())>=4,four_years_stress=sum(v>0 for v in stress_by_year.values())>=4,final_year=by_year['2026']>0 and stress_by_year['2026']>0,drawdown=max(runs['continuous_oos_base']['max_drawdown_pct'],runs['continuous_oos_stress']['max_drawdown_pct'])<=10,concentration=aggregate['net_pnl']>0 and positive>0 and max(monthly.values(),default=0)<=.40*positive,audit=False,forward_paper=False)
    historical=all(v for k,v in gates.items() if k not in ('audit','forward_paper'))
    protocol=pathlib.Path('research/core_development_activity_protocol_20261029.md')
    result=dict(strategy='XRP_CORE_DEVELOPMENT_ACTIVITY_V1',status='TEST NEDOKONCEN: audit and forward PAPER required' if historical else 'NEPROSEL',protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),manifest=gm+pm,data_quality=dict(merged_prs=len(events),partition_counts=counts,event_start=events[0],event_end=events[-1],price_rows=len(rows),price_duplicates=pdup,price_start=rows[0]['timestamp'],price_end=rows[-1]['timestamp'],price_gaps=gaps,eligible_signal_days=len(signals)),runs=runs,aggregate_oos=aggregate,aggregate_stress=aggregate_stress,by_year=by_year,stress_by_year=stress_by_year,monthly_base=monthly,gates=gates,historical_pass_before_audit=historical,limitations=['GitHub search is a public official index but historical results can change if repository metadata is altered; raw responses are locally hashed, not publisher-signed.','Merge count weights every PR equally and does not measure code quality or deployment.','Daily OHLC is not tick execution; stop-first ambiguity and candle-low drawdown are conservative.','All market history is exploratory and no independent forward PAPER evidence exists.'])
    (dest/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    with gzip.open(dest/'trades.json.gz','wt') as h:json.dump(ledgers,h)
    print(result['status'],gates,flush=True)
if __name__=='__main__':main()
