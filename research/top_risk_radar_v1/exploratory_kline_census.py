"""Exploratory XRP 1h close-price event census; NOT trade-level radar backtest.

Fetches 2024 Jan-Apr Binance spot 1h kline monthly archives with SHA256.
No feature tuning, prediction, model training, order execution or secrets.
"""
from __future__ import annotations
import csv, hashlib, io, json, re, urllib.request, zipfile
from datetime import datetime, timezone, timedelta
from decimal import Decimal

BASE="https://data.binance.vision/data/spot/monthly/klines/XRPUSDT/1h/"
MONTHS=("2024-01","2024-02","2024-03","2024-04")
LIMIT=25_000_000

def get(url):
    with urllib.request.urlopen(url,timeout=90) as r:
        data=r.read(LIMIT+1)
    if len(data)>LIMIT: raise ValueError("oversize")
    return data

def load_month(month):
    name=f"XRPUSDT-1h-{month}.zip"
    blob=get(BASE+name)
    chk=get(BASE+name+".CHECKSUM").decode()
    m=re.search(r"\b([a-fA-F0-9]{64})\b",chk)
    if not m or hashlib.sha256(blob).hexdigest()!=m.group(1).lower():
        raise ValueError(f"checksum mismatch: {month}")
    out=[]
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        files=[f for f in z.infolist() if not f.is_dir()]
        if len(files)!=1 or not files[0].filename.endswith(".csv"):
            raise ValueError("unexpected ZIP")
        with z.open(files[0]) as f:
            for row in csv.reader(io.TextIOWrapper(f,encoding="utf-8-sig")):
                if row and row[0].lower().startswith("open"): continue
                if len(row)!=12: raise ValueError("bad candle")
                stamp=int(row[0])
                if stamp < 10**12 or stamp >= 10**14: raise ValueError("unexpected timestamp")
                dt=datetime.fromtimestamp(stamp/1000,tz=timezone.utc)
                close=Decimal(row[4])
                if close<=0: raise ValueError("invalid price")
                out.append((dt,close))
    return out,{"month":month,"sha256":hashlib.sha256(blob).hexdigest(),"candles":len(out)}

def census(rows):
    by_time=dict(rows)
    if len(by_time)!=len(rows): raise ValueError("duplicate hourly timestamps")
    times=sorted(by_time)
    if any(b-a!=timedelta(hours=1) for a,b in zip(times,times[1:])):
        raise ValueError("missing hourly candle")
    outcomes={"matured_decisions":0,"growth_30pct_30d":0,"downside_20pct_14d":0,"both":0}
    for t in times:
        if t.hour!=1: continue  # 00:05 decision approximated by 01:00 close; NOT equivalent
        if t+timedelta(days=30)>times[-1]: continue
        price=by_time[t]
        up=any(by_time[t+timedelta(hours=h)]>=price*Decimal("1.30") for h in range(1,721))
        down=any(by_time[t+timedelta(hours=h)]<=price*Decimal("0.80") for h in range(1,337))
        outcomes["matured_decisions"]+=1
        outcomes["growth_30pct_30d"]+=int(up)
        outcomes["downside_20pct_14d"]+=int(down)
        outcomes["both"]+=int(up and down)
    return outcomes

if __name__=="__main__":
    rows=[]; manifests=[]
    for month in MONTHS:
        r,m=load_month(month)
        rows+=r; manifests.append(m)
    print(json.dumps({"status":"EXPLORATORY_ONLY_NOT_RADAR_BACKTEST",
       "market":"Binance XRPUSDT spot 1h CLOSE",
       "warning":"01:00 UTC candle close is not 00:05 UTC first-trade reference; closes miss intrahour spikes. No forecast model tested.",
       "sources":manifests,"outcomes":census(rows)},indent=2))
