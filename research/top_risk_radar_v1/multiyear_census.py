"""Multi-year descriptive XRP census; NOT a predictor, trade-level backtest, or OOS test."""
from __future__ import annotations
import json
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
from research.top_risk_radar_v1.exploratory_kline_census import load_month
from research.top_risk_radar_v1.episodes import group_positive_episodes

MONTHS=[f"{year}-{month:02d}" for year in range(2022,2026) for month in range(1,13)]

def evaluate(rows):
    by_time=dict(rows)
    if len(by_time)!=len(rows): raise ValueError("duplicate timestamps")
    times=sorted(by_time)
    gaps=[{"previous":a.isoformat(),"next":b.isoformat(),
           "missing_hours":int((b-a)/timedelta(hours=1))-1}
          for a,b in zip(times,times[1:]) if b-a!=timedelta(hours=1)]
    # Never fill absent candles. Exclude any decision whose 30-day forward
    # window crosses an absent timestamp; same exclusion for both outcomes.
    missing=set()
    for a,b in zip(times,times[1:]):
        while b-a>timedelta(hours=1):
            a+=timedelta(hours=1)
            missing.add(a)
    if len(missing)>1000:
        raise ValueError("too many missing hours; refuse census")
    result=defaultdict(lambda:{"matured":0,"growth":0,"risk":0,"both":0})
    growth_dates=[]; risk_dates=[]
    excluded_by_year=defaultdict(int)
    for t in times:
        if t.hour!=1 or t+timedelta(days=30)>times[-1]: continue
        if any(t+timedelta(hours=h) in missing for h in range(1,721)):
            excluded_by_year[str(t.year)]+=1
            continue
        p=by_time[t]
        up=any(by_time[t+timedelta(hours=h)]>=p*Decimal('1.30') for h in range(1,721))
        down=any(by_time[t+timedelta(hours=h)]<=p*Decimal('0.80') for h in range(1,337))
        x=result[str(t.year)]
        x["matured"]+=1; x["growth"]+=int(up); x["risk"]+=int(down); x["both"]+=int(up and down)
        if up: growth_dates.append(t)
        if down: risk_dates.append(t)
    def episodes(dates,horizon):
        return [{"first":e["first_decision"].isoformat(),
                 "last":e["last_decision"].isoformat(),
                 "positive_decisions":e["positive_decisions"]}
                for e in group_positive_episodes(dates,[True]*len(dates),
                          max_separation=timedelta(days=horizon))]
    return {"per_decision_year":dict(result),
            "excluded_decisions_missing_data_by_year":dict(excluded_by_year),
            "missing_hour_ranges":gaps,
            "growth_episodes_30d":episodes(growth_dates,30),
            "risk_episodes_14d":episodes(risk_dates,14)}

if __name__=="__main__":
    rows=[]; manifests=[]
    for month in MONTHS:
        part,meta=load_month(month)
        rows.extend(part); manifests.append(meta)
    report={"status":"DESCRIPTIVE_ONLY_NOT_PREDICTION_NOT_OOS",
      "market":"Binance XRPUSDT 1h spot CLOSE",
      "reference":"01:00 UTC close, not protocol 00:05 first trade",
      "years":"2022-2025","sources":manifests,"analysis":evaluate(rows)}
    with open("xrp_multiyear_census.json","w") as f: json.dump(report,f,indent=2)
    print(json.dumps({"status":report["status"],"per_decision_year":report["analysis"]["per_decision_year"],
       "growth_episode_count":len(report["analysis"]["growth_episodes_30d"]),
       "risk_episode_count":len(report["analysis"]["risk_episodes_14d"]),
       "archive_count":len(manifests)},indent=2))
