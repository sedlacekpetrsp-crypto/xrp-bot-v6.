"""Causal entry routing with position-owned exits, shared account and one slot."""
from dataclasses import dataclass
from statistics import mean
from elite.research_engine import Decision,aggregate,decisions as early_decisions
from elite.candidates_v8 import decisions as later_decisions,efficiency

@dataclass(frozen=True)
class OwnedDecision(Decision):
    source: str = ''


def owned(d,name):
    return OwnedDecision(d.stop_distance,d.target_distance,d.exit,d.max_bars,name)

class Router:
    def __init__(self,streams,priority,regime=None):
        self.streams=streams;self.priority=tuple(priority);self.regime=regime
    def for_position(self,index,owner=None):
        if owner is not None:
            # A component cannot close another component's position.
            return owned(self.streams[owner].get(index,Decision()),owner)
        allowed=self.priority
        if self.regime is not None:
            allowed=('v5',) if self.regime.get(index,False) else ('v8',)
        for name in allowed:
            d=self.streams[name].get(index,Decision())
            if d.stop_distance>0:
                return owned(d,name)
        return Decision()


def regime_series(rows):
    bars=aggregate(rows,12);close=[b[4] for b in bars];out={};cursor=0;flag=False
    for k,bar in enumerate(bars):
        end=bar[0]
        # New flag is usable only after the final constituent candle closes.
        for i in range(cursor,end):out[i]=flag
        flag=(k>=167 and close[k]>mean(close[k-167:k+1]) and efficiency(close[k-72:k+1])>.20)
        out[end]=flag;cursor=end+1
    for i in range(cursor,len(rows)):out[i]=flag
    return out


def streams(rows):
    return {n:(early_decisions(rows,n) if n=='v5' else later_decisions(rows,n)) for n in ('v5','v8','v10','v11')}


def make_router(all_streams,name,regime=None):
    if name=='v15':return Router(all_streams,('v8','v10','v5'))
    if name=='v16':
        if regime is None:raise ValueError('V16 requires regime')
        return Router(all_streams,('v5','v8'),regime)
    if name=='v17':return Router(all_streams,('v8','v10','v11'))
    raise ValueError('unknown router')
