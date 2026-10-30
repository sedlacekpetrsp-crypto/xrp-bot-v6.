import csv,datetime as dt,gzip,hashlib,io,json,math,pathlib,statistics,sys,zipfile
DAY=86400000;TOL=1e-7
def close(a,b):return abs(a-b)<=TOL*max(1,abs(a),abs(b))
def main():
    cache=pathlib.Path(sys.argv[1]);dest=pathlib.Path(sys.argv[2]);r=json.loads((dest/'results.json').read_text());led=json.load(gzip.open(dest/'trades.json.gz','rt'));checks=[];dv={};btc={};xrp={}
    def ck(n,x):checks.append(dict(name=n,pass_=bool(x)))
    for z in r['manifest']:
        p=cache/(f"deribit-btc-dvol-p{z['page']}.json" if z['kind'].startswith('deribit') else z['url'].rsplit('/',1)[-1]);raw=p.read_bytes();ck('hash:'+p.name,hashlib.sha256(raw).hexdigest()==z['sha256'])
        if z['kind'].startswith('deribit'):
            for x in json.loads(raw)['result']['data']:dv[int(x[0])]=float(x[4])
        else:
            target=btc if 'BTCUSDT' in z['kind'] else xrp
            with zipfile.ZipFile(io.BytesIO(raw)) as a:rows=csv.reader(io.TextIOWrapper(a.open(a.namelist()[0])))
            for x in rows:
                if x[0].lower().startswith('open'):continue
                t=int(x[0]);t=t//1000 if t>10**14 else t;target[t]=dict(open=float(x[1]),close=float(x[4]))
    for key,trades in led.items():
        eq=10000.;prior=-1;mul=2 if key.endswith('stress') else 1;fee=.00095*mul;slip=.0002*mul
        for i,t in enumerate(trades):
            p=f'{key}:{i}';mt=t['metric_timestamp'];days=[mt-j*DAY for j in range(20,-1,-1)];rets=[math.log(btc[days[j]]['close']/btc[days[j-1]]['close']) for j in range(1,21)];rv=statistics.pstdev(rets)*math.sqrt(365)*100;prem=dv[mt]-rv;ck(p+':feature',close(t['dvol_close'],dv[mt]) and close(t['rv20'],rv) and close(t['premium'],prem) and prem>=15);ck(p+':lag',t['entry_timestamp']==mt+2*DAY);ck(p+':overlap',t['entry_timestamp']>prior);ck(p+':open',close(t['raw_entry'],xrp[t['entry_timestamp']]['open']));ck(p+':entry',close(t['entry'],t['raw_entry']*(1+slip)));ck(p+':exit',close(t['exit'],t['raw_exit']*(1-slip)));f=t['qty']*(t['entry']+t['exit'])*fee;pn=t['qty']*(t['exit']-t['entry'])-f;ck(p+':fees',close(t['fees'],f));ck(p+':pnl',close(t['pnl'],pn));ck(p+':equity',close(t['entry_equity'],eq) and close(t['equity'],eq+t['pnl']));ck(p+':risk',t['qty']*(t['entry']-t['stop'])<=t['entry_equity']*.005+TOL);ck(p+':cap',t['leg_notional']<=t['entry_equity']*.2+TOL);prior=t['exit_timestamp'];eq=t['equity']
        ck(key+':count',len(trades)==r['runs'][key]['trades']);ck(key+':net',close(sum(x['pnl'] for x in trades),r['runs'][key]['net_pnl']))
    passed=all(x['pass_'] for x in checks);a=dict(passed=passed,checks=len(checks),failed=[x for x in checks if not x['pass_']],method='Independent source hashes, DVOL/BTC population-volatility features, lag, chronology, prices, fills, costs, sizing, non-overlap, equity and reports; no strategy import.');(dest/'audit.json').write_text(json.dumps(a,indent=2).replace('"pass_"','"pass"')+'\n');r['gates']['audit']=passed;r['status']='NEPROSEL' if not all(r['gates'].values()) else 'PROSEL';(dest/'results.json').write_text(json.dumps(r,indent=2,allow_nan=False)+'\n');print(json.dumps(a,indent=2))
    if not passed:raise SystemExit(1)
if __name__=='__main__':main()
