"""Historical runner for BETA_HEDGED_RESIDUAL_MOMENTUM_V1."""
import csv, hashlib, io, json, urllib.request, zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from research.beta_hedged_residual_momentum_v1 import Config, DAY_MS, SYMBOLS, backtest, with_double_costs

MONTHS=[(y,m) for y in range(2020,2027) for m in range(1,13) if (2020,9)<=(y,m)<=(2026,9)]
DEVELOPMENT=(("2021","2021-01-01","2022-01-01"),("2022","2022-01-01","2023-01-01"))
VALIDATION=(("2023","2023-01-01","2024-01-01"),("2024","2024-01-01","2025-01-01"),
            ("2025","2025-01-01","2026-01-01"),("2026_JAN_SEP","2026-01-01","2026-10-01"))

def timestamp(text):
    return int(datetime.fromisoformat(text).replace(tzinfo=timezone.utc).timestamp()*1000)

def fetch(item):
    symbol,year,month=item; filename=f"{symbol}-1h-{year}-{month:02d}.zip"
    url=f"https://data.binance.vision/data/spot/monthly/klines/{symbol}/1h/{filename}"
    request=urllib.request.Request(url,headers={"User-Agent":"beta-hedged-residual/1.0"})
    with urllib.request.urlopen(request,timeout=90) as response: payload=response.read()
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names=[name for name in archive.namelist() if name.endswith('.csv')]
        if len(names)!=1: raise ValueError(f"Unexpected archive: {filename}")
        rows=list(csv.reader(io.TextIOWrapper(archive.open(names[0]),encoding='utf-8')))
    bars=[]
    for row in rows:
        if not row or not row[0].isdigit(): continue
        stamp=int(row[0]); stamp=stamp//1000 if stamp>10**14 else stamp
        bars.append({"timestamp":stamp,"open":float(row[1]),"high":float(row[2]),
                     "low":float(row[3]),"close":float(row[4]),"volume":float(row[5])})
    start=timestamp(f"{year}-{month:02d}-01"); ny,nm=(year+1,1) if month==12 else (year,month+1)
    expected=set(range(start,timestamp(f"{ny}-{nm:02d}-01"),3_600_000)); stamps=[b['timestamp'] for b in bars]
    if not stamps or stamps!=sorted(set(stamps)) or not set(stamps)<=expected:
        raise ValueError(f"Invalid archive: {filename}")
    missing=sorted(expected-set(stamps))
    return symbol,bars,{"symbol":symbol,"url":url,"sha256":hashlib.sha256(payload).hexdigest(),
                        "bars":len(bars),"expected_bars":len(expected),"missing_bars":len(missing),
                        "first_missing_timestamp":missing[0] if missing else None}

def metrics(result):
    trades=result['trades']; profit=sum(max(0,t['net_pnl']) for t in trades); loss=-sum(min(0,t['net_pnl']) for t in trades)
    return {"trades":len(trades),"alt_long":sum(t['direction']=='ALT_LONG' for t in trades),
            "alt_short":sum(t['direction']=='ALT_SHORT' for t in trades),
            "win_rate":sum(t['net_pnl']>0 for t in trades)/len(trades) if trades else None,
            "net_return":result['net_return'],"net_pnl":result['ending_equity']-10000,
            "profit_factor":profit/loss if loss else None,"max_drawdown":result['max_drawdown'],
            "fees":sum(t['fees'] for t in trades),"borrow_cost":sum(t['borrow_cost'] for t in trades)}

def evaluate(market,blocks,config):
    return {name:metrics(backtest(market,timestamp(start),timestamp(end),config)) for name,start,end in blocks}

def main():
    jobs=[(s,y,m) for s in SYMBOLS for y,m in MONTHS]
    with ThreadPoolExecutor(max_workers=12) as pool: parts=list(pool.map(fetch,jobs))
    market={s:[] for s in SYMBOLS}; manifest=[]
    for symbol,bars,item in parts: market[symbol].extend(bars); manifest.append(item)
    complete={}; observed=set()
    for symbol,bars in market.items():
        counts={}
        for bar in bars:
            day=bar['timestamp']//DAY_MS*DAY_MS; counts[day]=counts.get(day,0)+1
        observed.update(counts); complete[symbol]={d for d,c in counts.items() if c==24}
    common=set.intersection(*complete.values()); dropped=sorted(observed-common)
    market={s:[b for b in bars if b['timestamp']//DAY_MS*DAY_MS in common] for s,bars in market.items()}
    config=Config(); dev=evaluate(market,DEVELOPMENT,config); dev2=evaluate(market,DEVELOPMENT,with_double_costs(config))
    val=evaluate(market,VALIDATION,config); val2=evaluate(market,VALIDATION,with_double_costs(config))
    val['ALL']=metrics(backtest(market,timestamp('2023-01-01'),timestamp('2026-10-01'),config))
    val2['ALL']=metrics(backtest(market,timestamp('2023-01-01'),timestamp('2026-10-01'),with_double_costs(config)))
    positive=sum(max(0,val[n]['net_pnl']) for n,*_ in VALIDATION)
    share=max(max(0,val[n]['net_pnl']) for n,*_ in VALIDATION)/positive if positive else 1.0
    gate={"development_positive":all(dev[n]['net_return']>0 for n,*_ in DEVELOPMENT),
          "validation_minimum_trades":val['ALL']['trades']>=80,
          "both_directions_sampled":val['ALL']['alt_long']>=20 and val['ALL']['alt_short']>=20,
          "normal_pf":(val['ALL']['profit_factor'] or 0)>=1.25,"stress_pf":(val2['ALL']['profit_factor'] or 0)>=1.10,
          "normal_positive_all_blocks":all(val[n]['net_return']>0 for n,*_ in VALIDATION),
          "stress_positive_three_blocks":sum(val2[n]['net_return']>0 for n,*_ in VALIDATION)>=3,
          "stress_total_positive":val2['ALL']['net_return']>0,"max_drawdown":val['ALL']['max_drawdown']<=0.15,
          "profit_not_concentrated":share<=0.60,"forward_paper_30_pairs":False}
    report={"strategy":"BETA_HEDGED_RESIDUAL_MOMENTUM_V1","data":"Binance spot 1h monthly archives",
            "development_period":"2021-01-01/2022-12-31","validation_period":"2023-01-01/2026-09-30",
            "config":config.__dict__,"development":dev,"development_double_costs":dev2,
            "validation":val,"validation_double_costs":val2,"largest_positive_validation_block_share":share,
            "gate":gate,"passes_historical_gate":all(v for k,v in gate.items() if k!='forward_paper_30_pairs'),
            "robust_candidate":all(gate.values()),"coverage":{"common_complete_days":len(common),
            "dropped_incomplete_or_unaligned_days":dropped},"manifest":manifest,
            "limitations":["Spot candles proxy short execution and not borrow availability.",
            "Daily beta is unstable in fast regimes.","Intrabar co-leg exit uses adverse hourly extreme.",
            "Historical passage would still require 30 new forward PAPER pairs."]}
    Path('research/beta_hedged_residual_results_20261023.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='manifest'},indent=2))

if __name__=='__main__': main()
