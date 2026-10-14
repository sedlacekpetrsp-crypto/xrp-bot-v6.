"""Causal Monday-anchored VWAP from actual quote/base turnover."""
from statistics import mean
from elite.research_engine import aggregate,Decision,validate
from elite.turnover_v34 import align_turnover
DAY=86400000
WEEK=7*DAY

def week_key(ts):return (ts+3*DAY)//WEEK

def weekly_vwap(rows,turnover):
    align_turnover(rows,turnover)
    out=[];week=None;volume=quote=0.;complete=False
    for row,(_,v,q) in zip(rows,turnover):
        key=week_key(row[0])
        if key!=week:
            week=key;volume=quote=0.
            complete=(row[0]+3*DAY)%WEEK==0
        volume+=v;quote+=q
        out.append(quote/volume if complete and volume>0 else None)
    return out


def atr(bars,k):
    return mean(max(bars[j][2]-bars[j][3],abs(bars[j][2]-bars[j-1][4]),
                    abs(bars[j][3]-bars[j-1][4])) for j in range(k-13,k+1))


def signal(bars,k,name,vwap,previous,eligible):
    if name not in ('v34','v35'):raise ValueError('unknown VWAP candidate')
    if k<200 or not eligible or vwap is None or previous is None:return Decision()
    c=bars[k][4];p=bars[k-1][4];a=atr(bars,k)
    if name=='v34':
        slow=mean(b[4] for b in bars[k-167:k+1]);old=mean(b[4] for b in bars[k-191:k-23])
        buy=p<=previous and c>vwap and c>slow and slow>old
        return Decision(3*a if buy else 0,exit=c<vwap,max_bars=2016)
    buy=p<previous-2*atr(bars,k-1) and c>bars[k-1][2] and c<vwap
    return Decision(2*a if buy else 0,4*a,exit=c>=vwap,max_bars=576)


def decisions(rows,turnover,name):
    validate(rows);curve=weekly_vwap(rows,turnover);bars=aggregate(rows,12);out={}
    for k in range(200,len(bars)):
        i=bars[k][0];j=bars[k-1][0]
        eligible=(week_key(rows[i][0])==week_key(rows[j][0]) and
                  (rows[i][0]+3*DAY)%WEEK>=DAY)
        out[i]=signal(bars,k,name,curve[i],curve[j],eligible)
    return out
