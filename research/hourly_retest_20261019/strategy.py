"""Hourly retest signals mapped causally to 15m execution bars. Offline only."""
from research.candle_validation_20261019.engine import signals
STEP=900000

def hourly_rows(rows):
 out=[];ends=[]
 for i in range(0,len(rows),4):
  bars=rows[i:i+4]
  if len(bars)!=4:break
  if int(bars[0][0])%3600000 or any(int(r[0])!=int(bars[0][0])+j*STEP or int(r[6])!=int(r[0])+STEP-1 for j,r in enumerate(bars)):
   raise ValueError('Require contiguous hour-aligned 15m input')
  out.append([bars[0][0],bars[0][1],max(float(r[2]) for r in bars),min(float(r[3]) for r in bars),bars[-1][4],sum(float(r[5]) for r in bars),bars[-1][6]])
  ends.append(i+3)
 return out,ends

def hourly_signals(rows,p):
 hours,ends=hourly_rows(rows);sig,atr=signals(hours,'breakout_retest',p)
 mapped=[0]*len(rows);vol=[0.]*len(rows)
 for j,i in enumerate(ends):mapped[i]=sig[j];vol[i]=atr[j]
 return mapped,vol
