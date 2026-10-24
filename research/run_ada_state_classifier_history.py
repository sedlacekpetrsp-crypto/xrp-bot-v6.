"""Frozen train/development/validation runner for ADA_STATE_CLASSIFIER_V1."""
import csv, hashlib, io, json, urllib.request, zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from research.ada_state_classifier_v1 import BAR_MS, Config, backtest, feature_at, resample_4h, with_cost_stress

SYMBOL="ADAUSDT"; HOUR_MS=3_600_000
MONTHS=[(y,m) for y in range(2020,2027) for m in range(1,13) if (2020,12)<=(y,m)<=(2026,9)]
DEV=(("2023","2023-01-01","2024-01-01"),)
VAL=(("2024_H1","2024-01-01","2024-07-01"),("2024_H2","2024-07-01","2025-01-01"),
     ("2025_H1","2025-01-01","2025-07-01"),("2025_H2","2025-07-01","2026-01-01"),
     ("2026_JAN_SEP","2026-01-01","2026-10-01"))


def timestamp(value): return int(datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp()*1000)


def fetch(item):
    y,m=item; filename=f"{SYMBOL}-1h-{y}-{m:02d}.zip"; url=f"https://data.binance.vision/data/spot/monthly/klines/{SYMBOL}/1h/{filename}"
    request=urllib.request.Request(url,headers={"User-Agent":"ada-state-classifier/1.0"})
    with urllib.request.urlopen(request,timeout=90) as response: payload=response.read()
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names=[name for name in archive.namelist() if name.endswith('.csv')]
        if len(names)!=1: raise ValueError(url)
        rows=list(csv.reader(io.TextIOWrapper(archive.open(names[0]),encoding='utf-8')))
    bars=[]
    for row in rows:
        if row and row[0].isdigit():
            stamp=int(row[0]); stamp=stamp//1000 if stamp>10**14 else stamp
            bars.append({"timestamp":stamp,"open":float(row[1]),"high":float(row[2]),"low":float(row[3]),
                         "close":float(row[4]),"quote_volume":float(row[7])})
    start=timestamp(f"{y}-{m:02d}-01"); ny,nm=(y+1,1) if m==12 else (y,m+1)
    expected=set(range(start,timestamp(f"{ny}-{nm:02d}-01"),HOUR_MS)); stamps={bar['timestamp'] for bar in bars}; missing=sorted(expected-stamps)
    return bars,{"url":url,"sha256":hashlib.sha256(payload).hexdigest(),"bars":len(bars),"expected_bars":len(expected),
                 "missing_bars":len(missing),"first_missing_timestamp":missing[0] if missing else None}


def fit_model(bars):
    train_start=timestamp("2021-01-01"); train_end=timestamp("2023-01-01"); horizon=6
    features=[]; labels=[]
    for i in range(len(bars)-horizon):
        vector=feature_at(bars,i)
        if vector is None or not (train_start<=bars[i]['timestamp']<train_end): continue
        if bars[i+horizon]['timestamp']-bars[i]['timestamp']!=horizon*BAR_MS or bars[i+horizon]['timestamp']>=train_end: continue
        features.append(vector); labels.append(int(bars[i+horizon]['close']>bars[i]['close']))
    x=np.asarray(features); y=np.asarray(labels); scaler=StandardScaler().fit(x); xs=scaler.transform(x)
    model=LogisticRegression(C=0.1,class_weight='balanced',solver='lbfgs',max_iter=1000,random_state=0).fit(xs,y)
    scores={}
    for i,bar in enumerate(bars):
        vector=feature_at(bars,i)
        if vector is not None and bar['timestamp']>=train_end:
            scores[bar['timestamp']]=float(model.predict_proba(scaler.transform(vector.reshape(1,-1)))[0,1])
    fitted={"training_samples":len(y),"positive_share":float(np.mean(y)),"feature_names":["return_24h","return_72h","volatility_72h","range_24h","volume_shift","distance_5d_mean"],
            "scaler_mean":scaler.mean_.tolist(),"scaler_scale":scaler.scale_.tolist(),"coefficients":model.coef_[0].tolist(),"intercept":float(model.intercept_[0])}
    return scores,fitted


