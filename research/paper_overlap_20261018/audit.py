"""Historical overlap / fixed-fill exclusion analysis, NOT a strategy backtest."""
import itertools,json,pathlib,sys
from datetime import datetime
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]))
from paper_overlap_guard import asset_key
HERE=pathlib.Path(__file__).parent

def ts(value):
    t=datetime.fromisoformat(value.replace('Z','+00:00'))
    if t.tzinfo is None: raise ValueError('Timezone required')
    return t.timestamp()

def audit(rows):
    keys=set()
    for r in rows:
        key=(r['bot'],r['id'])
        if key in keys: raise ValueError('Duplicate trade ID')
        keys.add(key)
        if ts(r['closed_at'])<=ts(r['opened_at']): raise ValueError('Invalid interval')
    pairs={}
    for a,b in itertools.combinations(rows,2):
        if a['bot']==b['bot']: continue
        duration=min(ts(a['closed_at']),ts(b['closed_at']))-max(ts(a['opened_at']),ts(b['opened_at']))
        if duration<=0: continue  # Half-open intervals: close before open at a tie.
        key=' / '.join(sorted((a['bot'],b['bot'])))
        p=pairs.setdefault(key,dict(pairs=0,same_asset=0,same_asset_same_side=0,unknown_asset_pairs=0,pair_seconds=0))
        same=asset_key(a.get('symbol')) is not None and asset_key(a.get('symbol'))==asset_key(b.get('symbol'))
        p['unknown_asset_pairs']+=int(asset_key(a.get('symbol')) is None or asset_key(b.get('symbol')) is None)
        p['pairs']+=1;p['same_asset']+=int(same);p['same_asset_same_side']+=int(same and a['side']==b['side']);p['pair_seconds']+=duration
    accepted=[];blocked=[]
    for r in sorted(rows,key=lambda r:(ts(r['opened_at']),r['bot'],r['id'])):
        asset=asset_key(r.get('symbol'))
        if asset is None or any(asset_key(p.get('symbol'))==asset and ts(p['closed_at'])>ts(r['opened_at']) for p in accepted):blocked.append(r)
        else:accepted.append(r)
    summary={}
    for bot in sorted({r['bot'] for r in rows}):
        baseline=[r for r in rows if r['bot']==bot];kept=[r for r in accepted if r['bot']==bot]
        summary[bot]={'unknown_asset_trades':sum(asset_key(r.get('symbol')) is None for r in baseline),'baseline_count':len(baseline),'baseline_net':sum(r['net_pnl'] for r in baseline),'fees':sum(r['fees'] for r in baseline),'kept_count':len(kept),'fixed_fill_net':sum(r['net_pnl'] for r in kept)}
    return dict(scope='Fixed historical fills from multiple versions; exclusion only. No substitute signals, equity resizing or profitability validation. Unknown symbols rejected from candidate subset.',pairs=pairs,summary=summary,blocked=len(blocked))

if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('Usage: audit.py /path/to/private/ledger.json (output to stdout)')
    result=audit(json.loads(pathlib.Path(sys.argv[1]).read_text()))
    print(json.dumps(result,indent=2))
