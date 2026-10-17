"""Read XRP base volume and USDT quote turnover from the verified price archives."""
import csv,hashlib,io,zipfile
from pathlib import Path
from math import isfinite


def align_turnover(rows,volumes):
    if len(rows)!=len(volumes):raise ValueError('volume length mismatch')
    for row,(ts,v,quote) in zip(rows,volumes):
        if ts!=row[0] or not isfinite(v) or v<0 or not isfinite(quote) or quote<0:
            raise ValueError('invalid turnover or timestamp')
        tolerance=max(1e-6,quote*1e-8)
        if quote<row[3]*v-tolerance or quote>row[2]*v+tolerance:
            raise ValueError('turnover outside OHLC bounds')


def load_turnover(cache,rows,manifest):
    volumes=[];prices=[]
    for m in manifest:
        p=Path(cache)/f"XRPUSDT-5m-{m['month']}.zip"
        raw=p.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=m['sha256']:
            raise ValueError('volume archive checksum mismatch: '+p.name)
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            names=[n for n in z.namelist() if n.endswith('.csv')]
            if len(names)!=1:raise ValueError('volume ZIP layout')
            count=0
            for r in csv.reader(io.TextIOWrapper(z.open(names[0]))):
                if r[0]=='open_time':continue
                ts=int(r[0]);ts=ts//1000 if ts>10**15 else ts
                prices.append((ts,*map(float,r[1:5])))
                volumes.append((ts,float(r[5]),float(r[7])));count+=1
            if count!=m['bars']:raise ValueError('volume archive bar count')
    if prices!=rows:raise ValueError('price/volume source mismatch')
    align_turnover(rows,volumes)
    return volumes
