"""Checksummed monthly cache, strict month coverage, no trading access."""
import hashlib, io, zipfile, csv, json, urllib.request
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from elite.data_loader import months, BASE
from elite.research_engine import validate


def download(cache, month, symbol='XRPUSDT'):
    if symbol not in ('XRPUSDT','BTCUSDT'):raise ValueError('unsupported symbol')
    base=BASE.replace('/XRPUSDT/','/'+symbol+'/')
    p=Path(cache)/f'{symbol}-5m-{month}.zip'
    p.parent.mkdir(parents=True,exist_ok=True)
    check=p.with_suffix('.sha256')
    if not p.exists() or not check.exists():
        url=base+'/'+p.name
        with urllib.request.urlopen(url,timeout=60) as r: raw=r.read()
        with urllib.request.urlopen(url+'.CHECKSUM',timeout=60) as r: expected=r.read().decode().split()[0].lower()
        if hashlib.sha256(raw).hexdigest()!=expected: raise ValueError('checksum mismatch')
        p.write_bytes(raw); check.write_text(expected)
    raw=p.read_bytes(); expected=check.read_text().strip()
    if hashlib.sha256(raw).hexdigest()!=expected: raise ValueError('cache checksum mismatch')
    rows=[]
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names=[n for n in z.namelist() if n.endswith('.csv')]
        if len(names)!=1: raise ValueError('ZIP layout')
        for r in csv.reader(io.TextIOWrapper(z.open(names[0]))):
            if r[0]=='open_time': continue
            ts=int(r[0]); ts=ts//1000 if ts>10**15 else ts
            rows.append((ts,*map(float,r[1:5])))
    validate(rows)
    y,m=map(int,month.split('-'))
    first=int(datetime(y,m,1,tzinfo=timezone.utc).timestamp()*1000)
    following=int(datetime(y+1 if m==12 else y,1 if m==12 else m+1,1,tzinfo=timezone.utc).timestamp()*1000)
    if rows[0][0]!=first or rows[-1][0]!=following-300000 or len(rows)!=(following-first)//300000:
        raise ValueError('incomplete month '+month)
    return rows,dict(month=month,sha256=expected,bars=len(rows),url=base+'/'+p.name)


def load_cached(cache,start='2023-04',end='2026-09',symbol='XRPUSDT'):
    with ThreadPoolExecutor(max_workers=6) as pool:
        parts=list(pool.map(lambda month:download(cache,month,symbol),months(start,end)))
    rows=[r for part,_ in parts for r in part]
    validate(rows)
    return rows,[manifest for _,manifest in parts]

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(); p.add_argument('--cache',required=True)
    args=p.parse_args()
    rows,manifest=load_cached(args.cache)
    print(json.dumps(dict(bars=len(rows),months=len(manifest))))
