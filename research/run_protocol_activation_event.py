"""Official XRPL/Binance validation for XRP_PROTOCOL_ACTIVATION_EVENT_V1."""
import csv,datetime as dt,gzip,hashlib,io,json,pathlib,sys,urllib.request,zipfile
from dataclasses import replace
from research.protocol_activation_event_v1 import Config,DAY,backtest,event_signals,validate_prices

UTC=dt.timezone.utc
SNAPSHOT='https://raw.githubusercontent.com/XRPLF/xrpl-dev-portal/master/@theme/data/amendments-snapshot.json'
MONTHS=[(y,m) for y in range(2020,2027) for m in range(1,13) if (y,m)<(2026,10)]

def get(url,path):
    if not path.exists():
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'xrp-research/1.0'}),timeout=120) as r:path.write_bytes(r.read())
    return path.read_bytes()
def stamp(y,m=1):return int(dt.datetime(y,m,1,tzinfo=UTC).timestamp()*1000)
def amendments(cache):
    p=cache/'amendments-snapshot.json';raw=get(SNAPSHOT,p);doc=json.loads(raw);rows=doc['amendments']
    return rows,dict(kind='XRPLF_xrpl_dev_portal_amendments_snapshot',url=SNAPSHOT,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),rows=len(rows),fetched_at=doc.get('fetched_at'))
def prices(cache):
    out=[];manifest=[]
    for y,m in MONTHS:
        name=f'XRPUSDT-1d-{y}-{m:02d}.zip';url=f'https://data.binance.vision/data/spot/monthly/klines/XRPUSDT/1d/{name}';p=cache/name;raw=get(url,p)
        with zipfile.ZipFile(io.BytesIO(raw)) as z:source=list(csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]))))
        rows=[]
        for x in source:
            if x[0].lower().startswith('open'):continue
            t=int(x[0]);t=t//1000 if t>10**14 else t;rows.append(dict(timestamp=t,open=float(x[1]),high=float(x[2]),low=float(x[3]),close=float(x[4])))
        out+=rows;manifest.append(dict(kind='binance_XRPUSDT_1d',url=url,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),rows=len(rows)))
    return out,manifest
def unique(rows):
    d={};dups=0
    for x in rows:
        if x['timestamp'] in d:
            if d[x['timestamp']]!=x:raise ValueError('price conflict')
            dups+=1
        d[x['timestamp']]=x
    return [d[t] for t in sorted(d)],dups
def metrics(trades,curve,initial=10000.):
    gains=sum(max(0,x['pnl']) for x in trades);losses=-sum(min(0,x['pnl']) for x in trades);net=sum(x['pnl'] for x in trades);peak=initial;dd=0
    for x in curve:peak=max(peak,x['equity']);dd=max(dd,(peak-x['equity'])/peak*100)
    return dict(trades=len(trades),net_pnl=net,net_return_pct=net/initial*100,profit_factor=gains/losses if losses else None,expectancy=net/len(trades) if trades else None,max_drawdown_pct=dd,fees=sum(x['fees'] for x in trades),slippage_cost=sum(x['slippage_cost'] for x in trades))

