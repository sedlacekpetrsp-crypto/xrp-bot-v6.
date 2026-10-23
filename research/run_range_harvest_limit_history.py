"""Historical runner for RANGE_HARVEST_LIMIT_V1."""
import csv,hashlib,io,json,urllib.request,zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from pathlib import Path
from research.range_harvest_limit_v1 import Config,DAY_MS,backtest,with_taker_stress

SYMBOL='BTCUSDT'
MONTHS=[(y,m) for y in range(2020,2027) for m in range(1,13) if (2020,9)<=(y,m)<=(2026,9)]
DEV=(("2021","2021-01-01","2022-01-01"),("2022","2022-01-01","2023-01-01"))
VAL=(("2023","2023-01-01","2024-01-01"),("2024","2024-01-01","2025-01-01"),
     ("2025","2025-01-01","2026-01-01"),("2026_JAN_SEP","2026-01-01","2026-10-01"))

def timestamp(s): return int(datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp()*1000)
def fetch(item):
    y,m=item; fn=f'{SYMBOL}-1h-{y}-{m:02d}.zip'; url=f'https://data.binance.vision/data/spot/monthly/klines/{SYMBOL}/1h/{fn}'
    req=urllib.request.Request(url,headers={'User-Agent':'range-harvest-limit/1.0'})
    with urllib.request.urlopen(req,timeout=90) as response: payload=response.read()
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names=[n for n in archive.namelist() if n.endswith('.csv')]
        if len(names)!=1: raise ValueError(fn)
        rows=list(csv.reader(io.TextIOWrapper(archive.open(names[0]),encoding='utf-8')))
    bars=[]
    for row in rows:
        if not row or not row[0].isdigit(): continue
        ts=int(row[0]); ts=ts//1000 if ts>10**14 else ts
        bars.append({'timestamp':ts,'open':float(row[1]),'high':float(row[2]),'low':float(row[3]),'close':float(row[4]),'volume':float(row[5])})
    start=timestamp(f'{y}-{m:02d}-01'); ny,nm=(y+1,1) if m==12 else (y,m+1)
    expected=set(range(start,timestamp(f'{ny}-{nm:02d}-01'),3_600_000)); stamps=[b['timestamp'] for b in bars]
    if not stamps or stamps!=sorted(set(stamps)) or not set(stamps)<=expected: raise ValueError(fn)
    missing=sorted(expected-set(stamps))
    return bars,{'symbol':SYMBOL,'url':url,'sha256':hashlib.sha256(payload).hexdigest(),'bars':len(bars),
                 'expected_bars':len(expected),'missing_bars':len(missing),'first_missing_timestamp':missing[0] if missing else None}
def metrics(result):
    trades=result['trades']; profit=sum(max(0,t['net_pnl']) for t in trades); loss=-sum(min(0,t['net_pnl']) for t in trades)
    return {'trades':len(trades),'win_rate':sum(t['net_pnl']>0 for t in trades)/len(trades) if trades else None,
            'net_return':result['net_return'],'net_pnl':result['ending_equity']-10000,
            'profit_factor':profit/loss if loss else None,'max_drawdown':result['max_drawdown'],
            'fees':sum(t['fees'] for t in trades)}
def evaluate(bars,blocks,config): return {n:metrics(backtest(bars,timestamp(a),timestamp(b),config)) for n,a,b in blocks}
def main():
    with ThreadPoolExecutor(max_workers=8) as pool: parts=list(pool.map(fetch,MONTHS))
    bars=[b for p,_ in parts for b in p]; manifest=[x for _,x in parts]; counts={}
    for b in bars:
        d=b['timestamp']//DAY_MS*DAY_MS; counts[d]=counts.get(d,0)+1
    complete={d for d,c in counts.items() if c==24}; dropped=sorted(set(counts)-complete)
    bars=[b for b in bars if b['timestamp']//DAY_MS*DAY_MS in complete]
    config=Config(); dev=evaluate(bars,DEV,config); dev2=evaluate(bars,DEV,with_taker_stress(config))
    val=evaluate(bars,VAL,config); val2=evaluate(bars,VAL,with_taker_stress(config))
    val['ALL']=metrics(backtest(bars,timestamp('2023-01-01'),timestamp('2026-10-01'),config))
    val2['ALL']=metrics(backtest(bars,timestamp('2023-01-01'),timestamp('2026-10-01'),with_taker_stress(config)))
    positive=sum(max(0,val[n]['net_pnl']) for n,*_ in VAL); share=max(max(0,val[n]['net_pnl']) for n,*_ in VAL)/positive if positive else 1
    gate={'development_positive':all(dev[n]['net_return']>0 for n,*_ in DEV),'validation_minimum_trades':val['ALL']['trades']>=150,
          'normal_pf':(val['ALL']['profit_factor'] or 0)>=1.20,'stress_pf':(val2['ALL']['profit_factor'] or 0)>=1.05,
          'normal_positive_all_blocks':all(val[n]['net_return']>0 for n,*_ in VAL),
          'stress_positive_three_blocks':sum(val2[n]['net_return']>0 for n,*_ in VAL)>=3,
          'stress_total_positive':val2['ALL']['net_return']>0,'max_drawdown':val['ALL']['max_drawdown']<=0.15,
          'profit_not_concentrated':share<=0.60,'forward_paper_50_trades':False}
    report={'strategy':'RANGE_HARVEST_LIMIT_V1','data':'Binance BTCUSDT spot 1h monthly archives',
            'development_period':'2021-01-01/2022-12-31','validation_period':'2023-01-01/2026-09-30',
            'config':config.__dict__,'taker_stress_config':with_taker_stress(config).__dict__,'development':dev,
            'development_taker_stress':dev2,'validation':val,'validation_taker_stress':val2,
            'largest_positive_validation_block_share':share,'gate':gate,
            'passes_historical_gate':all(v for k,v in gate.items() if k!='forward_paper_50_trades'),
            'robust_candidate':all(gate.values()),'coverage':{'complete_days':len(complete),'dropped_incomplete_days':dropped},
            'manifest':manifest,'limitations':['Hourly OHLC cannot reveal limit/stop path; same-bar rules are conservative.',
            'Maker queue position and partial fills are not modeled.','One venue may not generalize.',
            'Historical passage would still require 50 new forward PAPER trades.']}
    Path('research/range_harvest_limit_results_20261023.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='manifest'},indent=2))
if __name__=='__main__': main()
