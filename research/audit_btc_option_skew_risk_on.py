"""Independent source/arithmetic audit without importing strategy code."""
import datetime as dt,gzip,hashlib,json,math,pathlib,re,statistics,sys
DAY=86_400_000;UTC=dt.timezone.utc;PAT=re.compile(r'^BTC-(\d{1,2}[A-Z]{3}\d{2})-(\d+(?:\.\d+)?)-([CP])$')
def close(a,b,tol=1e-8):return abs(a-b)<=tol*max(1,abs(a),abs(b))
def metric(trades,friday):
    valid=[]
    for x in {str(z['trade_id']):z for z in trades}.values():
        m=PAT.match(str(x.get('instrument_name','')));iv=float(x.get('iv') or 0);spot=float(x.get('index_price') or 0)
        if not m or iv<=0 or spot<=0:continue
        exp=dt.datetime.strptime(m.group(1),'%d%b%y').replace(tzinfo=UTC,hour=8);tau=(exp.timestamp()*1000-int(x['timestamp']))/(365*DAY)
        if not 14/365<=tau<=60/365:continue
        sig=iv/100;strike=float(m.group(2));d1=(math.log(spot/strike)+.5*sig*sig*tau)/(sig*math.sqrt(tau));n=.5*(1+math.erf(d1/math.sqrt(2)));side=m.group(3);delta=n if side=='C' else n-1
        if .15<=abs(delta)<=.35:valid.append(dict(side=side,iv=iv,amount=float(x.get('amount') or 0)))
    c=[x for x in valid if x['side']=='C'];p=[x for x in valid if x['side']=='P'];base=dict(friday_timestamp=friday,window_start=friday+12*3_600_000,window_end=friday+13*3_600_000-1,raw_trades=len({str(z['trade_id']) for z in trades}),eligible_calls=len(c),eligible_puts=len(p),call_amount=sum(x['amount'] for x in c),put_amount=sum(x['amount'] for x in p))
    if len(c)<5 or len(p)<5 or base['call_amount']<1 or base['put_amount']<1:return dict(base,eligible=False,reason='insufficient_sides')
    a=statistics.median(x['iv'] for x in c);b=statistics.median(x['iv'] for x in p);return dict(base,eligible=True,reason='ok',call_median_iv=a,put_median_iv=b,risk_reversal=a-b,signal=a-b>0,entry_timestamp=friday+3*DAY)
def same(a,b):
    if a.keys()!=b.keys():return False
    return all(close(a[k],b[k]) if isinstance(a[k],float) else a[k]==b[k] for k in a)
