import concurrent.futures,datetime as dt,gzip,hashlib,json,pathlib,sys,time,urllib.parse,urllib.request
from dataclasses import replace
from research.xrpl_dex_liquidity_replenishment_v1 import Config,DAY,STRIDE,backtest,make_signals,summarize,validate
UTC=dt.timezone.utc;RPC='https://xrplcluster.com/';ISSUER='rhub8VRN55s94qWKDv6jmDy1pUykJzF3wq';BI='https://data-api.binance.vision/api/v3/klines';RIPPLE_EPOCH=946684800
def stamp(y,m=1,d=1):return int(dt.datetime(y,m,d,tzinfo=UTC).timestamp()*1000)
def rpc(cache,idx,kind,method,params):
    p=cache/f'xrpl-{idx}-{kind}.json';body=json.dumps({'method':method,'params':[params]},sort_keys=True,separators=(',',':')).encode()
    if not p.exists():
        err=None
        for n in range(6):
            try:
                q=urllib.request.Request(RPC,data=body,headers={'User-Agent':'xrp-research/1.0','Content-Type':'application/json'})
                with urllib.request.urlopen(q,timeout=180) as r:raw=r.read()
                doc=json.loads(raw);res=doc.get('result',{})
                if res.get('status')!='success':raise RuntimeError(str(res.get('error') or res))
                p.write_bytes(raw);break
            except Exception as e:err=e;time.sleep(2**n)
        else:raise RuntimeError(f'RPC failed {idx} {kind}: {err}')
    raw=p.read_bytes();doc=json.loads(raw);res=doc['result']
    return res,dict(kind='xrpl_'+kind,url=RPC,method=method,params=params,cache_file=p.name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),ledger_index=idx,ledger_hash=res.get('ledger_hash'))
def snapshot(cache,idx):
    l,lm=rpc(cache,idx,'ledger','ledger',{'ledger_index':idx,'transactions':False,'expand':False});led=l['ledger'];base=dict(validated=l.get('validated'),ledger_index=int(l['ledger_index']),ledger_hash=l['ledger_hash'],close_time_ms=(int(led['close_time'])+RIPPLE_EPOCH)*1000)
    x={'currency':'XRP'};u={'currency':'USD','issuer':ISSUER}
    a,am=rpc(cache,idx,'asks','book_offers',{'ledger_index':idx,'taker_gets':x,'taker_pays':u,'limit':400})
    b,bm=rpc(cache,idx,'bids','book_offers',{'ledger_index':idx,'taker_gets':u,'taker_pays':x,'limit':400})
    return idx,summarize(base,a,b),[lm,am,bm],base
def load_snapshots(cache):
    indices=list(range(60_000_000,107_400_001,STRIDE));got={}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        fs={ex.submit(snapshot,cache,i):i for i in indices}
        for n,f in enumerate(concurrent.futures.as_completed(fs),1):
            i,o,m,b=f.result();got[i]=(o,m,b)
            if n%25==0:print('snapshots',n,'/',len(indices),flush=True)
    obs=[];man=[];bases=[];cut=stamp(2026,10)
    for i in indices:
        o,m,b=got[i]
        if b['close_time_ms']>=cut:continue
        obs.append(o);man+=m;bases.append(b)
    return obs,man,bases
def get(url,p):
    if not p.exists():
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'xrp-research/1.0'}),timeout=180) as r:p.write_bytes(r.read())
    return p.read_bytes()
def load_prices(cache):
    start=stamp(2021);end=stamp(2026,10)-1;cursor=start;page=0;rows=[];man=[]
    while cursor<=end:
        q=urllib.parse.urlencode(dict(symbol='XRPUSDT',interval='1d',startTime=cursor,endTime=end,limit=1000));url=BI+'?'+q;p=cache/f'XRPUSDT-1d-dex-api-{page}.json';raw=get(url,p);doc=json.loads(raw);man.append(dict(kind='binance_XRPUSDT_1d',url=url,cache_file=p.name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),rows=len(doc)))
        if not doc:break
        rows += [dict(timestamp=int(x[0]),open=float(x[1]),high=float(x[2]),low=float(x[3]),close=float(x[4])) for x in doc];cursor=int(doc[-1][0])+DAY;page+=1
        if len(doc)<1000:break
    return rows,man
def metrics(t,c,initial=10000.):
    w=sum(max(0,x['pnl']) for x in t);l=-sum(min(0,x['pnl']) for x in t);n=sum(x['pnl'] for x in t);peak=initial;dd=0
    for x in c:peak=max(peak,x['equity']);dd=max(dd,(peak-x['equity'])/peak*100)
    return dict(trades=len(t),net_pnl=n,net_return_pct=n/initial*100,profit_factor=w/l if l else None,expectancy=n/len(t) if t else None,max_drawdown_pct=dd,fees=sum(x['fees'] for x in t),slippage_cost=sum(x['slippage_cost'] for x in t),gross_profit=w,gross_loss=l)
