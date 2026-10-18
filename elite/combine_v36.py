"""Boolean composition of frozen BTC and taker-flow gates, one V5 position."""
from math import isclose
from elite.research_engine import Decision
from elite.cross_market_v18 import decisions as btc_decisions
from elite.candidates_v28 import decisions as flow_decisions


def combine(a,b,name):
    if name not in ('v36','v37'):raise ValueError('unknown filter combination')
    if (a.target_distance,a.exit,a.max_bars)!=(b.target_distance,b.exit,b.max_bars):
        raise ValueError('incompatible price/exit family')
    x=a.stop_distance>0;y=b.stop_distance>0
    if x and y and not isclose(a.stop_distance,b.stop_distance,rel_tol=1e-12):
        raise ValueError('incompatible entry sizing')
    allowed=(x or y) if name=='v36' else (x and y)
    return Decision(max(a.stop_distance,b.stop_distance) if allowed else 0,
                    a.target_distance,a.exit,a.max_bars)


def prepare(rows,btc,flows):
    a=btc_decisions(rows,btc,'v18');b=flow_decisions(rows,flows,'v28')
    if a.keys()!=b.keys():raise ValueError('signal timestamps mismatch')
    streams={n:{i:combine(a[i],b[i],n) for i in a} for n in ('v36','v37')}
    counts=dict(btc_only=0,flow_only=0,both=0,neither=0)
    for i in a:
        x=a[i].stop_distance>0;y=b[i].stop_distance>0
        key='both' if x and y else 'btc_only' if x else 'flow_only' if y else 'neither'
        counts[key]+=1
    return streams,counts
