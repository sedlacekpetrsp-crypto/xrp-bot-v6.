"""Independent labor-resilience audit; no strategy import."""
import csv,datetime as dt,gzip,hashlib,io,json,pathlib,statistics,sys
DAY=86400000; UTC=dt.timezone.utc; root=pathlib.Path(sys.argv[1]); cache=pathlib.Path(sys.argv[2]); result=json.loads((root/'results.json').read_text())
with gzip.open(root/'trades.json.gz','rt') as h: ledgers=json.load(h)
checks=0; failures=[]
def check(v,m):
    global checks; checks+=1
    if not v: failures.append(m)
macro={}; prices={}; page=0
for source in result['manifest']:
    if source['kind']=='FRED_ICSA': path=cache/'fred-ICSA.csv'
    else: path=cache/f'XRPUSDT-1d-curve-api-{page}.json'; page+=1
    payload=path.read_bytes(); check(hashlib.sha256(payload).hexdigest()==source['sha256'],'hash:'+path.name)
    if source['kind']=='FRED_ICSA':
        for x in csv.DictReader(io.StringIO(payload.decode())):
            if x['ICSA'].strip() in ('','.'): continue
            macro[int(dt.datetime.strptime(x['observation_date'],'%Y-%m-%d').replace(tzinfo=UTC).timestamp()*1000)]=float(x['ICSA'])
    else:
        for x in json.loads(payload): prices[int(x[0])]={'open':float(x[1]),'high':float(x[2]),'low':float(x[3]),'close':float(x[4])}
ordered=sorted(macro); loc={t:i for i,t in enumerate(ordered)}
for key,trades in ledgers.items():
    previous=None; equity=10000.; fee=.0019 if key.endswith('_stress') else .00095; slip=.0004 if key.endswith('_stress') else .0002
    for n,t in enumerate(trades):
        label=f'{key}[{n}]'; li=loc[t['metric_timestamp']]; si=loc[t['signal_timestamp']]; hist=[macro[x] for x in ordered[li-52:li]]; recent=[macro[x] for x in ordered[li-3:li+1]]; prior=[macro[x] for x in ordered[li-7:li-3]]
        check(si-li==2,label+':lag'); check(t['latest_claims']<=statistics.median(hist)+1e-9,label+':median'); check(sum(recent)/4<sum(prior)/4,label+':trend'); check(t['entry_timestamp']-t['signal_timestamp']==DAY,label+':entry_lag'); check(abs(t['raw_entry']-prices[t['entry_timestamp']]['open'])<1e-12,label+':entry_open'); check(previous is None or t['entry_timestamp']>previous,label+':nonoverlap'); check(t['leg_notional']<=t['entry_equity']*.2+1e-7,label+':cap'); check(t['qty']*(t['entry']-t['stop'])<=t['entry_equity']*.005+1e-7,label+':risk')
        expected=fee*t['qty']*(t['entry']+t['exit']); fill=t['qty']*(t['exit']-t['entry']); check(abs(expected-t['fees'])<1e-7,label+':fees'); check(abs(fill-t['fees']-t['pnl'])<1e-7,label+':pnl'); check(abs(t['gross']-fill-t['slippage_cost'])<1e-7,label+':slippage'); check(abs(t['entry_equity']-equity)<1e-7 and abs(t['equity']-equity-t['pnl'])<1e-7,label+':equity'); check(t['intratrade_min_equity']<=t['entry_equity']+1e-7,label+':marked_drawdown'); check(abs(t['entry']-t['raw_entry']*(1+slip))<1e-9,label+':entry_slip'); check(abs(t['exit']-t['raw_exit']*(1-slip))<1e-9,label+':exit_slip')
        if t['reason']=='GAP_STOP': check(t['raw_exit']==prices[t['exit_timestamp']]['open'] and t['raw_exit']<=t['stop'],label+':gap_stop')
        previous=t['exit_timestamp']; equity=t['equity']
    check(len(trades)==result['runs'][key]['trades'],key+':count'); check(abs(sum(x['pnl'] for x in trades)-result['runs'][key]['net_pnl'])<1e-7,key+':net')
passed=not failures; result['gates']['audit']=passed; historical=all(v for k,v in result['gates'].items() if k!='forward_paper'); result['status']='TEST NEDOKONCEN: forward PAPER required' if historical else 'NEPROSEL'; (root/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n'); audit={'passed':passed,'checks':checks,'failures':failures}; (root/'audit.json').write_text(json.dumps(audit,indent=2)+'\n'); print(json.dumps(audit))
if not passed: raise SystemExit(1)
