import concurrent.futures,datetime,hashlib,json,pathlib,subprocess,sys
root=pathlib.Path(sys.argv[1]);root.mkdir(parents=True,exist_ok=True)
p=json.loads((pathlib.Path(__file__).parent/'protocol.json').read_text())
start=int(datetime.datetime.fromisoformat(p['data_start'].replace('Z','+00:00')).timestamp()*1000)
end=int(datetime.datetime.fromisoformat(p['data_end_exclusive'].replace('Z','+00:00')).timestamp()*1000)
step=60000
jobs=[(t,min(t+1000*step,end)) for t in range(start,end,1000*step)]
def fetch(job):
    a,b=job;path=root/f'{a}.json'
    if not path.exists():
        url=f'https://data-api.binance.vision/api/v3/klines?symbol=XRPUSDC&interval=1m&startTime={a}&endTime={b-1}&limit=1000'
        r=subprocess.run(['curl','--retry','2','--max-time','30','-fsS',url],capture_output=True,text=True)
        if r.returncode:raise RuntimeError(r.stderr)
        rows=json.loads(r.stdout)
        if not isinstance(rows,list) or len(rows)!=(b-a)//step:raise ValueError('Missing batch')
        path.write_text(r.stdout)
    rows=json.loads(path.read_text())
    if rows[0][0]!=a or rows[-1][0]+step!=b:raise ValueError('Misaligned batch')
    return rows
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    data=[r for batch in pool.map(fetch,jobs) for r in batch]
for i,r in enumerate(data):
    if r[0]!=start+i*step or r[6]!=r[0]+step-1:raise ValueError('Gap or duplicate')
    o,h,l,c=map(float,r[1:5]);v=float(r[5])
    if not (0<l<=min(o,c)<=max(o,c)<=h) or v<0:raise ValueError('Invalid OHLCV')
raw=json.dumps(data,separators=(',',':')).encode();(root/'XRPUSDC_1m.json').write_bytes(raw)
manifest=dict(bars=len(data),start=p['data_start'],end=p['data_end_exclusive'],sha256=hashlib.sha256(raw).hexdigest())
(pathlib.Path(__file__).parent/'data_manifest.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps(manifest),flush=True)