def main():
    cache=pathlib.Path(sys.argv[1]);dest=pathlib.Path(sys.argv[2]);res=json.loads((dest/'results.json').read_text());checks=[]
    def check(name,x):checks.append(dict(name=name,passed=bool(x)))
    weeks={}
    for m in res['manifest']:
        raw=(cache/m['cache_file']).read_bytes();check('hash_'+m['cache_file'],hashlib.sha256(raw).hexdigest()==m['sha256'] and len(raw)==m['bytes']);doc=json.loads(raw);rows=doc if m['kind'].startswith('binance') else doc['result']['trades'];check('rows_'+m['cache_file'],len(rows)==m['rows'])
        if m['kind'].startswith('deribit'):
            check('complete_flag_'+m['cache_file'],m['used']==(not m['has_more']))
            if m['used']:weeks.setdefault(str(m['week']),[]).extend(rows)
    with gzip.open(dest/'observations.json.gz','rt') as h:observations=json.load(h)
    check('observation_count',len(observations)==len(weeks));om={str(x['friday_timestamp']):x for x in observations}
    for f,t in weeks.items():check('metric_'+f,same(metric(t,int(f)),om[f]))
    price=[]
    for m in res['manifest']:
        if m['kind'].startswith('binance'):
            doc=json.loads((cache/m['cache_file']).read_bytes());price += [dict(timestamp=int(x[0]),open=float(x[1]),high=float(x[2]),low=float(x[3]),close=float(x[4])) for x in doc]
    check('price_rows',len(price)==res['data_quality']['price_rows']);check('price_gaps',all(b['timestamp']-a['timestamp']==DAY for a,b in zip(price,price[1:])));index={x['timestamp']:i for i,x in enumerate(price)}
    with gzip.open(dest/'trades.json.gz','rt') as h:ledgers=json.load(h)
    n=0
    for key,trades in ledgers.items():
        fee=.0019 if key.endswith('_stress') else .00095;slip=.0004 if key.endswith('_stress') else .0002
        for a,b in zip(trades,trades[1:]):check('nonoverlap_'+key+'_'+str(n),a['exit_timestamp']<b['entry_timestamp'])
        for t in trades:
            n+=1;i=index[t['entry_timestamp']];row=price[i];o=om[str(t['friday_timestamp'])];check('causal_'+str(n),o['eligible'] and o['signal'] and o['entry_timestamp']==t['entry_timestamp'] and o['window_end']<t['entry_timestamp']);check('rr_'+str(n),close(o['risk_reversal'],t['risk_reversal']));check('entry_raw_'+str(n),close(row['open'],t['raw_entry']));check('entry_fill_'+str(n),close(t['entry'],t['raw_entry']*(1+slip)))
            av=sum(max(price[j]['high']-price[j]['low'],abs(price[j]['high']-price[j-1]['close']),abs(price[j]['low']-price[j-1]['close'])) for j in range(i-14,i))/14;check('atr_'+str(n),close(av,t['atr']));check('stop_target_'+str(n),close(t['stop'],t['entry']-2*av) and close(t['target'],t['entry']+3*(t['entry']-t['stop'])));check('limits_'+str(n),t['leg_notional']<=t['entry_equity']*.2+1e-7 and t['qty']*(t['entry']-t['stop'])<=t['entry_equity']*.005+1e-7)
            j=index[t['exit_timestamp']];erow=price[j];reason=t['reason'];expected=erow['open'] if reason=='GAP_STOP' else t['stop'] if reason=='STOP' else t['target'] if reason=='TARGET' else erow['close'];check('exit_raw_'+str(n),close(t['raw_exit'],expected));check('gap_'+str(n),reason!='GAP_STOP' or erow['open']<=t['stop']);check('stop_'+str(n),reason!='STOP' or (erow['open']>t['stop'] and erow['low']<=t['stop']));check('exit_fill_'+str(n),close(t['exit'],t['raw_exit']*(1-slip)))
            fees=t['qty']*t['entry']*fee+t['qty']*t['exit']*fee;check('fees_'+str(n),close(fees,t['fees']));check('pnl_'+str(n),close(t['pnl'],t['qty']*(t['exit']-t['entry'])-fees))
        m=res['runs'][key];win=sum(max(0,x['pnl']) for x in trades);loss=-sum(min(0,x['pnl']) for x in trades);net=sum(x['pnl'] for x in trades);check('report_'+key,m['trades']==len(trades) and close(m['net_pnl'],net) and close(m['gross_profit'],win) and close(m['gross_loss'],loss) and (m['profit_factor'] is None if not loss else close(m['profit_factor'],win/loss)))
    check('aggregate_count',res['aggregate_oos']['trades']==sum(len(ledgers[str(y)+'_base']) for y in range(2022,2027)));passed=all(x['passed'] for x in checks);res['gates']['audit']=passed;hist=all(v for k,v in res['gates'].items() if k!='forward_paper');res['status']='TEST NEDOKONCEN: forward PAPER required' if hist else 'NEPROSEL';(dest/'results.json').write_text(json.dumps(res,indent=2,allow_nan=False)+'\n');audit=dict(strategy=res['strategy'],passed=passed,checks=len(checks),trade_checks=n,failures=[x['name'] for x in checks if not x['passed']]);(dest/'audit.json').write_text(json.dumps(audit,indent=2)+'\n');print(audit,flush=True)
    if not passed:raise SystemExit(1)
if __name__=='__main__':main()