def main():
    cache=pathlib.Path(sys.argv[1]);dest=pathlib.Path(sys.argv[2]);cache.mkdir(parents=True,exist_ok=True);dest.mkdir(parents=True,exist_ok=True);obs,xm,bases=load_snapshots(cache);rows,pm=load_prices(cache);validate(rows);signals=make_signals(obs)
    for x in rows:
        if x['timestamp'] in signals:x['dex_signal']=signals[x['timestamp']]
    folds=[('2021_control',stamp(2021),stamp(2022))]+[(str(y),stamp(y),stamp(y+1) if y<2026 else stamp(2026,10)) for y in range(2022,2027)]+[('continuous_oos',stamp(2022),stamp(2026,10))];runs={};ledgers={}
    for name,start,end in folds:
        for label,mul in (('base',1),('stress',2)):
            c=replace(Config(),fee=Config().fee*mul,slippage=Config().slippage*mul);t,curve=backtest(rows,start,end,c);key=name+'_'+label;ledgers[key]=t;runs[key]=metrics(t,curve);print(key,runs[key],flush=True)
    years=[str(y) for y in range(2022,2027)];base=[x for y in years for x in ledgers[y+'_base']];stress=[x for y in years for x in ledgers[y+'_stress']];agg=metrics(base,[]);aggs=metrics(stress,[]);agg['max_drawdown_pct']=None;aggs['max_drawdown_pct']=None;by={y:runs[y+'_base']['net_pnl'] for y in years};bys={y:runs[y+'_stress']['net_pnl'] for y in years};monthly={}
    for x in base:
        k=dt.datetime.fromtimestamp(x['exit_timestamp']/1000,UTC).strftime('%Y-%m');monthly[k]=monthly.get(k,0)+x['pnl']
    positive=sum(max(0,v) for v in monthly.values());share=max((max(0,v)/positive for v in monthly.values()),default=1)
    gates=dict(sample=agg['trades']>=100,base_net=agg['net_pnl']>0,base_expectancy=(agg['expectancy'] or 0)>0,base_pf=(agg['profit_factor'] or 0)>1.20,stress_net=aggs['net_pnl']>0,stress_expectancy=(aggs['expectancy'] or 0)>0,stress_pf=(aggs['profit_factor'] or 0)>1.05,four_years=sum(v>0 for v in by.values())>=4,four_years_stress=sum(v>0 for v in bys.values())>=4,final_year=by['2026']>0 and bys['2026']>0,drawdown=max(runs['continuous_oos_base']['max_drawdown_pct'],runs['continuous_oos_stress']['max_drawdown_pct'])<=10,concentration=agg['net_pnl']>0 and positive>0 and share<=.25,audit=False,forward_paper=False)
    hist=all(v for k,v in gates.items() if k not in ('audit','forward_paper'));proto=pathlib.Path('research/xrpl_dex_liquidity_replenishment_protocol_20261030.md');valid=[x for x in obs if x];sig_by={str(y):sum(dt.datetime.fromtimestamp(t/1000,UTC).year==y for t in signals) for y in range(2021,2027)}
    res=dict(strategy='XRPL_DEX_LIQUIDITY_REPLENISHMENT_V1',status='TEST NEDOKONCEN: audit and forward PAPER required' if hist else 'NEPROSEL',protocol_sha256=hashlib.sha256(proto.read_bytes()).hexdigest(),xrpl_manifest=xm,price_manifest=pm,data_quality=dict(requested_snapshots=len(bases),valid_snapshots=len(valid),invalid_snapshots=len(obs)-len(valid),first_ledger=bases[0],last_ledger=bases[-1],valid_time_monotonic=all(b['close_time_ms']>a['close_time_ms'] for a,b in zip(bases,bases[1:])),price_rows=len(rows),price_start=rows[0]['timestamp'],price_end=rows[-1]['timestamp'],price_gaps=[]),signals_total=len(signals),signals_by_entry_year=sig_by,runs=runs,aggregate_oos=agg,aggregate_stress=aggs,by_year=by,stress_by_year=bys,monthly_base=monthly,positive_month_profit_concentration=share,gates=gates,historical_pass_before_audit=hist,limitations=['GateHub USD is issuer credit and its order book is venue- and issuer-specific.','Only offers with explicit positive owner_funds are counted, conservatively understating reusable owner liquidity.','Fixed ledger-index cadence is irregular in calendar time.','Public full-history RPC availability is not guaranteed.','Daily XRP OHLC cannot reconstruct tick paths; fixed conservative gap/stop rules apply.','Local SHA256 values are not publisher signatures.','No independent forward PAPER evidence exists.']);(dest/'results.json').write_text(json.dumps(res,indent=2,allow_nan=False)+'\n')
    with gzip.open(dest/'observations.json.gz','wt') as h:json.dump(obs,h)
    with gzip.open(dest/'trades.json.gz','wt') as h:json.dump(ledgers,h)
    print(res['status'],gates,sig_by,'valid',len(valid),'/',len(obs),flush=True)
if __name__=='__main__':main()
