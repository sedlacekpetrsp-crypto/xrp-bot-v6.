"""15m entry hypotheses with strictly completed 4h trend and fixed cost hurdle."""
from bisect import bisect_right
from statistics import mean
from elite.research_engine import aggregate,Decision,validate


def higher_trend(bars,k):
    if k<65:return False
    c=[b[4] for b in bars[k-65:k+1]]
    return c[-1]>mean(c[-60:]) and mean(c[-60:])>mean(c[-66:-6])


def signal(bars,k,name,trend,require_hurdle=True):
    if name not in ('v32','v33'):raise ValueError('unknown 15m candidate')
    if k<200:return Decision()
    tr=[max(bars[j][2]-bars[j][3],abs(bars[j][2]-bars[j-1][4]),
            abs(bars[j][3]-bars[j-1][4])) for j in range(k-32,k+1)]
    atr=mean(tr[-14:]);c=bars[k][4]
    if name=='v32':
        # Prior contraction excludes the current breakout candle.
        quiet=mean(tr[-9:-1])<.7*mean(tr[-33:-9])
        buy=quiet and c>max(b[2] for b in bars[k-16:k])
        stop=3*atr;target=6*atr
    else:
        prev=bars[k-1]
        buy=(prev[3]<min(b[3] for b in bars[k-17:k-1])
             and prev[4]<mean(b[4] for b in bars[k-20:k])
             and c>prev[2] and c>bars[k][1])
        stop=2*atr;target=4*atr
    allowed=trend and atr>0 and (not require_hurdle or target/c>=.02)
    return Decision(stop if buy and allowed else 0,target,exit=not trend,max_bars=576)


def decisions(rows,name,require_hurdle=True):
    validate(rows);bars=aggregate(rows,3);higher=aggregate(rows,48)
    ends=[b[0] for b in higher];flags=[higher_trend(higher,k) for k in range(len(higher))]
    out={}
    for k in range(200,len(bars)):
        i=bars[k][0];h=bisect_right(ends,i)-1
        out[i]=signal(bars,k,name,flags[h] if h>=0 else False,require_hurdle)
    return out
