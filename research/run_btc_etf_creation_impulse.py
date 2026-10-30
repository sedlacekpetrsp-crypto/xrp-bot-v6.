import datetime as dt,gzip,hashlib,json,pathlib,sys,urllib.parse,urllib.request
from dataclasses import replace
from research.btc_etf_creation_impulse_v1 import Config,DAY,backtest,make_signals,parse_farside_html,validate
UTC=dt.timezone.utc
FLOW_URL='https://farside.co.uk/bitcoin-etf-flow-all-data/'
BI='https://data-api.binance.vision/api/v3/klines'
def stamp(y,m=1,d=1):return int(dt.datetime(y,m,d,tzinfo=UTC).timestamp()*1000)
def get(url,p):
    if not p.exists():
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'xrp-research/1.0'}),timeout=180) as r:p.write_bytes(r.read())
    return p.read_bytes()
def load_flows(cache):
    p=cache/'farside-btc-etf-all-data.html';raw=get(FLOW_URL,p);all_rows=parse_farside_html(raw);cut=stamp(2026,10);rows=[x for x in all_rows if x['timestamp']<cut and x['total_flow'] is not None]
    missing=[x['date'] for x in all_rows if x['timestamp']<cut and x['total_flow'] is None]
    return rows,dict(kind='farside_BTC_ETF_daily_flows',url=FLOW_URL,cache_file=p.name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),rows_all=len(all_rows),rows_used=len(rows),missing_total_dates=missing)
def load_prices(cache):
    start=stamp(2024);end=stamp(2026,10)-1;cursor=start;page=0;rows=[];man=[]
    while cursor<=end:
        q=urllib.parse.urlencode(dict(symbol='XRPUSDT',interval='1d',startTime=cursor,endTime=end,limit=1000));url=BI+'?'+q;p=cache/f'XRPUSDT-1d-etf-api-{page}.json';raw=get(url,p);doc=json.loads(raw);man.append(dict(kind='binance_XRPUSDT_1d',url=url,cache_file=p.name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),rows=len(doc)))
        if not doc:break
        rows += [dict(timestamp=int(x[0]),open=float(x[1]),high=float(x[2]),low=float(x[3]),close=float(x[4])) for x in doc];cursor=int(doc[-1][0])+DAY;page+=1
        if len(doc)<1000:break
    return rows,man
def metrics(t,c,initial=10000.):
    w=sum(max(0,x['pnl']) for x in t);l=-sum(min(0,x['pnl']) for x in t);n=sum(x['pnl'] for x in t);peak=initial;dd=0
    for x in c:peak=max(peak,x['equity']);dd=max(dd,(peak-x['equity'])/peak*100)
    return dict(trades=len(t),net_pnl=n,net_return_pct=n/initial*100,profit_factor=w/l if l else None,expectancy=n/len(t) if t else None,max_drawdown_pct=dd,fees=sum(x['fees'] for x in t),slippage_cost=sum(x['slippage_cost'] for x in t),gross_profit=w,gross_loss=l)
