"""Offline retrospective replay; no orders, database access or live strategy promotion."""
import asyncio,bisect,contextlib,copy,gzip,hashlib,io,json,math,pathlib,sys
from datetime import datetime,timezone
from types import SimpleNamespace
HERE=pathlib.Path(__file__).parent.resolve();ROOT=HERE.parents[1];sys.path.insert(0,str(ROOT))
import app_blue_whale_mirror as w
protocol=json.loads((HERE/'protocol.json').read_text());symbols=protocol['symbols']
ms=lambda s:int(datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()*1000)
clock=[0];data={};frames={};ends={}

def aggregate(rows,minutes):
 result=[]
 for i in range(0,len(rows),minutes):
  group=rows[i:i+minutes]
  if len(group)!=minutes:break
  if int(group[0][0])%(minutes*60000):raise ValueError('Misaligned aggregate')
  result.append([group[0][0],group[0][1],max(float(x[2]) for x in group),min(float(x[3]) for x in group),group[-1][4],sum(float(x[5]) for x in group),int(group[0][0])+minutes*60000-1])
 return result
manifest=json.loads((HERE/'data_manifest.json').read_text())
for m in manifest:
 raw=(pathlib.Path(sys.argv[1])/f"{m['symbol']}_1m.json").read_bytes()
 if hashlib.sha256(raw).hexdigest()!=m['sha256']:raise ValueError('Data hash mismatch')
 rows=json.loads(raw);s=m['symbol'];data[s]=rows
 frames[s]={'1m':rows,'5m':aggregate(rows,5),'15m':aggregate(rows,15),'1h':aggregate(rows,60)}
 ends[s]={k:[int(r[6]) for r in v] for k,v in frames[s].items()}

def closed_rows(symbol,interval,limit=120):
 count=bisect.bisect_left(ends[symbol][interval],clock[0])
 return frames[symbol][interval][max(0,count-limit):count]
async def market_get(client,url,params,**kwargs):
 # Historical confirmation receives closed-only bars, which production accepts.
 return SimpleNamespace(json=lambda:closed_rows(params['symbol'],params['interval'],params.get('limit',120)))
async def no_news(*a,**k):return {}
w.market_get=market_get;w.news_signal.get_news=no_news;w.news_signal.blocks_entry=lambda *a:False
w.utcnow=lambda:datetime.fromtimestamp(clock[0]/1000,timezone.utc)
w.time=SimpleNamespace(time=lambda:clock[0]/1000)
w.DATABASE_URL=None;w.save_state=lambda:None;w.save_trade=lambda t:None
w.PAUSED_STRATEGIES=frozenset() # Isolated replay only; production file remains paused.
w.WHALE_TECH_CONFIRM=True;w.WHALE_CONFIRM_MIN_SCORE=4
w.FEE_RATE=protocol['fee_per_side'];w.SLIPPAGE_RATE=protocol['slippage_per_side']
w.MAX_OPEN_POSITIONS=protocol['max_positions']
w.portfolio_entry_allowed=lambda *a:(True,'isolated replay')
w.portfolio_risk_allowance=lambda name,symbol,side,risk:(min(risk,min(protocol['shared_reference_balance'],w.state['balance'])*protocol['portfolio_risk_share']),{})

