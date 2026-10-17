"""Download and validate Binance Vision monthly XRPUSDT 5m spot candles.

Usage: python -m elite.data_loader --start 2025-10 --end 2026-09 --out elite_xrp.csv
No API keys or trading permissions required.
"""
import argparse
import csv
import hashlib
import io
import urllib.request
import zipfile
from datetime import datetime

BASE="https://data.binance.vision/data/spot/monthly/klines/XRPUSDT/5m"

def months(start,end):
    y,m=map(int,start.split("-"))
    ey,em=map(int,end.split("-"))
    while (y,m)<=(ey,em):
        yield f"{y:04d}-{m:02d}"
        m+=1
        if m>12: y,m=y+1,1

def fetch_month(month):
    filename=f"XRPUSDT-5m-{month}.zip"
    url=f"{BASE}/{filename}"
    with urllib.request.urlopen(url,timeout=40) as resp:
        raw=resp.read()
    with urllib.request.urlopen(url+".CHECKSUM",timeout=20) as resp:
        expected=resp.read().decode().split()[0].lower()
    if hashlib.sha256(raw).hexdigest()!=expected:
        raise ValueError("checksum mismatch: "+filename)
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        members=[n for n in z.namelist() if n.endswith(".csv")]
        if len(members)!=1: raise ValueError("unexpected ZIP layout")
        rows=[]
        for row in csv.reader(io.TextIOWrapper(z.open(members[0]),encoding="utf-8")):
            if not row or row[0].lower()=="open_time": continue
            timestamp=int(row[0])
            if timestamp>10**15: timestamp//=1000  # spot microseconds since 2025
            o,h,l,c=map(float,row[1:5])
            if not (0<l<=min(o,c)<=max(o,c)<=h):
                raise ValueError("invalid OHLC "+str(timestamp))
            rows.append((timestamp,o,h,l,c))
        return rows

def load(start,end):
    result=[]
    for month in months(start,end):
        result.extend(fetch_month(month))
    result.sort(key=lambda r:r[0])
    for prev,cur in zip(result,result[1:]):
        if cur[0]-prev[0]!=300000:
            raise ValueError(f"missing or duplicate 5m candles: {prev[0]} -> {cur[0]}")
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--start",required=True)
    p.add_argument("--end",required=True)
    p.add_argument("--out",required=True)
    args=p.parse_args()
    rows=load(args.start,args.end)
    with open(args.out,"w",newline="") as f:
        writer=csv.writer(f)
        writer.writerow(["timestamp_ms","open","high","low","close"])
        writer.writerows(rows)
    print(f"validated {len(rows)} candles: {rows[0][0]} to {rows[-1][0]}")

if __name__=="__main__": main()
