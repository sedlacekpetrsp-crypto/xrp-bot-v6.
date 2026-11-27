"""G1 ex-ante power arithmetic (no market data; n = 21 from census 0103335)."""
import math, json
def pmf(n,k,p): return math.comb(n,k)*p**k*(1-p)**(n-k)
def wilson_lo(k,n,z=1.959964):
    ph=k/n; d=1+z*z/n; c=ph+z*z/(2*n); r=z*math.sqrt(ph*(1-ph)/n+z*z/(4*n*n)); return (c-r)/d
def p_pass(n,p,thr,ci):
    return sum(pmf(n,k,p) for k in range(n+1) if (wilson_lo(k,n)>thr if ci else k/n>=thr))
out={}
for n in (21,14,10):
  out[n]={}
  for thr,name in ((0.5,'recall'),(0.6,'precision')):
    out[n][name]={f"{p:.1f}":{"point":round(p_pass(n,p,thr,False),3),"wilson_lo95":round(p_pass(n,p,thr,True),3)} for p in (0.3,0.4,0.5,0.6,0.7,0.8,0.9)}
  # minimum k for CI pass
  out[n]["min_k_recall_ci"]=min(k for k in range(n+1) if wilson_lo(k,n)>0.5)
  out[n]["min_k_precision_ci"]=min(k for k in range(n+1) if wilson_lo(k,n)>0.6)
print(json.dumps(out,indent=1))
