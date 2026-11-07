import sys,os
import json,glob,os,re
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'attr.py')).read().split('summary=[]')[0])
res=[]
for f in sorted(glob.glob(sys.argv[1]+'/*.json')):
    out=[]; walk(json.load(open(f)),'',out)
    name=os.path.basename(f)[:-5]
    base=[r for r in out if re.search(r'(base|/x1)(/|$|\b)',r[0]) and not re.search(r'stress|/x2|/x3|tuning|grid/|per_symbol|development',r[0])]
    if not base: base=[r for r in out if not re.search(r'stress|/x2|/x3|tuning',r[0])]
    if not base: res.append((name,'-'));continue
    ng=sum(r[3]>0 for r in base); nn=sum(r[1]>0 for r in base)
    nt3=[r[4]+r[2] for r in base if r[4] is not None]
    cls='COST-LIMITED?' if ng==len(base) and nn<len(base) else ('NET+ALL' if nn==len(base) else 'gross<=0 somewhere')
    res.append((name,cls,len(base),ng,nn,round(sum(r[3] for r in base)),round(sum(r[1] for r in base)), min(nt3) if nt3 else None))
import collections
print(collections.Counter(r[1] for r in res))
for r in res:
    if r[1]!='gross<=0 somewhere': print(r)
