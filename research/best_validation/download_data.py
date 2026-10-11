"""Download exactly the frozen input; reject changed content rather than silently reuse."""
import argparse,hashlib,json,time
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import urlencode
from datetime import datetime
STEP=300000
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((Path(__file__).parent/'results/data_manifest.json').read_text())
    for m in manifest:
        start=int(datetime.fromisoformat(m['start']).timestamp()*1000);end=int(datetime.fromisoformat(m['end']).timestamp()*1000);rows=[]
        while start<end:
            url='https://data-api.binance.vision/api/v3/klines?'+urlencode(dict(symbol=m['symbol'],interval='5m',startTime=start,endTime=end-1,limit=1000))
            batch=json.load(urlopen(url,timeout=30))
            if not isinstance(batch,list) or not batch:raise ValueError('missing data')
            rows.extend(batch);start=int(batch[-1][0])+STEP;time.sleep(.2)
        raw=json.dumps(rows,separators=(',',':')).encode()
        if len(rows)!=m['bars'] or hashlib.sha256(raw).hexdigest()!=m['sha256']:raise ValueError('Dataset differs from frozen hash: '+m['symbol'])
        (a.output/(m['symbol']+'_5m.json')).write_bytes(raw)
        print(m['symbol'],'verified')
