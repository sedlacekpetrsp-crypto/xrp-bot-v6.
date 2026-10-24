"""Offline, fixed-parameter chronological validation. No production imports."""
import concurrent.futures, csv, hashlib, io, json, pathlib, sys, urllib.request, zipfile
from datetime import datetime, timezone
from dataclasses import replace
from research.autocorr_regime_v1 import Config, backtest, validate
from research.fetch_binance_klines import MONTHS

def stamp(y,m):
    return int(datetime(y,m,1,tzinfo=timezone.utc).timestamp()*1000)

def fetch(job):
    symbol,y,m,cache=job
    name=f'{symbol}-15m-{y}-{m:02d}.zip'
    url=f'https://data.binance.vision/data/spot/monthly/klines/{symbol}/15m/{name}'
    path=cache/name
    if not path.exists():
        with urllib.request.urlopen(url,timeout=45) as r: payload=r.read()
        path.write_bytes(payload)
    payload=path.read_bytes()
    start=stamp(y,m); end=stamp(y+1,1) if m==12 else stamp(y,m+1)
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        names=z.namelist()
        if names != [name[:-4]+'.csv']: raise ValueError('Unexpected archive members')
        rows=list(csv.reader(io.TextIOWrapper(z.open(names[0]))))
    bars=[]
    for r in rows:
        t=int(r[0]); t=t//1000 if t>10**14 else t
        bars.append(dict(timestamp=t,**dict(zip(('open','high','low','close'),map(float,r[1:5])))))
    validate(bars)
    if len(bars)!=(end-start)//900000 or bars[0]['timestamp']!=start or bars[-1]['timestamp']!=end-900000:
        raise ValueError('Incomplete monthly archive')
    return bars,dict(url=url,sha256=hashlib.sha256(payload).hexdigest(),bars=len(bars))

def metrics(bars,trades,initial,c):
    win=sum(max(0,t['pnl']) for t in trades); loss=-sum(min(0,t['pnl']) for t in trades)
    monthly={}; peak=initial; dd=0.; cash=initial; byentry={t['entry_index']:t for t in trades}; active=None
    for i,b in enumerate(bars):
        if i in byentry: active=byentry[i]
        equity=cash
        if active:
            # Conservative intrabar low valuation, with liquidation costs.
            mark=b['low']*(1-c.slippage)
            equity=cash+active['qty']*(mark-active['entry'])-c.fee*active['qty']*(active['entry']+mark)
            close_mark=b['close']*(1-c.slippage)
            close_equity=cash+active['qty']*(close_mark-active['entry'])-c.fee*active['qty']*(active['entry']+close_mark)
            if i==active['exit_index']:
                cash+=active['pnl']; active=None;close_equity=cash
        dd=max(dd,(peak-equity)/peak); peak=max(peak,cash,close_equity if active else cash)
    for t in trades:
        month=datetime.fromtimestamp(bars[t['exit_index']]['timestamp']/1000,timezone.utc).strftime('%Y-%m')
        monthly[month]=monthly.get(month,0)+t['pnl']
    net=win-loss
    return dict(trades=len(trades),net_pnl=net,return_pct=net/initial*100,profit_factor=win/loss if loss else None,expectancy=net/len(trades) if trades else None,max_drawdown_pct=dd*100,monthly_net=monthly,fees=sum(c.fee*t['qty']*(t['entry']+t['exit']) for t in trades),gross_before_fees_and_slippage=sum(t['qty']*(t['exit']/(1-c.slippage)-t['entry']/(1+c.slippage)) for t in trades))

def main(backtester=backtest,strategy="AUTOCORR_REGIME_SWITCH_V1",warmup=97):
    cache=pathlib.Path(sys.argv[1]);cache.mkdir(parents=True,exist_ok=True)
    dest=pathlib.Path(sys.argv[2]);dest.mkdir(parents=True,exist_ok=True)
    results={'strategy':strategy,'status':'TEST NEDOKONCEN','manifest':[],'runs':{},'capital_policy':'Two isolated $5000 sleeves, each capped at 20% sleeve equity; combined gross <=20% total equity. No tuning. OOS starts flat; autocorr uses 97 prior warmup bars, calendar strategy none.','limitations':['Exploratory OOS: these dates were inspected in prior projects.','Intrabar drawdown conservatively uses entire exit candle low.','No independent forward paper validation yet.']}
    alltrades={}
    for symbol in ('XRPUSDT','ETHUSDT'):
        jobs=[(symbol,y,m,cache) for y,m in MONTHS]
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool: chunks=list(pool.map(fetch,jobs))
        bars=[b for chunk,_ in chunks for b in chunk];validate(bars)
        results['manifest'] += [manifest for _,manifest in chunks]
        split=next(i for i,b in enumerate(bars) if b['timestamp']>=stamp(2026,7))
        for period,data in [('train',bars[:split]),('oos',bars[split-warmup:])]:
            for cost,mult in [('base',1),('stress',2)]:
                c=replace(Config(),fee=Config().fee*mult,slippage=Config().slippage*mult)
                trades=backtester(data,c,5000.)
                key=f'{symbol}_{period}_{cost}'
                results['runs'][key]=metrics(data,trades,5000.,c)
                alltrades[key]=[dict(t,entry_timestamp=data[t['entry_index']]['timestamp'],exit_timestamp=data[t['exit_index']]['timestamp']) for t in trades]
                print(key,json.dumps(results['runs'][key]),flush=True)
    base=[results['runs'][f'{s}_oos_base'] for s in ('XRPUSDT','ETHUSDT')]
    stress=[results['runs'][f'{s}_oos_stress'] for s in ('XRPUSDT','ETHUSDT')]
    months={}
    for r in base:
        for k,v in r['monthly_net'].items(): months[k]=months.get(k,0)+v
    total=sum(r['net_pnl'] for r in base)
    gates={'at_least_100_oos_trades':sum(r['trades'] for r in base)>=100,'both_symbols_profitable':all(r['net_pnl']>0 for r in base),'both_base_pf_above_1_2':all((r['profit_factor'] or 0)>1.2 for r in base),'both_stress_pf_above_1_05':all((r['profit_factor'] or 0)>1.05 for r in stress),'drawdown_at_most_10_pct':all(r['max_drawdown_pct']<=10 for r in base+stress),'monthly_profit_concentration':total>0 and max(months.values(),default=0)<=.5*total}
    results['gates']=gates
    results['status']='NEPROSEL' if not all(gates.values()) else 'TEST NEDOKONCEN: forward validation required'
    (dest/'results.json').write_text(json.dumps(results,indent=2,allow_nan=False)+'\n')
    import gzip
    with gzip.open(dest/'trades.json.gz','wt') as f: json.dump(alltrades,f)
    print(results['status'],gates)
if __name__=='__main__':main()
