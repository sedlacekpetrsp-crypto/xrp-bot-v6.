"""Isolated FIB timeframe screening. Never touches deployment or persisted accounts."""
import asyncio,bisect,copy,gzip,hashlib,json,pathlib,sys
from collections import Counter
from datetime import datetime,timezone
from types import SimpleNamespace
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT))
import app_blue_whale_mirror as w
P=json.loads((HERE/'protocol.json').read_text())
def ms(s):return int(datetime.fromisoformat(s).timestamp()*1000)
def aggregate(rows,n):
 out=[]
 for i in range(0,len(rows),n):
  g=rows[i:i+n]
  if len(g)<n:break
  if g[0][0]%(n*300000) or any(b[0]-a[0]!=300000 for a,b in zip(g,g[1:])):raise ValueError('Misaligned/gapped bars')
  out.append([g[0][0],g[0][1],max(r[2] for r in g),min(r[3] for r in g),g[-1][4],sum(r[5] for r in g),g[-1][6]])
 return out
def closed(rows,ends,now,limit=120):
 end=bisect.bisect_left(ends,now)
 return rows[max(0,end-limit):end]
class Replay:
 def __init__(self,root):
  manifest=json.loads((HERE/'datasets.json').read_text())
  self.data={}
  for s in P['symbols']:
   raw=(root/(s+'.json')).read_bytes()
   if hashlib.sha256(raw).hexdigest()!=manifest[s]['sha256']:raise ValueError('Dataset hash mismatch '+s)
   self.data[s]=json.loads(raw)
  self.frames={s:{'5m':r,'15m':aggregate(r,3),'1h':aggregate(r,12)} for s,r in self.data.items()}
  self.ends={s:{k:[r[6] for r in rows] for k,rows in f.items()} for s,f in self.frames.items()}
  self.clock=0
  w.market_get=self.market_get;w.news_signal.get_news=self.no_news;w.news_signal.blocks_entry=lambda *a:False
  w.time=SimpleNamespace(time=lambda:self.clock/1000)
  w.utcnow=lambda:datetime.fromtimestamp(self.clock/1000,timezone.utc)
  w.save_state=lambda:None;w.save_trade=lambda *a:None;w.DATABASE_URL=None
  w.WHALE_CONFIRM_MIN_SCORE=P['confirmation_score'];w.WHALE_TECH_CONFIRM=True
  w.FEE_RATE=P['fee_per_side'];w.SLIPPAGE_RATE=P['slippage_per_side'];w.paper_stop_policy.MULTIPLIER=P['stop_multiplier']
  w.portfolio_entry_allowed=lambda *a:(True,'isolated FIB screening')
  w.portfolio_risk_allowance=lambda name,symbol,side,risk:(min(risk,P['shared_reference_balance']*P['risk_share']),{'risk_cap_usdc':min(risk,P['shared_reference_balance']*P['risk_share'])})
 def rows(self,s,frame,limit=120):return closed(self.frames[s][frame],self.ends[s][frame],self.clock,limit)
 async def no_news(self,*a):return {}
 async def market_get(self,client,url,params,**kwargs):
  return SimpleNamespace(json=lambda:self.rows(params['symbol'],params['interval'],params.get('limit',120)))
 async def signals(self,frame):
  signals={};counts=Counter();technical={}
  for i,bar in enumerate(self.data[P['symbols'][0]]):
   now=bar[0]
   if not ms(P['development'][0])<=now<ms(P['holdout'][1]):continue
   # At each 5m open, the most recent fully closed 15m candidate may be retried.
   self.clock=now
   for s in P['symbols']:
    candidate,diag=w.fib_candidate(self.rows(s,frame));counts[diag['reason']]+=1
    if not candidate:continue
    counts['raw_candidate']+=1
    key=(s,now,candidate['side'])
    if key not in technical:technical[key]=await w.technical_confirmation(None,s,candidate['side'])
    ok,tech=technical[key]
    if not ok:counts['MTF_veto' if tech.get('hard_veto') else 'MTF_score']+=1;continue
    signals.setdefault(now,[]).append(dict(symbol=s,candidate=candidate))
   if i%10000==0:print('signal progress',frame,i,flush=True)
  return signals,dict(counts)
 def run(self,signals,start,end,slip):
  w.SLIPPAGE_RATE=slip
  w.state.update(balance=10000.,equity=10000.,open_positions=[],open_position=None,trades=[],seen_signal_ids=[],market_prices={},last_signal=None)
  trades=[];rejects=Counter();peak=10000.;drawdown=0.
  def close_trade(p,price,reason,mark=None):
   w.close_paper(p,price,reason,mark);trades.append(copy.deepcopy(w.state['trades'][-1]))
  timeline=self.data[P['symbols'][0]]
  for i,bar in enumerate(timeline):
   now=bar[0]
   if not start<=now<end:continue
   self.clock=now;bars={s:self.data[s][i] for s in P['symbols']}
   for s,r in bars.items():w.state['market_prices'][s]=r[1]
   for p in list(w.state['open_positions']):
    o=bars[p['symbol']][1]
    if (o<=p['stop'] if p['side']=='LONG' else o>=p['stop']):close_trade(p,o,'GAP_SL',o)
   for item in signals.get(now,[]):
    c=copy.deepcopy(item['candidate']);s=item['symbol']
    sid=int.from_bytes(hashlib.sha256((s+c['key']).encode()).digest()[:8],'big')&((1<<63)-1)
    if sid in w.state['seen_signal_ids']:rejects['already_traded']+=1;continue
    stop=c['stop'];c.update(id=sid,symbol=s,text=c['side'],stop=dict(low=stop,high=stop,raw=str(stop),masked=False))
    if not w.open_paper(c,c['side'],bars[s][1]):rejects[(w.state.get('last_signal') or {}).get('rejected','other')]+=1
   for p in list(w.state['open_positions']):
    o,h,l,c=bars[p['symbol']][1:5];long=p['side']=='LONG'
    # Adverse ordering if the intrabar path is unknowable.
    if (l<=p['stop'] if long else h>=p['stop']):close_trade(p,p['stop'],'SL',c);continue
    if (h>=p['tp'] if long else l<=p['tp']):close_trade(p,p['tp'],'TP',c);continue
    if w.age_hours(p)>=w.MAX_HOLD_HOURS:close_trade(p,c,'TIME',c);continue
    one_r=abs(p['entry']-p['initial_stop']);favorable=(c-p['entry']) if long else (p['entry']-c)
    if one_r>0 and favorable>=w.WHALE_BREAKEVEN_R*one_r:
     be=p['entry']*(1+w.FEE_RATE)/((1-w.FEE_RATE)*(1-slip)) if long else p['entry']*(1-w.FEE_RATE)/((1+w.FEE_RATE)*(1+slip))
     if (c>be if long else c<be):p['stop']=max(p['stop'],be) if long else min(p['stop'],be);p['breakeven']=True
   for s,r in bars.items():w.state['market_prices'][s]=r[4]
   w.mark_to_market();peak=max(peak,w.state['equity']);drawdown=max(drawdown,peak-w.state['equity'])
  for p in list(w.state['open_positions']):close_trade(p,w.state['market_prices'][p['symbol']],'WINDOW_END')
  gains=sum(max(t['net_pnl'],0) for t in trades);losses=-sum(min(t['net_pnl'],0) for t in trades)
  result=dict(trades=len(trades),net_pnl=w.state['balance']-10000,fees=sum(t['entry_fee']+t['exit_fee'] for t in trades),profit_factor=gains/losses if losses else None,wins=sum(t['net_pnl']>0 for t in trades),max_drawdown=drawdown,by_symbol={s:dict(trades=sum(t['symbol']==s for t in trades),net_pnl=sum(t['net_pnl'] for t in trades if t['symbol']==s)) for s in P['symbols']},rejections=dict(rejects),window_end_closes=sum(t['reason']=='WINDOW_END' for t in trades))
  return result,trades
