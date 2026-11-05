"""Frozen direct FRED/Binance bank-credit validation."""
import csv,datetime as dt,gzip,hashlib,io,json,pathlib,sys,urllib.parse,urllib.request
from dataclasses import replace
from research.xrp_bank_credit_expansion_v1 import Config,DAY,backtest,make_signals,validate_prices
UTC=dt.timezone.utc

def get(url,path):
    if not path.exists():
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'xrp-paper-research/1.0'}),timeout=120) as r: path.write_bytes(r.read())
    return path.read_bytes()
def stamp(y,m=1,d=1): return int(dt.datetime(y,m,d,tzinfo=UTC).timestamp()*1000)
def load_macro(cache):
    url='https://fred.stlouisfed.org/graph/fredgraph.csv?id=BUSLOANS&cosd=2020-01-01&coed=2026-10-01'; payload=get(url,cache/'fred-BUSLOANS.csv'); raw=list(csv.DictReader(io.StringIO(payload.decode()))); rows=[]; missing=[]
    for x in raw:
        t=int(dt.datetime.strptime(x['observation_date'],'%Y-%m-%d').replace(tzinfo=UTC).timestamp()*1000); v=x['BUSLOANS'].strip()
        if v in ('','.'): missing.append(t); continue
        rows.append({'timestamp':t,'value':float(v)})
    return rows,{'kind':'FRED_BUSLOANS','url':url,'sha256':hashlib.sha256(payload).hexdigest(),'bytes':len(payload),'raw_rows':len(raw),'valid_rows':len(rows),'missing_value_timestamps':missing}
def load_prices(cache):
    base='https://data-api.binance.vision/api/v3/klines'; start=stamp(2020); end=stamp(2026,10,1)-1; page=0; rows=[]; manifest=[]
    while start<=end:
        url=base+'?'+urllib.parse.urlencode({'symbol':'XRPUSDT','interval':'1d','startTime':start,'endTime':end,'limit':1000}); path=cache/f'XRPUSDT-1d-credit-api-{page}.json'; payload=get(url,path); data=json.loads(payload)
        if not isinstance(data,list) or not data: raise ValueError('empty Binance page')
        parsed=[{'timestamp':int(x[0]),'open':float(x[1]),'high':float(x[2]),'low':float(x[3]),'close':float(x[4])} for x in data]; rows+=parsed
        manifest.append({'kind':'binance_XRPUSDT_1d','url':url,'sha256':hashlib.sha256(payload).hexdigest(),'bytes':len(payload),'rows':len(parsed),'first_timestamp':parsed[0]['timestamp'],'last_timestamp':parsed[-1]['timestamp']})
        new=parsed[-1]['timestamp']+DAY
        if new<=start: raise ValueError('non-advancing page')
        start=new; page+=1
    return rows,manifest
def unique(rows,name):
    out={}; duplicates=0
    for x in rows:
        if x['timestamp'] in out:
            if out[x['timestamp']]!=x: raise ValueError('conflicting duplicate '+name)
            duplicates+=1
        out[x['timestamp']]=x
    return [out[t] for t in sorted(out)],duplicates
def metrics(trades,curve,initial=10_000.):
    gain=sum(max(0,x['pnl']) for x in trades); loss=-sum(min(0,x['pnl']) for x in trades); net=sum(x['pnl'] for x in trades); peak=initial; dd=0
    for p in curve: peak=max(peak,p['equity']); dd=max(dd,(peak-p['equity'])/peak*100)
    return {'trades':len(trades),'net_pnl':net,'net_return_pct':net/initial*100,'profit_factor':gain/loss if loss else None,'expectancy':net/len(trades) if trades else None,'max_drawdown_pct':dd,'fees':sum(x['fees'] for x in trades),'slippage_cost':sum(x['slippage_cost'] for x in trades)}
