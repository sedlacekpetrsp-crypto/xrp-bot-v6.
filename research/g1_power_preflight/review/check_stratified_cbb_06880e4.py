"""Claude review of ChatGPT stratified CBB @ 06880e47 (synthetic only, no market data).
Usage: python3 check_stratified_cbb_06880e4.py <worktree at 06880e47>"""
import sys, math, random
sys.path.insert(0, sys.argv[1])  
import numpy as np
from research.g1_power_preflight.g1_stratified_cbb import stratified_paired_bss as S

# 1) exact equality vs independent reference with identical RNG consumption + bridge audit via provenance tags
def ref_impl(folds, block, reps, seed, audit=None):
    rng = random.Random(seed); out=[]
    for _ in range(reps):
        num=den=0.0
        for fi,(m,r) in enumerate(folds):
            n=len(m); idx=[]
            while len(idx)<n:
                s=rng.randrange(n); idx += [(s+k)%n for k in range(block)]
            idx=idx[:n]
            if audit is not None: audit.append((fi,n,idx))
            num+=math.fsum(m[i] for i in idx); den+=math.fsum(r[i] for i in idx)
        out.append(1-num/den)
    return out
rs=np.random.default_rng(7)
folds=[([float(x) for x in rs.uniform(0,.3,n)], [float(x) for x in rs.uniform(.05,.4,n)]) for n in (56,90,140)]
a=S(folds,block_days=28,replicates=500,seed=5); aud=[]
b=ref_impl(folds,28,500,5,aud)
print("max|diff| vs reference:", max(abs(x-y) for x,y in zip(a,b)))
# block contiguity mod n and fold confinement
bad=0
for fi,n,idx in aud:
    assert all(0<=i<n for i in idx) and len(idx)==n
    breaks=sum(1 for j in range(1,n) if idx[j]!=(idx[j-1]+1)%n)
    bad+= breaks > math.ceil(n/28)-1
print("replicates with excess breaks:", bad)
# 2) zero-denominator: fold sum>0 but sparse ref -> mid-run abort?
f=[([0.1]*56, [0.0]*55+[1.0])]
try: S(f,block_days=28,replicates=2000,seed=1); print("sparse ref: ok")
except ValueError as e: print("sparse ref: fail-closed mid-run ->", e)
# 3) numpy float64 input
try: S([(list(np.full(56,.1)), list(np.full(56,.2)))],block_days=28,replicates=3,seed=1); print("np.float64: accepted")
except ValueError as e: print("np.float64: rejected ->", e)
# 4) stratified vs naive concatenated CBB under fold heterogeneity (level shift between folds)
def naive(folds,block,reps,seed):
    m=sum((list(x) for x,_ in folds),[]); r=sum((list(y) for _,y in folds),[])
    return ref_impl([(m,r)],block,reps,seed)
het=[tuple([float(x) for x in rs.uniform(lo,lo+.1,60)] for lo in p) for p in ((0,.2),(.25,.2))]
for name,fn in (("stratified",lambda:S(het,block_days=28,replicates=2000,seed=9)),("naive concat",lambda:naive(het,28,2000,9))):
    v=np.array(fn()); print(name, "pt-ish mean %.4f  95%% CI %.4f..%.4f sd %.4f"%(v.mean(),*np.percentile(v,[2.5,97.5]),v.std()))
