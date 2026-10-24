"""Historical runner for TRIANGULAR_PARITY_V1."""
import csv,hashlib,io,json,urllib.request,zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from pathlib import Path
from research.triangular_parity_v1 import BAR_MS,Config,backtest,with_cost_stress

SYMBOLS=("BTCUSDT","ETHUSDT","ETHBTC")
MONTHS=[(y,m) for y in range(2022,2027) for m in range(1,13) if (2022,12)<=(y,m)<=(2026,9)]
DEV=(("2023","2023-01-01","2024-01-01"),)
VAL=(("2024_H1","2024-01-01","2024-07-01"),("2024_H2","2024-07-01","2025-01-01"),
     ("2025_H1","2025-01-01","2025-07-01"),("2025_H2","2025-07-01","2026-01-01"),
     ("2026_JAN_SEP","2026-01-01","2026-10-01"))


def timestamp(value): return int(datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp()*1000)


def download(symbol,item):
    y,m=item; filename=f"{symbol}-5m-{y}-{m:02d}.zip"; url=f"https://data.binance.vision/data/spot/monthly/klines/{symbol}/5m/{filename}"
    request=urllib.request.Request(url,headers={"User-Agent":"triangular-parity/1.0"})
    with urllib.request.urlopen(request,timeout=90) as response: payload=response.read()
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names=[name for name in archive.namelist() if name.endswith('.csv')]
        if len(names)!=1: raise ValueError(url)
        rows=list(csv.reader(io.TextIOWrapper(archive.open(names[0]),encoding='utf-8')))
    data={}
    for row in rows:
        if row and row[0].isdigit():
            stamp=int(row[0]); stamp=stamp//1000 if stamp>10**14 else stamp
            data[stamp]=(float(row[1]),float(row[4]))
    return data,{"symbol":symbol,"url":url,"sha256":hashlib.sha256(payload).hexdigest(),"bars":len(data)}


def fetch(item):
    pieces=[download(symbol,item) for symbol in SYMBOLS]; maps=[piece[0] for piece in pieces]; common=sorted(set(maps[0])&set(maps[1])&set(maps[2]))
    bars=[]
    for ts in common:
        bars.append({"timestamp":ts,"btcusdt_open":maps[0][ts][0],"btcusdt_close":maps[0][ts][1],
                     "ethusdt_open":maps[1][ts][0],"ethusdt_close":maps[1][ts][1],
                     "ethbtc_open":maps[2][ts][0],"ethbtc_close":maps[2][ts][1]})
    y,m=item; start=timestamp(f"{y}-{m:02d}-01"); ny,nm=(y+1,1) if m==12 else (y,m+1)
    expected=set(range(start,timestamp(f"{ny}-{nm:02d}-01"),BAR_MS)); missing=sorted(expected-set(common))
    return bars,[piece[1] for piece in pieces],{"month":f"{y}-{m:02d}","expected":len(expected),"synchronized":len(common),
                                                "missing_synchronized":len(missing),"first_missing":missing[0] if missing else None}


def metrics(result):
    trades=result['trades']; profit=sum(max(0,t['net_pnl']) for t in trades); loss=-sum(min(0,t['net_pnl']) for t in trades)
    return {"trades":len(trades),"forward":sum(t['route']=="USDT_BTC_ETH_USDT" for t in trades),
            "reverse":sum(t['route']=="USDT_ETH_BTC_USDT" for t in trades),"win_rate":sum(t['net_pnl']>0 for t in trades)/len(trades) if trades else None,
            "net_return":result['net_return'],"net_pnl":result['ending_equity']-10000,"profit_factor":profit/loss if loss else None,
            "max_drawdown":result['max_drawdown']}


def evaluate(bars,blocks,config): return {name:metrics(backtest(bars,timestamp(start),timestamp(end),config)) for name,start,end in blocks}


def main():
    with ThreadPoolExecutor(max_workers=8) as pool: parts=list(pool.map(fetch,MONTHS))
    bars=[bar for part,_,_ in parts for bar in part]; manifest=[entry for _,entries,_ in parts for entry in entries]; coverage=[c for _,_,c in parts]
    config=Config(); stress=with_cost_stress(config); dev=evaluate(bars,DEV,config); dev_stress=evaluate(bars,DEV,stress)
    val=evaluate(bars,VAL,config); val_stress=evaluate(bars,VAL,stress)
    val['ALL']=metrics(backtest(bars,timestamp('2024-01-01'),timestamp('2026-10-01'),config)); val_stress['ALL']=metrics(backtest(bars,timestamp('2024-01-01'),timestamp('2026-10-01'),stress))
    positive=sum(max(0,val[name]['net_pnl']) for name,*_ in VAL); share=max((max(0,val[name]['net_pnl']) for name,*_ in VAL),default=0)/positive if positive else 1
    count=val['ALL']['trades']; balance=min(val['ALL']['forward'],val['ALL']['reverse'])/count if count else 0
    gate={"development_2023_positive":dev['2023']['net_return']>0,"validation_minimum_100_cycles":count>=100,
          "both_routes_at_least_20pct":balance>=0.20,"normal_pf_at_least_1_20":(val['ALL']['profit_factor'] or 0)>=1.20,
          "stress_pf_at_least_1_05":(val_stress['ALL']['profit_factor'] or 0)>=1.05,
          "normal_positive_all_blocks":all(val[name]['net_return']>0 for name,*_ in VAL),
          "stress_positive_four_blocks":sum(val_stress[name]['net_return']>0 for name,*_ in VAL)>=4,
          "stress_total_positive":val_stress['ALL']['net_return']>0,"normal_max_drawdown_at_most_5pct":val['ALL']['max_drawdown']<=0.05,
          "profit_not_concentrated":share<=0.50,"forward_paper_100_cycles":False}
    report={"strategy":"TRIANGULAR_PARITY_V1","data":"Binance BTCUSDT, ETHUSDT and ETHBTC spot 5m monthly archives",
            "development_period":"2023-01-01/2023-12-31","validation_period":"2024-01-01/2026-09-30","config":config.__dict__,"stress_config":stress.__dict__,
            "development":dev,"development_stress":dev_stress,"validation":val,"validation_stress":val_stress,
            "largest_positive_validation_block_share":share,"smaller_route_share":balance,"gate":gate,
            "passes_historical_gate":all(v for k,v in gate.items() if k!='forward_paper_100_cycles'),"robust_candidate":all(gate.values()),
            "coverage":coverage,"manifest":manifest,
            "limitations":["Three sequential legs are modeled at one synchronized open; real leg latency and partial fills can be worse.",
                           "Signal-to-execution gap is fully realized; there is no held position requiring a stop.",
                           "OHLC bars do not provide executable order-book depth.","Historical passage would still require 100 new forward PAPER cycles."]}
    Path('research/triangular_parity_results_20261024.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='manifest'},indent=2))


if __name__=='__main__': main()
