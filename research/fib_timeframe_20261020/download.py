"""Download immutable monthly 5m bars with exchange checksum verification."""
import concurrent.futures,csv,hashlib,io,json,math,pathlib,sys,urllib.request,zipfile
HERE=pathlib.Path(__file__).resolve().parent
P=json.loads((HERE/'protocol.json').read_text())
def download(root,symbol,month):
 name=f'{symbol}-5m-{month}.zip'
 url=f'https://data.binance.vision/data/spot/monthly/klines/{symbol}/5m/{name}'
 path=root/name
 if not path.exists():path.write_bytes(urllib.request.urlopen(url,timeout=40).read())
 raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest()
 expected=urllib.request.urlopen(url+'.CHECKSUM',timeout=30).read().decode().split()[0]
 if digest!=expected:raise ValueError('Checksum mismatch '+name)
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  rows=[]
  for r in csv.reader(io.StringIO(z.read(z.namelist()[0]).decode())):
   stamp=int(r[0]);divisor=1000 if stamp>10**14 else 1
   row=[stamp//divisor,*map(float,r[1:6]),int(r[6])//divisor]
   o,h,l,c,v=row[1:6]
   if not all(math.isfinite(x) for x in row) or not 0<l<=min(o,c)<=max(o,c)<=h or v<0:raise ValueError('Bad OHLCV')
   rows.append(row)
 return symbol,rows,dict(url=url,sha256=digest,rows=len(rows))
def main(root):
 root.mkdir(parents=True,exist_ok=True);data={s:[] for s in P['symbols']};manifest=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
  tasks=[pool.submit(download,root,s,m) for s in P['symbols'] for m in P['months']]
  for t in tasks:
   s,rows,item=t.result();data[s].extend(rows);manifest.append(item);print(item['url'].split('/')[-1],len(rows),flush=True)
 datasets={}
 for s,rows in data.items():
  rows.sort(key=lambda r:r[0])
  if any(b[0]-a[0]!=300000 for a,b in zip(rows,rows[1:])):raise ValueError('Gap or duplicate '+s)
  if any(r[6]!=r[0]+299999 for r in rows):raise ValueError('Close-time mismatch')
  raw=json.dumps(rows,separators=(',',':')).encode();(root/(s+'.json')).write_bytes(raw)
  datasets[s]=dict(sha256=hashlib.sha256(raw).hexdigest(),rows=len(rows),first_open=rows[0][0],last_close=rows[-1][6])
 if len({tuple(r[0] for r in rows) for rows in data.values()})!=1:raise ValueError('Symbol timelines differ')
 (HERE/'datasets.json').write_text(json.dumps(datasets,indent=2))
 (HERE/'manifest.json').write_text(json.dumps(manifest,indent=2))
if __name__=='__main__':main(pathlib.Path(sys.argv[1]))
