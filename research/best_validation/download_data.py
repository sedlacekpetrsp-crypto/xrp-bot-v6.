"""Download frozen inputs concurrently; only write files with matching hashes."""
import argparse,hashlib,json,time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import urlencode
from datetime import datetime
STEP=300000

def fetch(job):
    symbol,start,end=job
    url='https://data-api.binance.vision/api/v3/klines?'+urlencode(dict(symbol=symbol,interval='5m',startTime=start,endTime=end-1,limit=1000))
    for attempt in range(3):
        try:
            with urlopen(url,timeout=30) as response:rows=json.load(response)
            if not isinstance(rows,list) or not rows:raise ValueError('missing data')
            if int(rows[0][0])!=start or int(rows[-1][0])+STEP!=end:raise ValueError('incomplete batch')
            return rows
        except Exception:
            if attempt==2:raise
            time.sleep(attempt+1)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((Path(__file__).parent/'results/data_manifest.json').read_text())
    with ThreadPoolExecutor(max_workers=8) as pool:
        for m in manifest:
            path=a.output/(m['symbol']+'_5m.json')
            if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()==m['sha256']:
                print(m['symbol'],'verified cached',flush=True);continue
            start=int(datetime.fromisoformat(m['start']).timestamp()*1000);end=int(datetime.fromisoformat(m['end']).timestamp()*1000)
            jobs=[(m['symbol'],t,min(t+1000*STEP,end)) for t in range(start,end,1000*STEP)]
            rows=[r for batch in pool.map(fetch,jobs) for r in batch]
            raw=json.dumps(rows,separators=(',',':')).encode()
            if len(rows)!=m['bars'] or hashlib.sha256(raw).hexdigest()!=m['sha256']:raise ValueError('Dataset differs from frozen hash: '+m['symbol'])
            path.write_bytes(raw)
            print(m['symbol'],'verified',flush=True)
