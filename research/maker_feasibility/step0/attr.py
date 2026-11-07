import json,glob,os,sys
rows=[]
def num(x):
    return x if isinstance(x,(int,float)) and not isinstance(x,bool) else None
def walk(o,path,out):
    if isinstance(o,dict):
        n=num(o.get('net_pnl'))
        if n is not None:
            fees=num(o.get('fees')) ; sl=num(o.get('slippage_cost')); co=num(o.get('costs'))
            cost=None
            if co is not None: cost=co
            elif fees is not None: cost=fees+(sl or 0)
            g=num(o.get('gross_before_fees_and_slippage'))
            if cost is not None or g is not None:
                gross = g if g is not None else n+cost
                if cost is None: cost=gross-n
                out.append((path,n,cost,gross,num(o.get('net_without_top3')),num(o.get('trades'))))
        for k,v in o.items(): walk(v,path+'/'+str(k),out)
    elif isinstance(o,list):
        for i,x in enumerate(o): walk(x,path+f'[{i}]',out)
summary=[]
for f in sorted(glob.glob(sys.argv[1]+'/*.json')):
    out=[]; walk(json.load(open(f)),'',out)
    name=os.path.basename(f)[:-5]
    if not out: summary.append((name,'NO_COST_FIELDS',0,0,0,''));continue
    neg=[r for r in out if r[1]<=0]
    costlim=[r for r in neg if r[3]>0]
    # robust cost-limited: gross>0 and gross-of-without-top3 >0 too
    robust=[r for r in costlim if r[4] is None or (r[4]+r[2])>0]
    ex=robust[0] if robust else (costlim[0] if costlim else '')
    summary.append((name,'ok',len(out),len(neg),len(costlim),len(robust),ex))
for s in summary: print(s if s[1]!='ok' else f"{s[0]:55s} blocks={s[2]:3d} neg={s[3]:3d} costlim={s[4]:3d} robust={s[5]:3d} {('%s n=%.0f c=%.0f g=%.0f nt3=%s'%(s[6][0][-60:],s[6][1],s[6][2],s[6][3],s[6][4])) if s[6] else ''}")
