import datetime as dt,gzip,hashlib,json,pathlib,sys
from research.xrpl_dex_liquidity_replenishment_v1 import DAY,entry_day,make_signals,summarize
UTC=dt.timezone.utc;RIPPLE_EPOCH=946684800
def close(a,b,tol=1e-8):return abs(a-b)<=tol*max(1,abs(a),abs(b))
def main():
    cache=pathlib.Path(sys.argv[1]);dest=pathlib.Path(sys.argv[2]);res=json.loads((dest/'results.json').read_text());checks=[]
    def check(n,v):checks.append(dict(name=n,passed=bool(v)))
    grouped={}
    for m in res['xrpl_manifest']:
        raw=(cache/m['cache_file']).read_bytes();check('hash_'+m['cache_file'],hashlib.sha256(raw).hexdigest()==m['sha256'] and len(raw)==m['bytes']);grouped.setdefault(m['ledger_index'],{})[m['kind'].split('_')[-1]]=json.loads(raw)['result']
    obs=[]
    for idx in sorted(grouped):
        g=grouped[idx];l=g['ledger'];led=l['ledger'];base=dict(validated=l.get('validated'),ledger_index=int(l['ledger_index']),ledger_hash=l['ledger_hash'],close_time_ms=(int(led['close_time'])+RIPPLE_EPOCH)*1000);obs.append(summarize(base,g['asks'],g['bids']))
    with gzip.open(dest/'observations.json.gz','rt') as h:saved=json.load(h)
    check('observations',obs==saved);signals=make_signals(obs);check('signals_total',len(signals)==res['signals_total'])
    price=[]
    for m in res['price_manifest']:
        raw=(cache/m['cache_file']).read_bytes();check('hash_'+m['cache_file'],hashlib.sha256(raw).hexdigest()==m['sha256'] and len(raw)==m['bytes']);doc=json.loads(raw);price += [dict(timestamp=int(x[0]),open=float(x[1]),high=float(x[2]),low=float(x[3]),close=float(x[4])) for x in doc]
    check('price_rows',len(price)==res['data_quality']['price_rows']);check('price_gaps',all(b['timestamp']-a['timestamp']==DAY for a,b in zip(price,price[1:])));index={x['timestamp']:i for i,x in enumerate(price)}
    with gzip.open(dest/'trades.json.gz','rt') as h:ledgers=json.load(h)
    n=0
    for key,trades in ledgers.items():
        fee=.0019 if key.endswith('_stress') else .00095;slip=.0004 if key.endswith('_stress') else .0002
        for a,b in zip(trades,trades[1:]):check('nonoverlap_'+key+'_'+str(n),a['exit_timestamp']<b['entry_timestamp'])
        for t in trades:
            n+=1;s=signals[t['entry_timestamp']];check('signal_'+str(n),t['ledger_index']==s['ledger_index'] and t['ledger_hash']==s['ledger_hash'] and close(t['total_depth_xrp'],s['total_depth_xrp']) and t['total_depth_xrp']>t['prior_depth_xrp']);i=index[t['entry_timestamp']];row=price[i];check('lag_'+str(n),entry_day(t['observation_timestamp'])==t['entry_timestamp'] and t['entry_timestamp']-t['observation_timestamp']>=2*DAY);check('entry_'+str(n),close(t['raw_entry'],row['open']) and close(t['entry'],row['open']*(1+slip)));av=sum(max(price[j]['high']-price[j]['low'],abs(price[j]['high']-price[j-1]['close']),abs(price[j]['low']-price[j-1]['close'])) for j in range(i-14,i))/14;check('atr_'+str(n),close(t['atr'],av));check('limits_'+str(n),t['leg_notional']<=t['entry_equity']*.2+1e-7 and t['qty']*(t['entry']-t['stop'])<=t['entry_equity']*.005+1e-7)
            j=index[t['exit_timestamp']];erow=price[j];expected=erow['open'] if t['reason']=='GAP_STOP' else t['stop'] if t['reason']=='STOP' else t['target'] if t['reason']=='TARGET' else erow['close'];check('exit_'+str(n),close(t['raw_exit'],expected) and close(t['exit'],expected*(1-slip)));fees=t['qty']*t['entry']*fee+t['qty']*t['exit']*fee;check('cost_'+str(n),close(t['fees'],fees) and close(t['pnl'],t['qty']*(t['exit']-t['entry'])-fees))
        m=res['runs'][key];win=sum(max(0,x['pnl']) for x in trades);loss=-sum(min(0,x['pnl']) for x in trades);net=sum(x['pnl'] for x in trades);check('report_'+key,m['trades']==len(trades) and close(m['net_pnl'],net) and close(m['gross_profit'],win) and close(m['gross_loss'],loss) and (m['profit_factor'] is None if not loss else close(m['profit_factor'],win/loss)))
    passed=all(x['passed'] for x in checks);res['gates']['audit']=passed;hist=all(v for k,v in res['gates'].items() if k!='forward_paper');res['status']='TEST NEDOKONCEN: forward PAPER required' if hist else 'NEPROSEL';(dest/'results.json').write_text(json.dumps(res,indent=2,allow_nan=False)+'\n');audit=dict(strategy=res['strategy'],passed=passed,checks=len(checks),trade_checks=n,failures=[x['name'] for x in checks if not x['passed']]);(dest/'audit.json').write_text(json.dumps(audit,indent=2)+'\n');print(audit,flush=True)
    if not passed:raise SystemExit(1)
if __name__=='__main__':main()
