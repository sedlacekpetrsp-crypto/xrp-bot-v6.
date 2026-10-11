"""Pre-registered diagnostic only. Never connects to a database or places orders."""
import argparse,contextlib,gzip,hashlib,io,json
from collections import defaultdict
from pathlib import Path
from research.best_validation import replay as r

HERE=Path(__file__).resolve().parent

def groups(trades):
    out=[]
    for setup in ('BREAKOUT','FIB_0618_0786','EMA_4H'):
        ts=[t for t in trades if t.get('setup')==setup]
        profit=sum(max(t['pnl'],0) for t in ts);loss=-sum(min(t['pnl'],0) for t in ts)
        out.append(dict(setup=setup,trades=len(ts),net=sum(t['pnl'] for t in ts),pf=profit/loss if loss else None,
            fees=sum(t['fees'] for t in ts),slippage=sum(t['slippage'] for t in ts)))
    return out

def main(folder):
    manifest=json.loads((HERE.parent/'best_validation/results/data_manifest.json').read_text())
    data={}
    for m in manifest:
        raw=(folder/(m['symbol']+'_5m.json')).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==m['sha256'],'Frozen data mismatch'
        rows=[[int(x[0]),*map(float,x[1:6]),int(x[6])] for x in json.loads(raw)]
        r.validate(rows);data[m['symbol']]=rows
    times=[x[0] for x in next(iter(data.values()))]
    assert all([x[0] for x in rows]==times for rows in data.values())
    signals=r.prepare(data);results=[];trades={}
    for label,start,end,slip in [('train','2026-07-04','2026-09-01',.0002),('validation','2026-09-01','2026-10-02',.0002),('validation_double_slippage','2026-09-01','2026-10-02',.0004)]:
        for variant in ('baseline','no_breakeven'):
            metrics,ts=r.simulate(data,signals,variant,start,end,slip)
            metrics.update(period=label,by_strategy=groups(ts));results.append(metrics);trades[label+':'+variant]=ts
            print(label,variant,round(metrics['net'],2),metrics['trades'],flush=True)
    val={x['variant']:x for x in results if x['period']=='validation'}
    stress=next(x for x in results if x['period']=='validation_double_slippage' and x['variant']=='no_breakeven')
    candidate=val['no_breakeven'];baseline=val['baseline']
    gates=dict(positive_net=candidate['net']>0,min_trades=candidate['trades']>=30,pf=candidate['pf'] is not None and candidate['pf']>=1.1,
        drawdown=candidate['drawdown_pct']<=baseline['drawdown_pct'],stress_positive=stress['net']>0)
    decision=dict(gates=gates,diagnostic_pass=all(gates.values()),promotion=False,
        reason='Known-data diagnostic only; future holdout and isolated PAPER required even if all gates pass.')
    out=HERE/'results';out.mkdir(exist_ok=True)
    (out/'results.json').write_text(json.dumps(results,indent=2))
    (out/'decision.json').write_text(json.dumps(decision,indent=2))
    (out/'data_manifest.json').write_text(json.dumps(manifest,indent=2))
    with gzip.GzipFile(filename=str(out/'trades.json.gz'),mode='wb',mtime=0) as f:f.write(json.dumps(trades,separators=(',',':')).encode())
    print(json.dumps(decision),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);a=p.parse_args();main(a.data)
