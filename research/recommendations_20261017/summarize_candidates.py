"""Summarize archived sampled marks; never treat them as execution PnL."""
import collections
import gzip
import hashlib
import json
from pathlib import Path
import statistics

root=Path(__file__).parent
raw=gzip.decompress((root/'candidate_snapshot.json.gz').read_bytes())
assert hashlib.sha256(raw).hexdigest()==json.loads((root/'candidate_manifest.json').read_text())['sha256']
cs=json.loads(raw)['candidates']
out={'scope':'Unique overlapping scan candidates; sampled future marks, not fills or strategy PnL. No profitability claim.',
     'candidates':len(cs),'counts':dict(collections.Counter(c['strategy'] for c in cs)),'groups':[]}
for strategy in sorted(out['counts']):
    rows=[r for r in cs if r['strategy']==strategy]
    for minutes in ('15','60','240'):
        follow=[r.get('followups',{}).get(minutes,{}) for r in rows]
        valid=[f for f in follow if 'directional_move_pct' in f and not f.get('missed')]
        vals=[f['directional_move_pct']-f.get('estimated_round_trip_cost_pct',0) for f in valid]
        out['groups'].append(dict(strategy=strategy,horizon_minutes=int(minutes),total=len(rows),timely_marks=len(vals),
            missed=sum(bool(f.get('missed')) for f in follow),pending=sum(not bool(f) for f in follow),
            mean_directional_less_estimated_cost_pct=statistics.mean(vals) if vals else None,
            median_directional_less_estimated_cost_pct=statistics.median(vals) if vals else None,
            cost_cleared=sum(v>0 for v in vals)))
(root/'candidate_summary.json').write_text(json.dumps(out,indent=2)+'\n')
