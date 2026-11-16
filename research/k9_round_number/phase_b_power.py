"""K9 dodatek 2: pocty neprekryvajicich se obchodu a synteticka sila fáze B jen z CASU udalosti faze A (bez vynosu)."""
import pandas as pd, numpy as np, json
from scipy.stats import norm
d=pd.read_csv('research/k9_round_number/phaseA_events.csv.gz',parse_dates=['time'])
d['period']=np.where(d.time<'2024-01-01','dev','final')
out={}
for H in (15,60):
  for (per,kind),g in d.groupby(['period','kind']):
    keep=[]
    for a,ga in g.sort_values('time').groupby('asset'):
      busy=None
      for t in ga.time:
        if busy is None or t>=busy:  # entry open t+1, exit close t+H -> busy until t+H+1
          keep.append((a,t)); busy=t+pd.Timedelta(minutes=H+1)
    k=pd.DataFrame(keep,columns=['asset','time']); m=k.groupby(k.time.dt.date).size()
    n=len(k); meff=(m**2).sum()/n
    row={'n_trades':n,'days':len(m),'m_eff':round(meff,2)}
    for mu in (0.0014,0.0028):
      for s in (0.004,0.008) if H==15 else (0.008,0.016):
        for rho in (0.0,0.3):
          se=s/np.sqrt(n)*np.sqrt(1+(meff-1)*rho)
          row[f'pw_mu{mu}_sd{s}_rho{rho}']=round(float(norm.cdf(mu/se-1.96)),3)
    out[f'H{H}_{per}_{kind}']=row
print(json.dumps(out,indent=1))
json.dump(out,open('research/k9_round_number/phaseB_power_table.json','w'),indent=1)
