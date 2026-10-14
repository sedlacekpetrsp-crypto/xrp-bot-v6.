"""Monthly causal selection of fixed strategies; incumbent owns its exits."""
from bisect import bisect_left,bisect_right
from datetime import datetime,timezone
from elite.research_engine import Decision,simulate,decisions as original
from elite.candidates_v8 import decisions as family
from elite.cross_market_v18 import decisions as cross,align
from elite.exit_v21 import decisions as exits
from elite.candidates_v24 import decisions as retest
from elite.portfolio_v15 import owned
from elite.research_run import compact

NAMES=('v5','v8','v10','v18','v22','v25')
DAY=86400000

def select(scores,name):
    if name not in ('v30','v31'):raise ValueError('unknown selector')
    eligible=[]
    for n in NAMES:
        a=scores[n]['180'];b=scores[n]['90']
        if not (a['trades']>=5 and a['net_pnl']>0 and a['profit_factor'] is not None
                and a['profit_factor']>=1.2 and a['close_mtm_drawdown_pct']<=10):continue
        if name=='v31' and not (b['trades']>=3 and b['net_pnl']>0):continue
        eligible.append(n)
    # Stable predeclared tie order, no access to forward returns.
    return max(eligible,key=lambda n:scores[n]['180']['net_pnl']) if eligible else None


class MonthlyRouter:
    def __init__(self,streams,starts,choices):
        self.streams=streams;self.starts=starts;self.choices=choices
    def for_position(self,index,owner=None):
        if owner is not None:return owned(self.streams[owner].get(index,Decision()),owner)
        # Decision index refers to the closed bar; execution is index+1.
        k=bisect_right(self.starts,index+1)-1
        chosen=self.choices[k] if k>=0 else None
        return owned(self.streams[chosen].get(index,Decision()),chosen) if chosen else Decision()


def schedule(rows,streams,scorer=simulate):
    times=[r[0] for r in rows];starts=[];records=[]
    for i,row in enumerate(rows):
        date=datetime.fromtimestamp(row[0]/1000,tz=timezone.utc)
        if not (date.day==1 and date.hour==0 and date.minute==0):continue
        if row[0]-rows[0][0]<180*DAY:continue
        scores={}
        for n in NAMES:
            scores[n]={}
            for days in (180,90):
                lo=bisect_left(times,row[0]-days*DAY)
                # end=i excludes every candle of the selected month.
                r=scorer(rows,streams[n],lo,i,fee=.002,slip=.0006,half_spread=.0002)
                scores[n][str(days)]=compact(r)
        starts.append(i)
        records.append(dict(start_index=i,start_timestamp=row[0],training_end_timestamp=rows[i-1][0],
                            scores=scores,choices={n:select(scores,n) for n in ('v30','v31')}))
    return starts,records


def prepare(rows,btc):
    align(rows,btc)
    streams={'v5':original(rows,'v5'),'v8':family(rows,'v8'),'v10':family(rows,'v10'),
             'v18':cross(rows,btc,'v18'),'v22':exits(rows,btc,'v22'),'v25':retest(rows,'v25')}
    starts,records=schedule(rows,streams)
    return {n:MonthlyRouter(streams,starts,[r['choices'][n] for r in records]) for n in ('v30','v31')},records