def main():
    cache=pathlib.Path(sys.argv[1]);dest=pathlib.Path(sys.argv[2]);cache.mkdir(parents=True,exist_ok=True);dest.mkdir(parents=True,exist_ok=True);flows,fm=load_flows(cache);rows,pm=load_prices(cache);validate(rows);signals=make_signals(flows)
    for x in rows:
        if x['timestamp'] in signals:x['etf_signal']=signals[x['timestamp']]
    folds=[('2024_H1_control',stamp(2024,1,11),stamp(2024,7)),('2024_H2',stamp(2024,7),stamp(2025)),('2025_H1',stamp(2025),stamp(2025,7)),('2025_H2',stamp(2025,7),stamp(2026)),('2026_H1',stamp(2026),stamp(2026,7)),('2026_Q3',stamp(2026,7),stamp(2026,10)),('continuous_oos',stamp(2024,7),stamp(2026,10))];runs={};ledgers={}
    for name,start,end in folds:
        for label,mul in (('base',1),('stress',2)):
            c=replace(Config(),fee=Config().fee*mul,slippage=Config().slippage*mul);t,curve=backtest(rows,start,end,c);key=name+'_'+label;ledgers[key]=t;runs[key]=metrics(t,curve);print(key,runs[key],flush=True)
    periods=['2024_H2','2025_H1','2025_H2','2026_H1','2026_Q3'];base=[x for p in periods for x in ledgers[p+'_base']];stress=[x for p in periods for x in ledgers[p+'_stress']];agg=metrics(base,[]);aggs=metrics(stress,[]);agg['max_drawdown_pct']=None;aggs['max_drawdown_pct']=None;by={p:runs[p+'_base']['net_pnl'] for p in periods};bys={p:runs[p+'_stress']['net_pnl'] for p in periods};monthly={}
    for x in base:
        k=dt.datetime.fromtimestamp(x['exit_timestamp']/1000,UTC).strftime('%Y-%m');monthly[k]=monthly.get(k,0)+x['pnl']
    positive=sum(max(0,v) for v in monthly.values());share=max((max(0,v)/positive for v in monthly.values()),default=1)
    gates=dict(sample=agg['trades']>=100,base_net=agg['net_pnl']>0,base_expectancy=(agg['expectancy'] or 0)>0,base_pf=(agg['profit_factor'] or 0)>1.20,stress_net=aggs['net_pnl']>0,stress_expectancy=(aggs['expectancy'] or 0)>0,stress_pf=(aggs['profit_factor'] or 0)>1.05,four_periods=sum(v>0 for v in by.values())>=4,four_periods_stress=sum(v>0 for v in bys.values())>=4,final_period=by['2026_Q3']>0 and bys['2026_Q3']>0,drawdown=max(runs['continuous_oos_base']['max_drawdown_pct'],runs['continuous_oos_stress']['max_drawdown_pct'])<=10,concentration=agg['net_pnl']>0 and positive>0 and share<=.25,audit=False,forward_paper=False)
    hist=all(v for k,v in gates.items() if k not in ('audit','forward_paper'));proto=pathlib.Path('research/btc_etf_creation_impulse_protocol_20261030.md');sig_period={p:sum(start<=t<end for t in signals) for p,start,end in [(x[0],x[1],x[2]) for x in folds[:-1]]}
    flow_gaps=[(flows[i-1]['date'],flows[i]['date'],(flows[i]['timestamp']-flows[i-1]['timestamp'])//DAY) for i in range(1,len(flows)) if flows[i]['timestamp']-flows[i-1]['timestamp']>4*DAY]
    price_gaps=[(a['timestamp'],b['timestamp']) for a,b in zip(rows,rows[1:]) if b['timestamp']-a['timestamp']!=DAY]
    res=dict(strategy='BTC_ETF_CREATION_IMPULSE_XRP_V1',status='TEST NEDOKONCEN: audit and forward PAPER required' if hist else 'NEPROSEL',protocol_sha256=hashlib.sha256(proto.read_bytes()).hexdigest(),manifest=[fm]+pm,data_quality=dict(flow_rows=len(flows),flow_start=flows[0]['timestamp'],flow_end=flows[-1]['timestamp'],flow_long_gaps=flow_gaps,price_rows=len(rows),price_start=rows[0]['timestamp'],price_end=rows[-1]['timestamp'],price_gaps=price_gaps),signals_total=len(signals),signals_by_period=sig_period,runs=runs,aggregate_oos=agg,aggregate_stress=aggs,by_period=by,stress_by_period=bys,monthly_base=monthly,positive_month_profit_concentration=share,gates=gates,historical_pass_before_audit=hist,limitations=['Farside is a third-party compilation, not an issuer filing or audited primary source.','Historical release times are unavailable; the frozen D+2 entry is a conservative timing assumption.','The source begins in January 2024, limiting independent market regimes and full calendar years.','Daily XRP OHLC cannot reconstruct tick paths; fixed conservative gap/stop rules apply.','Local SHA256 values are not publisher signatures.','No independent forward PAPER evidence exists.']);(dest/'results.json').write_text(json.dumps(res,indent=2,allow_nan=False)+'\n')
    with gzip.open(dest/'trades.json.gz','wt') as h:json.dump(ledgers,h)
    print(res['status'],gates,sig_period,flush=True)
if __name__=='__main__':main()