async def main(root):
 r=Replay(root);results={};all_trades={}
 for name,frame in P['variants'].items():
  w.SLIPPAGE_RATE=P['slippage_per_side']
  sig,diag=await r.signals(frame);row={'diagnostics':diag}
  for period in ('development','holdout'):
   row[period],all_trades[name+'_'+period]=r.run(sig,*map(ms,P[period]),P['slippage_per_side'])
  row['stress'],all_trades[name+'_stress']=r.run(sig,*map(ms,P['holdout']),P['stress_slippage_per_side'])
  results[name]=row;print(name,json.dumps(row),flush=True)
 base=results['baseline_5m'];candidate=results['candidate_15m'];c=candidate['holdout']
 results['screening_passed']=candidate['development']['net_pnl']>0 and c['net_pnl']>0 and c['trades']>=30 and (c['profit_factor'] or 0)>=1.1 and c['trades']>base['holdout']['trades'] and candidate['stress']['net_pnl']>0
 (HERE/'results.json').write_text(json.dumps(results,indent=2));(HERE/'trades.json.gz').write_bytes(gzip.compress(json.dumps(all_trades,separators=(',',':')).encode()))
 print('SCREENING_PASSED',results['screening_passed'],flush=True)
if __name__=='__main__':asyncio.run(main(pathlib.Path(sys.argv[1])))
