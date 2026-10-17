"""Causal closed-trade loss streak overlay; always reset between simulations."""
from elite.research_engine import Decision
from elite.cross_market_v18 import decisions as btc_decisions
from elite.candidates_v28 import decisions as flow_decisions
from elite.combine_v36 import combine
DAY=86400000

class LossOverlay:
    def __init__(self,rows,base,strict,name):
        if name not in ('v38','v39'):raise ValueError('unknown loss overlay')
        self.times=[r[0] for r in rows];self.base=base;self.strict=strict;self.name=name
        self.reset()
    def reset(self):
        self.streak=0;self.until=0;self.events=[]
    def on_closed_trade(self,trade):
        self.streak=self.streak+1 if trade['pnl']<0 else 0
        if self.streak>=3:
            known_at=trade['exit_timestamp']+300000
            self.until=known_at+7*DAY
            self.events.append(dict(trigger_exit_index=trade['exit_index'],known_at=known_at,until=self.until))
            self.streak=0
    def for_position(self,index,owner=None):
        d=self.base.get(index,Decision())
        active=self.times[index+1]<self.until
        if not active:return d
        if self.name=='v39':return self.strict.get(index,Decision())
        # Entry pause never suppresses an exit signal.
        return Decision(0,d.target_distance,d.exit,d.max_bars)


def prepare(rows,btc,flows):
    base=btc_decisions(rows,btc,'v18');flow=flow_decisions(rows,flows,'v28')
    if base.keys()!=flow.keys():raise ValueError('signal mismatch')
    strict={i:combine(base[i],flow[i],'v37') for i in base}
    return {n:LossOverlay(rows,base,strict,n) for n in ('v38','v39')}
