"""Independent arithmetic/source audit; intentionally does not import strategy code."""
import gzip,hashlib,json,math,pathlib,sys
DAY=86_400_000

def weights(vols,cap=.5):
    inv={k:1/v for k,v in vols.items()};out={};free=set(inv);rem=1.0
    while free:
        den=sum(inv[k] for k in free);trial={k:rem*inv[k]/den for k in free};over={k for k,v in trial.items() if v>cap+1e-15}
        if not over:out.update(trial);break
        for k in sorted(over):out[k]=cap;free.remove(k);rem-=cap
    return out
def vol(rows,i):
    c=[x['close'] for x in rows[i-31:i]];r=[math.log(b/a) for a,b in zip(c,c[1:])];m=sum(r)/30
    return math.sqrt(sum((x-m)**2 for x in r)/29)*math.sqrt(365)
def atr(rows,i):
    return sum(max(rows[j]['high']-rows[j]['low'],abs(rows[j]['high']-rows[j-1]['close']),abs(rows[j]['low']-rows[j-1]['close'])) for j in range(i-14,i))/14
def close(a,b,tol=1e-8):return abs(a-b)<=tol*max(1,abs(a),abs(b))
def main():
    cache=pathlib.Path(sys.argv[1]);dest=pathlib.Path(sys.argv[2]);res=json.loads((dest/'results.json').read_text());checks=[];markets={}
    def check(name,value):checks.append(dict(name=name,passed=bool(value)))
    for s in res['data_quality']['symbols']:
        rows=[];items=[x for x in res['manifest'] if x['symbol']==s]
        for m in items:
            raw=(cache/m['cache_file']).read_bytes();check('hash_'+s+'_'+m['cache_file'],hashlib.sha256(raw).hexdigest()==m['sha256'] and len(raw)==m['bytes']);doc=json.loads(raw);check('page_rows_'+m['cache_file'],len(doc)==m['rows'])
            rows += [dict(timestamp=int(x[0]),open=float(x[1]),high=float(x[2]),low=float(x[3]),close=float(x[4])) for x in doc]
        markets[s]=rows;check('rows_'+s,len(rows)==res['data_quality']['rows'][s]);check('gaps_'+s,all(b['timestamp']-a['timestamp']==DAY for a,b in zip(rows,rows[1:])))
    symbols=sorted(markets);check('alignment',all([x['timestamp'] for x in markets[s]]==[x['timestamp'] for x in markets[symbols[0]]] for s in symbols[1:]));index={b['timestamp']:i for i,b in enumerate(markets[symbols[0]])}
    with gzip.open(dest/'trades.json.gz','rt') as h:ledgers=json.load(h)
    total_trade_checks=0
    for key,trades in ledgers.items():
        fee=.0019 if key.endswith('_stress') else .00095;slip=.0004 if key.endswith('_stress') else .0002
        groups={};by_symbol={s:[] for s in symbols}
        for t in trades:
            total_trade_checks+=1;i=index[t['entry_timestamp']];s=t['symbol'];row=markets[s][i];groups.setdefault(t['entry_timestamp'],[]).append(t);by_symbol[s].append(t)
            check('entry_monday_'+str(total_trade_checks),(t['entry_timestamp']//DAY+3)%7==0);check('entry_raw_'+str(total_trade_checks),close(t['entry_raw'],row['open']));check('entry_fill_'+str(total_trade_checks),close(t['entry_fill'],row['open']*(1+slip)))
            vols={z:vol(markets[z],i) for z in symbols};w=weights(vols);check('vol_'+str(total_trade_checks),close(t['realized_vol'],vols[s]));check('weight_'+str(total_trade_checks),close(t['target_weight'],w[s]) and t['target_weight']<=.5+1e-12)
            av=atr(markets[s],i);check('atr_'+str(total_trade_checks),close(t['atr'],av));check('stop_'+str(total_trade_checks),close(t['stop'],t['entry_fill']-3*av))
            j=index[t['exit_timestamp']];erow=markets[s][j];reason=t['exit_reason']
            expected=erow['open'] if reason in ('weekly_rebalance','gap_stop') else erow['close'] if reason=='segment_end' else t['stop']
            check('exit_raw_'+str(total_trade_checks),close(t['exit_raw'],expected));check('gap_rule_'+str(total_trade_checks),reason!='gap_stop' or erow['open']<=t['stop']);check('stop_rule_'+str(total_trade_checks),reason!='stop' or (erow['open']>t['stop'] and erow['low']<=t['stop']))
            check('exit_fill_'+str(total_trade_checks),close(t['exit_fill'],t['exit_raw']*(1-slip)));ef=t['qty']*t['entry_fill']*fee;xf=t['qty']*t['exit_fill']*fee
            check('fees_'+str(total_trade_checks),close(t['entry_fee'],ef) and close(t['exit_fee'],xf) and close(t['fees'],ef+xf));check('pnl_'+str(total_trade_checks),close(t['pnl'],t['qty']*(t['exit_fill']-t['entry_fill'])-t['fees']))
        for s,q in by_symbol.items():
            q.sort(key=lambda x:x['entry_timestamp']);check('nonoverlap_'+key+'_'+s,all(a['exit_timestamp']<=b['entry_timestamp'] for a,b in zip(q,q[1:])))
        for ts,g in groups.items():check('group_'+key+'_'+str(ts),len(g)==3 and close(sum(x['target_weight'] for x in g),1))
        m=res['runs'][key];win=sum(max(0,x['pnl']) for x in trades);loss=-sum(min(0,x['pnl']) for x in trades);net=sum(x['pnl'] for x in trades)
        check('report_'+key,m['trades']==len(trades) and close(m['net_pnl'],net) and close(m['gross_profit'],win) and close(m['gross_loss'],loss) and (m['profit_factor'] is None if loss==0 else close(m['profit_factor'],win/loss)))
    check('aggregate_count',res['aggregate_oos']['trades']==sum(len(ledgers[str(y)+'_base']) for y in range(2022,2027)));check('stress_count',res['aggregate_stress']['trades']==sum(len(ledgers[str(y)+'_stress']) for y in range(2022,2027)))
    passed=all(x['passed'] for x in checks);res['gates']['audit']=passed;hist=all(v for k,v in res['gates'].items() if k not in ('forward_paper',));res['status']='TEST NEDOKONCEN: forward PAPER required' if hist else 'NEPROSEL';(dest/'results.json').write_text(json.dumps(res,indent=2,allow_nan=False)+'\n')
    audit=dict(strategy=res['strategy'],passed=passed,checks=len(checks),trade_checks=total_trade_checks,failures=[x['name'] for x in checks if not x['passed']]);(dest/'audit.json').write_text(json.dumps(audit,indent=2)+'\n');print(audit,flush=True)
    if not passed:raise SystemExit(1)
if __name__=='__main__':main()