def main():
    cache=pathlib.Path(sys.argv[1]); cache.mkdir(parents=True,exist_ok=True); dest=pathlib.Path(sys.argv[2]); dest.mkdir(parents=True,exist_ok=True)
    mr,mm=load_macro(cache); pr,pm=load_prices(cache); macro,md=unique(mr,'macro'); prices,pd=unique(pr,'price'); validate_prices(prices); signals=make_signals(macro)
    rows=[]
    for x in prices:
        row=dict(x); signal=signals.get(x['timestamp']); row.update(macro_signal=bool(signal)); row.update(signal or {}); rows.append(row)
    gaps=[{'after':a['timestamp'],'before':b['timestamp'],'missing_days':(b['timestamp']-a['timestamp'])//DAY-1} for a,b in zip(prices,prices[1:]) if b['timestamp']-a['timestamp']!=DAY]
    quality={'macro_rows':len(macro),'macro_duplicates':md,'macro_start':macro[0]['timestamp'],'macro_end':macro[-1]['timestamp'],'price_rows':len(prices),'price_duplicates':pd,'price_start':prices[0]['timestamp'],'price_end':prices[-1]['timestamp'],'price_gaps':gaps,'eligible_signal_dates':len(signals),'signal_dates_without_price':len(set(signals)-{x['timestamp'] for x in prices})}
    folds=[('2020_2021_control',stamp(2020),stamp(2022))]+[(str(y),stamp(y),stamp(y+1) if y<2026 else stamp(2026,10,1)) for y in range(2022,2027)]+[('continuous_oos',stamp(2022),stamp(2026,10,1))]
    runs={}; ledgers={}
    for name,start,end in folds:
        for label,multiple in (('base',1),('stress',2)):
            c=Config(); c=replace(c,fee=c.fee*multiple,slippage=c.slippage*multiple); trades,curve=backtest(rows,start,end,c); key=f'{name}_{label}'; ledgers[key]=trades; runs[key]=metrics(trades,curve); print(key,runs[key],flush=True)
    years=[str(y) for y in range(2022,2027)]; bt=[x for y in years for x in ledgers[y+'_base']]; st=[x for y in years for x in ledgers[y+'_stress']]
    def aggregate(ts): return metrics(ts,[{'equity':10_000.},{'equity':10_000.+sum(x['pnl'] for x in ts)}])
    ab=aggregate(bt); ass=aggregate(st); ab['max_drawdown_pct']=None; ass['max_drawdown_pct']=None
    by={y:runs[y+'_base']['net_pnl'] for y in years}; sy={y:runs[y+'_stress']['net_pnl'] for y in years}; monthly={}
    for t in bt:
        m=dt.datetime.fromtimestamp(t['exit_timestamp']/1000,UTC).strftime('%Y-%m'); monthly[m]=monthly.get(m,0)+t['pnl']
    positive=sum(max(0,v) for v in monthly.values())
    gates={'sample':ab['trades']>=75,'base_net':ab['net_pnl']>0,'base_expectancy':(ab['expectancy'] or 0)>0,'base_pf':(ab['profit_factor'] or 0)>1.15,'stress_net':ass['net_pnl']>0,'stress_expectancy':(ass['expectancy'] or 0)>0,'stress_pf':(ass['profit_factor'] or 0)>1.02,'four_positive_years':sum(v>0 for v in by.values())>=4,'four_positive_stress_years':sum(v>0 for v in sy.values())>=4,'final_year':by['2026']>0 and sy['2026']>0,'drawdown':max(runs['continuous_oos_base']['max_drawdown_pct'],runs['continuous_oos_stress']['max_drawdown_pct'])<=10,'concentration':ab['net_pnl']>0 and positive>0 and max(monthly.values(),default=0)<=.25*positive,'audit':False,'forward_paper':False}
    historical=all(v for k,v in gates.items() if k not in ('audit','forward_paper')); protocol=pathlib.Path('research/xrp_bank_credit_expansion_protocol_20261105.md')
    result={'strategy':'XRP_BANK_CREDIT_EXPANSION_V1','status':'TEST NEDOKONCEN: audit and forward PAPER required' if historical else 'NEPROSEL','protocol_sha256':hashlib.sha256(protocol.read_bytes()).hexdigest(),'manifest':[mm]+pm,'data_quality':quality,'runs':runs,'aggregate_oos':ab,'aggregate_stress':ass,'by_year':by,'stress_by_year':sy,'monthly_base':monthly,'gates':gates,'historical_pass_before_audit':historical,'limitations':['FRED can revise history; retained SHA256 identifies this evaluated response, not an original vintage.','Two-observation lag is conservative but does not reconstruct original release vintages.','Daily OHLC uses stop-first ambiguity and cannot reconstruct tick order.','No independent forward PAPER evidence exists.']}
    (dest/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');
    with gzip.open(dest/'trades.json.gz','wt') as h: json.dump(ledgers,h)
    print(result['status'],gates,flush=True)
if __name__=='__main__': main()
