"""Real-archive chronological evaluation for the frozen lead/lag protocol."""
import concurrent.futures,gzip,hashlib,json,pathlib,sys
from dataclasses import replace
from research.btc_lead_lag_v1 import Config,backtest,validate
from research.run_relative_strength import fetch
from research.run_autocorr_history import metrics,stamp

def aggregate(ts):
    pos=sum(max(0,t['pnl']) for t in ts);neg=-sum(min(0,t['pnl']) for t in ts)
    return dict(trades=len(ts),net_pnl=pos-neg,profit_factor=pos/neg if neg else None,
                expectancy=(pos-neg)/len(ts) if ts else None)

def main():
    cache=pathlib.Path(sys.argv[1]);cache.mkdir(parents=True,exist_ok=True)
    dest=pathlib.Path(sys.argv[2]);dest.mkdir(parents=True,exist_ok=True)
    months=[(y,m) for y in range(2022,2027) for m in range(1,13) if (y,m)<(2026,10)]
    jobs=[(s,y,m,cache) for s in ('BTCUSDT','XRPUSDT') for y,m in months]
    markets={s:[] for s in ('BTCUSDT','XRPUSDT')};manifest=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        for n,(s,bars,source) in enumerate(pool.map(fetch,jobs),1):
            markets[s]+=bars;manifest.append(source)
            if n%12==0:print('Validated archives',n,'/',len(jobs),flush=True)
    common=set.intersection(*(set(b['timestamp'] for b in bars) for bars in markets.values()))
    omitted={s:[b['timestamp'] for b in bars if b['timestamp'] not in common] for s,bars in markets.items()}
    markets={s:[b for b in bars if b['timestamp'] in common] for s,bars in markets.items()};validate(markets)
    bars=markets['XRPUSDT'];runs={};ledger={}
    folds=[('2022_control',stamp(2022,1),stamp(2023,1))]
    folds += [(str(y),stamp(y,1),stamp(y+1,1) if y<2026 else stamp(2026,10)) for y in range(2023,2027)]
    folds += [('continuous_oos',stamp(2023,1),stamp(2026,10))]
    for name,start,end in folds:
        for cost,mult in [('base',1),('stress',2)]:
            c=replace(Config(),fee=Config().fee*mult,slippage=Config().slippage*mult)
            ts=backtest(markets,start,end,c);key=f'{name}_{cost}'
            runs[key]=metrics(bars,ts,10_000.,c)
            runs[key]['slippage_cost']=sum(t['slippage_cost'] for t in ts)
            ledger[key]=[dict(t,entry_timestamp=bars[t['entry_index']]['timestamp'],exit_timestamp=bars[t['exit_index']]['timestamp']) for t in ts]
            print(key,json.dumps(runs[key]),flush=True)
    base=[t for y in range(2023,2027) for t in ledger[f'{y}_base']]
    stress=[t for y in range(2023,2027) for t in ledger[f'{y}_stress']]
    a,b=aggregate(base),aggregate(stress);monthly={}
    for y in range(2023,2027):
        for month,pnl in runs[f'{y}_base']['monthly_net'].items():monthly[month]=pnl
    gates=dict(sample=a['trades']>=120,base_net=a['net_pnl']>0,base_expectancy=(a['expectancy'] or 0)>0,
               base_pf=(a['profit_factor'] or 0)>1.15,stress_net=b['net_pnl']>0,
               stress_expectancy=(b['expectancy'] or 0)>0,stress_pf=(b['profit_factor'] or 0)>1.02,
               three_positive_folds=sum(runs[f'{y}_base']['net_pnl']>0 for y in range(2023,2027))>=3,
               final_fold=runs['2026_base']['net_pnl']>0,
               drawdown=all(runs[f'continuous_oos_{x}']['max_drawdown_pct']<=10 for x in ('base','stress')),
               concentration=a['net_pnl']>0 and max(monthly.values(),default=0)<=.4*a['net_pnl'])
    protocol=pathlib.Path('research/btc_lead_lag_protocol.md')
    result=dict(strategy='BTC_LEAD_LAG_IMPULSE_V1',status='NEPROSEL' if not all(gates.values()) else 'TEST NEDOKONCEN: forward evidence required',
                protocol=str(protocol),protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),manifest=manifest,
                alignment_omissions=omitted,runs=runs,aggregate_oos=a,aggregate_stress=b,gates=gates,
                limitations=['Exploratory previously inspected history, not untouched validation.','Local SHA256 fingerprints are not publisher signatures.','OHLC bracket path and conservative candle-low drawdown are not tick-exact.','No independent future PAPER evidence.'])
    (dest/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    with gzip.open(dest/'trades.json.gz','wt') as f:json.dump(ledger,f)
    print(result['status'],json.dumps(gates),flush=True)

if __name__=='__main__':main()
