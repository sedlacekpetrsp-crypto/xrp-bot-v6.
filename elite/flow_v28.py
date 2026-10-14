"""Read total and taker-buy XRP volume from the verified price archives."""
import csv,hashlib,io,zipfile
from pathlib import Path
from math import isfinite


def align_flow(rows,volumes):
    if len(rows)!=len(volumes):raise ValueError('volume length mismatch')
    for row,(ts,v,buy) in zip(rows,volumes):
        if ts!=row[0] or not isfinite(v) or v<0 or not isfinite(buy) or not 0<=buy<=v:
            raise ValueError('invalid volume or timestamp')


def load_flow(cache,rows,manifest):
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
                volumes.append((ts,float(r[5]),float(r[9])));count+=1
            if count!=m['bars']:raise ValueError('volume archive bar count')
    if prices!=rows:raise ValueError('price/volume source mismatch')
    align_flow(rows,volumes)
    return volumes
