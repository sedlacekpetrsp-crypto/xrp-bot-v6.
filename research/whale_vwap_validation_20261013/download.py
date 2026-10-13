import concurrent.futures,datetime,hashlib,json,math,pathlib,subprocess,sys
HERE=pathlib.Path(__file__).parent;p=json.loads((HERE/'protocol.json').read_text())
root=pathlib.Path(sys.argv[1]);root.mkdir(parents=True,exist_ok=True)
ms=lambda s:int(datetime.datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()*1000)
start,end=ms(p['data_start']),ms(p['data_end_exclusive']);step=60000
jobs=[(s,t,min(t+1000*step,end)) for s in p['symbols'] for t in range(start,end,1000*step)]
def fetch(job):
 symbol,a,b=job;path=root/f'{symbol}_{a}.json'
 if not path.exists():
  url=f'https://data-api.binance.vision/api/v3/klines?symbol={symbol}&interval=1m&startTime={a}&endTime={b-1}&limit=1000'
  r=subprocess.run(['curl','--retry','2','--max-time','30','-fsS',url],capture_output=True,text=True)
  if r.returncode:raise RuntimeError(r.stderr)
  rows=json.loads(r.stdout)
  if not isinstance(rows,list) or len(rows)!=(b-a)//step:raise ValueError('Incomplete batch')
  path.write_text(r.stdout)
 rows=json.loads(path.read_text())
 if rows[0][0]!=a or rows[-1][0]+step!=b:raise ValueError('Misaligned batch')
 return symbol,rows
merged={s:[] for s in p['symbols']}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
 for symbol,rows in pool.map(fetch,jobs):merged[symbol].extend(rows)
manifest=[]
for symbol,rows in merged.items():
 for i,r in enumerate(rows):
  if r[0]!=start+i*step or r[6]!=r[0]+step-1:raise ValueError('Gap or duplicate')
  o,h,l,c=map(float,r[1:5]);v=float(r[5])
  if not all(math.isfinite(x) for x in (o,h,l,c,v)) or not 0<l<=min(o,c)<=max(o,c)<=h or v<0:raise ValueError('Invalid OHLCV')
 raw=json.dumps(rows,separators=(',',':')).encode();(root/f'{symbol}_1m.json').write_bytes(raw)
 manifest.append(dict(symbol=symbol,bars=len(rows),sha256=hashlib.sha256(raw).hexdigest(),start=p['data_start'],end=p['data_end_exclusive']))
(HERE/'data_manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest),flush=True)
