"""Independent source/ledger audit without importing strategy code."""
import csv,gzip,hashlib,io,json,pathlib,sys,zipfile
DAY=86_400_000;TOL=1e-7
def close(a,b):return abs(a-b)<=TOL*max(1,abs(a),abs(b))
def main():
    cache=pathlib.Path(sys.argv[1]);dest=pathlib.Path(sys.argv[2]);r=json.loads((dest/'results.json').read_text())
    with gzip.open(dest/'trades.json.gz','rt') as h:ledgers=json.load(h)
    checks=[]
    def check(name,ok,detail=''):checks.append(dict(name=name,pass_=bool(ok),detail=detail))
    prs={};prices={}
    for item in r['manifest']:
        if item['kind'].startswith('github'):
            path=cache/f"rippled-merged-{item['partition']}-p{item['page']}.json";doc=json.loads(path.read_bytes())
            check('hash:'+path.name,hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256'])
            check('rows:'+path.name,len(doc['items'])==item['rows'] and doc['total_count']==item['reported_total'])
            for x in doc['items']:
                k=x['number'];v=x['pull_request']['merged_at']
                check(f'merged:{k}',bool(v))
                if k in prs:check(f'duplicate:{k}',prs[k]==v)
                prs[k]=v
        else:
            path=cache/item['url'].rsplit('/',1)[-1];payload=path.read_bytes();check('hash:'+path.name,hashlib.sha256(payload).hexdigest()==item['sha256'])
            with zipfile.ZipFile(io.BytesIO(payload)) as z:raw=csv.reader(io.TextIOWrapper(z.open(z.namelist()[0])))
            count=0
            for x in raw:
                if x[0].lower().startswith('open'):continue
                ts=int(x[0]);ts=ts//1000 if ts>10**14 else ts;prices[ts]=dict(open=float(x[1]),high=float(x[2]),low=float(x[3]),close=float(x[4]));count+=1
            check('rows:'+path.name,count==item['rows'])
    check('unique_pr_count',len(prs)==r['data_quality']['merged_prs'])
    event_times=sorted(int(__import__('datetime').datetime.fromisoformat(v.replace('Z','+00:00')).timestamp()*1000) for v in prs.values())
    for key,trades in ledgers.items():
        prior_exit=-1;equity=10000.;multiple=2 if key.endswith('stress') else 1;fee=.00095*multiple;slip=.00020*multiple
        for n,t in enumerate(trades):
            p=f'{key}:{n}';check(p+':causal',t['signal_timestamp']<t['entry_timestamp'] and t['entry_timestamp']==t['signal_day']+DAY)
            n7=sum(t['signal_day']-6*DAY<=x<t['signal_day']+DAY for x in event_times);n30=sum(t['signal_day']-29*DAY<=x<t['signal_day']+DAY for x in event_times)
            check(p+':counts',t['merge_count_7']==n7 and t['merge_count_30']==n30 and n7>=5 and n30>=15)
            check(p+':nonoverlap',t['entry_timestamp']>prior_exit);check(p+':entry_open',close(t['raw_entry'],prices[t['entry_timestamp']]['open']))
            check(p+':entry_slip',close(t['entry'],t['raw_entry']*(1+slip)));check(p+':exit_slip',close(t['exit'],t['raw_exit']*(1-slip)))
            expected_fee=t['qty']*(t['entry']+t['exit'])*fee;expected_pnl=t['qty']*(t['exit']-t['entry'])-expected_fee
            check(p+':fees',close(t['fees'],expected_fee));check(p+':pnl',close(t['pnl'],expected_pnl));check(p+':equity_in',close(t['entry_equity'],equity));check(p+':equity_out',close(t['equity'],equity+t['pnl']))
            check(p+':risk',t['qty']*(t['entry']-t['stop'])<=t['entry_equity']*.005+TOL);check(p+':cap',t['leg_notional']<=t['entry_equity']*.20+TOL)
            if t['reason']=='GAP_STOP':check(p+':gap_stop',close(t['raw_exit'],prices[t['exit_timestamp']]['open']) and t['raw_exit']<=t['stop'])
            prior_exit=t['exit_timestamp'];equity=t['equity']
        check(key+':count',len(trades)==r['runs'][key]['trades']);check(key+':net',close(sum(x['pnl'] for x in trades),r['runs'][key]['net_pnl']))
    passed=all(x['pass_'] for x in checks);audit=dict(passed=passed,checks=len(checks),failed=[x for x in checks if not x['pass_']],method='Independent API-page completeness, hashes, merge counts, chronology, raw fills, costs, sizing, non-overlap and equity reconciliation; no strategy import.')
    (dest/'audit.json').write_text(json.dumps(audit,indent=2).replace('"pass_"','"pass"')+'\n');r['gates']['audit']=passed;r['status']='NEPROSEL' if not all(r['gates'].values()) else 'PROSEL';(dest/'results.json').write_text(json.dumps(r,indent=2,allow_nan=False)+'\n')
    print(json.dumps(audit,indent=2));
    if not passed:raise SystemExit(1)
if __name__=='__main__':main()
