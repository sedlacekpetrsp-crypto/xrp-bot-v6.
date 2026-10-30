import datetime as dt,gzip,hashlib,json,pathlib,statistics,sys
DAY=86_400_000;UTC=dt.timezone.utc
def close(a,b,tol=1e-8):return abs(a-b)<=tol*max(1,abs(a),abs(b))
def main():
    cache=pathlib.Path(sys.argv[1]);dest=pathlib.Path(sys.argv[2]);res=json.loads((dest/'results.json').read_text());checks=[]
    def check(n,v):checks.append(dict(name=n,passed=bool(v)))
    for m in res['manifest']:
        raw=(cache/m['cache_file']).read_bytes();check('hash_'+m['cache_file'],hashlib.sha256(raw).hexdigest()==m['sha256'] and len(raw)==m['bytes'])
    md=json.loads((cache/res['manifest'][0]['cache_file']).read_bytes())['data'];metric=[dict(timestamp=int(dt.datetime.fromisoformat(x['time'].replace('Z','+00:00')).timestamp()*1000),hashrate=float(x['HashRate'])) for x in md];check('metric_rows',len(metric)==res['data_quality']['metric_rows']);check('metric_gaps',all(b['timestamp']-a['timestamp']==DAY for a,b in zip(metric,metric[1:])))
    signals={}
    for i in range(31,len(metric)):
        w=[x['hashrate'] for x in metric[i-31:i-1]];mean=statistics.mean(w);sd=statistics.pstdev(w);shock=metric[i-1]['hashrate'];cur=metric[i]['hashrate']
        if sd and (shock-mean)/sd<=-1 and cur>shock:signals[metric[i]['timestamp']+2*DAY]=dict(metric_timestamp=metric[i]['timestamp'],prior_timestamp=metric[i-1]['timestamp'],hashrate=cur,shock_hashrate=shock,mean30=mean,sd30=sd,zscore=(shock-mean)/sd)
    check('signals_total',len(signals)==res['signals_total'])
    price=[]
    for m in res['manifest'][1:]:
        doc=json.loads((cache/m['cache_file']).read_bytes());check('rows_'+m['cache_file'],len(doc)==m['rows']);price += [dict(timestamp=int(x[0]),open=float(x[1]),high=float(x[2]),low=float(x[3]),close=float(x[4])) for x in doc]
    check('price_rows',len(price)==res['data_quality']['price_rows']);check('price_gaps',all(b['timestamp']-a['timestamp']==DAY for a,b in zip(price,price[1:])));index={x['timestamp']:i for i,x in enumerate(price)}
    with gzip.open(dest/'trades.json.gz','rt') as h:ledgers=json.load(h)
    n=0
    for key,trades in ledgers.items():
        fee=.0019 if key.endswith('_stress') else .00095;slip=.0004 if key.endswith('_stress') else .0002
        for a,b in zip(trades,trades[1:]):check('nonoverlap_'+key+'_'+str(n),a['exit_timestamp']<b['entry_timestamp'])
        for t in trades:
            n+=1;s=signals[t['entry_timestamp']];check('signal_'+str(n),all(close(t[k],s[k]) if isinstance(s[k],float) else t[k]==s[k] for k in s));i=index[t['entry_timestamp']];row=price[i];check('lag_'+str(n),t['metric_timestamp']+2*DAY==t['entry_timestamp']);check('entry_'+str(n),close(t['raw_entry'],row['open']) and close(t['entry'],row['open']*(1+slip)));av=sum(max(price[j]['high']-price[j]['low'],abs(price[j]['high']-price[j-1]['close']),abs(price[j]['low']-price[j-1]['close'])) for j in range(i-14,i))/14;check('atr_'+str(n),close(t['atr'],av));check('brackets_'+str(n),close(t['stop'],t['entry']-2*av) and close(t['target'],t['entry']+3*(t['entry']-t['stop'])));check('limits_'+str(n),t['leg_notional']<=t['entry_equity']*.2+1e-7 and t['qty']*(t['entry']-t['stop'])<=t['entry_equity']*.005+1e-7)
            j=index[t['exit_timestamp']];erow=price[j];reason=t['reason'];expected=erow['open'] if reason=='GAP_STOP' else t['stop'] if reason=='STOP' else t['target'] if reason=='TARGET' else erow['close'];check('exit_'+str(n),close(t['raw_exit'],expected) and close(t['exit'],expected*(1-slip)));fees=t['qty']*t['entry']*fee+t['qty']*t['exit']*fee;check('cost_'+str(n),close(t['fees'],fees) and close(t['pnl'],t['qty']*(t['exit']-t['entry'])-fees))
        m=res['runs'][key];win=sum(max(0,x['pnl']) for x in trades);loss=-sum(min(0,x['pnl']) for x in trades);net=sum(x['pnl'] for x in trades);check('report_'+key,m['trades']==len(trades) and close(m['net_pnl'],net) and close(m['gross_profit'],win) and close(m['gross_loss'],loss) and (m['profit_factor'] is None if not loss else close(m['profit_factor'],win/loss)))
    passed=all(x['passed'] for x in checks);res['gates']['audit']=passed;hist=all(v for k,v in res['gates'].items() if k!='forward_paper');res['status']='TEST NEDOKONCEN: forward PAPER required' if hist else 'NEPROSEL';(dest/'results.json').write_text(json.dumps(res,indent=2,allow_nan=False)+'\n');audit=dict(strategy=res['strategy'],passed=passed,checks=len(checks),trade_checks=n,failures=[x['name'] for x in checks if not x['passed']]);(dest/'audit.json').write_text(json.dumps(audit,indent=2)+'\n');print(audit,flush=True)
    if not passed:raise SystemExit(1)
if __name__=='__main__':main()
