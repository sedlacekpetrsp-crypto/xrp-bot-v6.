import concurrent.futures,datetime,hashlib,json,math,pathlib,subprocess,sys
HERE=pathlib.Path(__file__).parent
p=json.loads((HERE/'protocol.json').read_text());root=pathlib.Path(sys.argv[1]);root.mkdir(parents=True,exist_ok=True)
ms=lambda s:int(datetime.datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()*1000)
start,end=ms(p['data_start']),ms(p['data_end']);step=900000

def fetch(a):
 b=min(a+1000*step,end);path=root/f'{a}.json'
 if not path.exists():
  url=f"https://data-api.binance.vision/api/v3/klines?symbol={p['symbol']}&interval=15m&startTime={a}&endTime={b-1}&limit=1000"
  r=subprocess.run(['curl','-fsS','--max-time','30','--retry','2',url],capture_output=True,text=True)
  if r.returncode:raise RuntimeError(r.stderr)
  path.write_text(r.stdout)
 rows=json.loads(path.read_text())
 if len(rows)!=(b-a)//step:raise ValueError('Missing candles')
 return rows
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:rows=[r for batch in ex.map(fetch,range(start,end,step*1000)) for r in batch]
for i,r in enumerate(rows):
 if r[0]!=start+i*step or r[6]!=r[0]+step-1:raise ValueError('Gap or duplicate')
 o,h,l,c,v=map(float,r[1:6])
 if not all(math.isfinite(x) for x in (o,h,l,c,v)) or not 0<l<=min(o,c)<=max(o,c)<=h or v<0:raise ValueError('Invalid OHLCV')
raw=json.dumps(rows,separators=(',',':')).encode();(root/'candles.json').write_bytes(raw)
manifest=dict(symbol=p['symbol'],interval='15m',bars=len(rows),start=p['data_start'],end_exclusive=p['data_end'],sha256=hashlib.sha256(raw).hexdigest())
(HERE/'data_manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest))