async def signals():
 cache=HERE/'signals.json.gz'
 if cache.exists():return json.loads(gzip.decompress(cache.read_bytes()))
 start,end=ms(protocol['development'][0]),ms(protocol['check'][1]);all_signals={};technical={}
 for i in range(len(data[symbols[0]])):
  now=int(data[symbols[0]][i][0])
  if now<start or now>=end:continue
  clock[0]=now
  for s in symbols:
   candidate,diag=w.vwap_candidate(closed_rows(s,'1m'),closed_rows(s,'5m'))
   if not candidate or candidate['strategy']!='VWAP_REVERSION':continue
   cachekey=(s,now//300000,candidate['side'])
   if cachekey not in technical:technical[cachekey]=await w.technical_confirmation(None,s,candidate['side'])
   ok,tech=technical[cachekey]
   if not ok:continue
   all_signals.setdefault(str(now),[]).append({'symbol':s,'candidate':candidate,'technical':tech,
                                              'review':w.reversion_review(candidate,tech)})
  if (now-start)//60000%10000==0:print('Signals minute',(now-start)//60000,'candidates',sum(map(len,all_signals.values())),flush=True)
 cache.write_bytes(gzip.compress(json.dumps(all_signals,separators=(',',':')).encode()))
 return all_signals

def passes(item,variant):
 if variant=='baseline':return True
 review=item['review']
 if not review['rsi_available'] or review['extreme_rsi_would_block']:return False
 return variant=='rsi_extremes' or review['continuation_5m']

def replay(signals,start,end,variant,slip):
 w.SLIPPAGE_RATE=slip
 w.state.update(balance=10000.,equity=10000.,open_positions=[],open_position=None,trades=[],seen_signal_ids=[],
                market_prices={},persistence='postgres',persistence_error=None,last_signal=None)
 trades=[];original_close=w.close_paper
 def close(p,price,reason,mark_price=None):
  original_close(p,price,reason,mark_price);trades.append(copy.deepcopy(w.state['trades'][-1]))
 w.close_paper=close
 indices={s:{int(r[0]):r for r in data[s]} for s in symbols}
 peak=10000.;dd=0.;rejected={};candidate_count=0
 for now in range(start,end,60000):
  clock[0]=now;bars={s:indices[s][now] for s in symbols}
  for s,bar in bars.items():w.state['market_prices'][s]=float(bar[1])
  for p in list(w.state['open_positions']):
   o=float(bars[p['symbol']][1]);long=p['side']=='LONG'
   if o<=p['stop'] if long else o>=p['stop']:w.close_paper(p,o,'GAP STOP',o)
  for item in signals.get(str(now),[]):
   candidate_count+=1
   if not passes(item,variant):rejected['hypothesis']=rejected.get('hypothesis',0)+1;continue
   s=item['symbol'];candidate=copy.deepcopy(item['candidate'])
   sid=int.from_bytes(hashlib.sha256((s+candidate['key']).encode()).digest()[:8],'big')&((1<<63)-1)
   if sid in w.state['seen_signal_ids'] or any(p['symbol']==s for p in w.state['open_positions']):continue
   stop=candidate['stop'];candidate.update(symbol=s,id=sid,text=candidate['side'],stop={'low':stop,'high':stop,'raw':str(stop),'masked':False})
   if not w.open_paper(candidate,candidate['side'],float(bars[s][1])):
    reason=(w.state.get('last_signal') or {}).get('rejected','other');rejected[reason]=rejected.get(reason,0)+1
  for p in list(w.state['open_positions']):
   o,h,l,c=map(float,bars[p['symbol']][1:5]);long=p['side']=='LONG'
   if l<=p['stop'] if long else h>=p['stop']:w.close_paper(p,p['stop'],'SL',c);continue
   if h>=p['tp'] if long else l<=p['tp']:w.close_paper(p,p['tp'],'TP',c);continue
   if w.age_hours(p)>=w.MAX_HOLD_HOURS:w.close_paper(p,c,'TIME',c);continue
   one_r=abs(p['entry']-p['initial_stop']);favorable=c-p['entry'] if long else p['entry']-c
   if one_r>0 and favorable>=w.WHALE_BREAKEVEN_R*one_r:
    be=p['entry']*(1+w.FEE_RATE)/((1-w.FEE_RATE)*(1-w.SLIPPAGE_RATE)) if long else p['entry']*(1-w.FEE_RATE)/((1+w.FEE_RATE)*(1+w.SLIPPAGE_RATE))
    if c>be if long else c<be:p['stop']=max(p['stop'],be) if long else min(p['stop'],be);p['breakeven']=True
  for s,bar in bars.items():w.state['market_prices'][s]=float(bar[4])
  w.mark_to_market();equity=w.state['equity'];peak=max(peak,equity);dd=max(dd,peak-equity)
 for p in list(w.state['open_positions']):w.close_paper(p,float(indices[p['symbol']][end-60000][4]),'WINDOW END')
 peak=max(peak,w.state['balance']);dd=max(dd,peak-w.state['balance']);w.close_paper=original_close
 gp=sum(max(t['net_pnl'],0) for t in trades);gl=-sum(min(t['net_pnl'],0) for t in trades)
 pnl={s:sum(t['net_pnl'] for t in trades if t['symbol']==s) for s in symbols}
 return {'net_pnl':w.state['balance']-10000,'trades':len(trades),'profit_factor':gp/gl if gl else None,'max_drawdown':dd,
         'fees':sum(t['entry_fee']+t['exit_fee'] for t in trades),'wins':sum(t['net_pnl']>0 for t in trades),
         'by_symbol':pnl,'candidate_count':candidate_count,'rejections':rejected,'window_end_closes':sum(t['reason']=='WINDOW END' for t in trades)},trades

async def main():
 sig=await signals();results=[];all_trades={}
 for variant in protocol['variants']:
  row={'variant':variant}
  for period in ('development','check'):
   start,end=map(ms,protocol[period])
   with contextlib.redirect_stdout(io.StringIO()):r,tr=replay(sig,start,end,variant,protocol['slippage_per_side'])
   row[period]=r;all_trades[variant+'-'+period]=tr
  with contextlib.redirect_stdout(io.StringIO()):row['double_slippage'],_=replay(sig,*map(ms,protocol['check']),variant,protocol['slippage_per_side']*2)
  check=row['check'];stress=row['double_slippage']
  row['passes_numeric_gate']=check['net_pnl']>0 and check['trades']>=30 and (check['profit_factor'] or 0)>=1.1 and stress['net_pnl']>0 and all(v>0 for v in check['by_symbol'].values())
  results.append(row);print(json.dumps(row),flush=True)
 (HERE/'results.json').write_text(json.dumps(results,indent=2))
 (HERE/'trades.json.gz').write_bytes(gzip.compress(json.dumps(all_trades,separators=(',',':')).encode()))
asyncio.run(main())