def metrics(result):
    trades=result['trades']; profit=sum(max(0,t['net_pnl']) for t in trades); loss=-sum(min(0,t['net_pnl']) for t in trades)
    return {"trades":len(trades),"longs":sum(t['side']==1 for t in trades),"shorts":sum(t['side']==-1 for t in trades),
            "win_rate":sum(t['net_pnl']>0 for t in trades)/len(trades) if trades else None,"net_return":result['net_return'],
            "net_pnl":result['ending_equity']-10000,"profit_factor":profit/loss if loss else None,"max_drawdown":result['max_drawdown'],
            "fees":sum(t['fees'] for t in trades),"borrow":sum(t['borrow'] for t in trades)}


def evaluate(bars,scores,blocks,config): return {name:metrics(backtest(bars,scores,timestamp(start),timestamp(end),config)) for name,start,end in blocks}


def main():
    with ThreadPoolExecutor(max_workers=8) as pool: parts=list(pool.map(fetch,MONTHS))
    hourly=[bar for part,_ in parts for bar in part]; manifest=[entry for _,entry in parts]; bars=resample_4h(hourly)
    scores,fitted=fit_model(bars); config=Config(); stress=with_cost_stress(config)
    dev=evaluate(bars,scores,DEV,config); dev_stress=evaluate(bars,scores,DEV,stress)
    val=evaluate(bars,scores,VAL,config); val_stress=evaluate(bars,scores,VAL,stress)
    val['ALL']=metrics(backtest(bars,scores,timestamp('2024-01-01'),timestamp('2026-10-01'),config))
    val_stress['ALL']=metrics(backtest(bars,scores,timestamp('2024-01-01'),timestamp('2026-10-01'),stress))
    positive=sum(max(0,val[name]['net_pnl']) for name,*_ in VAL); share=max((max(0,val[name]['net_pnl']) for name,*_ in VAL),default=0)/positive if positive else 1
    count=val['ALL']['trades']; direction=min(val['ALL']['longs'],val['ALL']['shorts'])/count if count else 0
    gate={"development_2023_positive":dev['2023']['net_return']>0,"validation_minimum_80_trades":count>=80,
          "both_directions_at_least_20pct":direction>=0.20,"normal_pf_at_least_1_20":(val['ALL']['profit_factor'] or 0)>=1.20,
          "stress_pf_at_least_1_05":(val_stress['ALL']['profit_factor'] or 0)>=1.05,
          "normal_positive_all_blocks":all(val[name]['net_return']>0 for name,*_ in VAL),
          "stress_positive_four_blocks":sum(val_stress[name]['net_return']>0 for name,*_ in VAL)>=4,
          "stress_total_positive":val_stress['ALL']['net_return']>0,"normal_max_drawdown_at_most_15pct":val['ALL']['max_drawdown']<=0.15,
          "profit_not_concentrated":share<=0.50,"forward_paper_50_trades":False}
    report={"strategy":"ADA_STATE_CLASSIFIER_V1","data":"Binance ADAUSDT spot 1h archives resampled to complete 4h bars",
            "training_period":"2021-01-01/2022-12-31","development_period":"2023-01-01/2023-12-31","validation_period":"2024-01-01/2026-09-30",
            "config":config.__dict__,"stress_config":stress.__dict__,"fitted_model":fitted,"development":dev,"development_stress":dev_stress,
            "validation":val,"validation_stress":val_stress,"largest_positive_validation_block_share":share,"smaller_direction_share":direction,
            "gate":gate,"passes_historical_gate":all(v for k,v in gate.items() if k!='forward_paper_50_trades'),"robust_candidate":all(gate.values()),
            "coverage":{"complete_4h_bars":len(bars)},"manifest":manifest,
            "limitations":["A fixed linear classifier cannot capture all regime changes.","Hourly OHLC cannot reveal intrabar stop/target order; stop is assumed first.",
                           "Short availability and liquidation are not modeled; explicit borrow is charged.","Historical passage would still require 50 new forward PAPER trades."]}
    Path('research/ada_state_classifier_results_20261024.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='manifest'},indent=2))


if __name__=='__main__': main()