def main():
    cache=pathlib.Path(sys.argv[1]);cache.mkdir(parents=True,exist_ok=True);dest=pathlib.Path(sys.argv[2]);dest.mkdir(parents=True,exist_ok=True)
    records,am=amendments(cache);raw,pm=prices(cache);rows,pdup=unique(raw);validate_prices(rows);signals=event_signals(records)
    for x in rows:
        if x['timestamp'] in signals:x['activation_signal']=signals[x['timestamp']]
    gaps=[dict(after=a['timestamp'],before=b['timestamp'],missing_days=(b['timestamp']-a['timestamp'])//DAY-1) for a,b in zip(rows,rows[1:]) if b['timestamp']-a['timestamp']!=DAY]
    dated=[x for x in records if x.get('date') and x.get('ledger_index') is not None and x.get('tx_hash')]
    folds=[('2020_2021_control',stamp(2020),stamp(2022))]+[(str(y),stamp(y),stamp(y+1) if y<2026 else stamp(2026,10)) for y in range(2022,2027)]+[('continuous_oos',stamp(2022),stamp(2026,10))]
    runs={};ledgers={}
    for name,start,end in folds:
        for label,mul in (('base',1),('stress',2)):
            c=replace(Config(),fee=Config().fee*mul,slippage=Config().slippage*mul);trades,curve=backtest(rows,start,end,c);key=f'{name}_{label}';ledgers[key]=trades;runs[key]=metrics(trades,curve);print(key,runs[key],flush=True)
    years=[str(y) for y in range(2022,2027)];base=[x for y in years for x in ledgers[y+'_base']];stress=[x for y in years for x in ledgers[y+'_stress']]
    aggregate=metrics(base,[{'equity':10000},{'equity':10000+sum(x['pnl'] for x in base)}]);aggregate_stress=metrics(stress,[{'equity':10000},{'equity':10000+sum(x['pnl'] for x in stress)}]);aggregate['max_drawdown_pct']=None;aggregate_stress['max_drawdown_pct']=None
    by={y:runs[y+'_base']['net_pnl'] for y in years};bys={y:runs[y+'_stress']['net_pnl'] for y in years};monthly={}
    for x in base:
        k=dt.datetime.fromtimestamp(x['exit_timestamp']/1000,UTC).strftime('%Y-%m');monthly[k]=monthly.get(k,0)+x['pnl']
    positive=sum(max(0,v) for v in monthly.values())
    gates=dict(sample=aggregate['trades']>=75,base_net=aggregate['net_pnl']>0,base_expectancy=(aggregate['expectancy'] or 0)>0,base_pf=(aggregate['profit_factor'] or 0)>1.20,stress_net=aggregate_stress['net_pnl']>0,stress_expectancy=(aggregate_stress['expectancy'] or 0)>0,stress_pf=(aggregate_stress['profit_factor'] or 0)>1.05,four_years=sum(v>0 for v in by.values())>=4,four_years_stress=sum(v>0 for v in bys.values())>=4,final_year=by['2026']>0 and bys['2026']>0,drawdown=max(runs['continuous_oos_base']['max_drawdown_pct'],runs['continuous_oos_stress']['max_drawdown_pct'])<=10,concentration=aggregate['net_pnl']>0 and positive>0 and max(monthly.values(),default=0)<=.40*positive,audit=False,forward_paper=False)
    historical=all(v for k,v in gates.items() if k not in ('audit','forward_paper'));proto=pathlib.Path('research/protocol_activation_event_protocol_20261029.md')
    result=dict(strategy='XRP_PROTOCOL_ACTIVATION_EVENT_V1',status='TEST NEDOKONCEN: audit and forward PAPER required' if historical else 'NEPROSEL',protocol_sha256=hashlib.sha256(proto.read_bytes()).hexdigest(),manifest=[am]+pm,data_quality=dict(snapshot_records=len(records),dated_records=len(dated),dated_start=min(x['date'] for x in dated),dated_end=max(x['date'] for x in dated),unique_event_entries=len(signals),event_entries_2020_2026=sum(stamp(2020)<=t<stamp(2026,10) for t in signals),price_rows=len(rows),price_duplicates=pdup,price_start=rows[0]['timestamp'],price_end=rows[-1]['timestamp'],price_gaps=gaps),runs=runs,aggregate_oos=aggregate,aggregate_stress=aggregate_stress,by_year=by,stress_by_year=bys,monthly_base=monthly,gates=gates,historical_pass_before_audit=historical,limitations=['The official current snapshot can revise metadata; retained bytes are locally hashed, not publisher-signed.','Activation is publicly anticipated after validator voting, so the event may be priced before its ledger timestamp.','Sparse protocol activations structurally limit statistical power; the sample gate was not reduced.','Daily OHLC cannot reconstruct intraday paths; stop-first and gap-stop rules are conservative.','All history is exploratory and no independent forward PAPER evidence exists.'])
    (dest/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    with gzip.open(dest/'trades.json.gz','wt') as h:json.dump(ledgers,h)
    print(result['status'],gates,flush=True)
if __name__=='__main__':main()
