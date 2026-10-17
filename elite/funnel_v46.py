"""Post-result signal-count audit only, no relaxed-strategy backtests."""
import argparse,json
from pathlib import Path
from statistics import mean
from elite.research_data import load_cached
from elite.research_engine import aggregate
from elite.candidates_v8 import efficiency

def run(cache,out):
    rows,_=load_cached(cache);bars=aggregate(rows,12)
    counts=dict(hours=0,reclaim=0,reclaim_and_trend=0,reclaim_trend_and_efficiency=0,all_conditions=0)
    for k in range(200,len(bars)):
        counts['hours']+=1
        c=[b[4] for b in bars[k-200:k+1]]
        if not (c[-2]<=mean(c[-25:-1]) and c[-1]>mean(c[-24:])):continue
        counts['reclaim']+=1
        if not c[-1]>mean(c[-168:])>mean(c[-192:-24]):continue
        counts['reclaim_and_trend']+=1
        if efficiency(c[-50:-1])<.35:continue
        counts['reclaim_trend_and_efficiency']+=1
        atr=mean(max(bars[j][2]-bars[j][3],abs(bars[j][2]-bars[j-1][4]),abs(bars[j][3]-bars[j-1][4])) for j in range(k-14,k))
        if 6*atr/c[-1]>=.02:counts['all_conditions']+=1
    result={'phase':'POST_RESULT_COUNTS_ONLY','v46':counts}
    Path(out).write_text(json.dumps(result,indent=2));print(json.dumps(result))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cache',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();run(a.cache,a.out)
