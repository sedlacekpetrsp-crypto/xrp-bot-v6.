"""Fixed UTC range hypotheses; at most one eligible entry signal per day."""
from elite.research_engine import aggregate, Decision, validate
DAY=86400000


def decisions(rows,name):
    if name not in ('v49','v50'):raise ValueError('unknown session candidate')
    validate(rows);bars=aggregate(rows,12);out={}
    day=None;opening=[];used=False;complete=False
    for k,bar in enumerate(bars):
        i,o,h,l,c=bar;ts=rows[i][0];key=ts//DAY;hour=(ts//3600000)%24
        if key!=day:
            day=key;opening=[];used=False;complete=(hour==0)
        if hour<6:
            opening.append(bar)
            continue
        if not complete or len(opening)!=6 or used or hour>21:continue
        high=max(b[2] for b in opening);low=min(b[3] for b in opening)
        width=high-low
        if not .01<=width/opening[-1][4]<=.06:continue
        if name=='v49':
            buy=bars[k-1][4]<=high<c
            stop=width;target=2*width
        else:
            stop=c-l+.1*width;target=high-c
            buy=l<low<c and target>=2*stop
        if buy and stop>0 and target/c>=.02:
            # Entry at the next 5m open; expiry at next UTC midnight open.
            remaining=((key+1)*DAY-(ts+300000))//300000
            out[i]=Decision(stop,target,max_bars=int(remaining))
            used=True
    return out
