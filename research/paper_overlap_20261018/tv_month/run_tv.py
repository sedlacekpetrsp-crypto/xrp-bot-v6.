"""Offline replay using production TV signal/open/exit functions.
One-minute OHLC approximation; not an unseen holdout or live tick replay.
"""
import asyncio,bisect,contextlib,copy,functools,hashlib,io,json,math,pathlib,sys
from datetime import datetime,timezone
ROOT=pathlib.Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
import paper_stop_policy
paper_stop_policy.MULTIPLIER=1.15
import app_v8 as base
import tv_consensus_scalper as tv
HERE=pathlib.Path(__file__).parent
protocol=json.loads((HERE/'protocol.json').read_text())
ms=lambda s:int(datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()*1000)
raw=pathlib.Path(sys.argv[1]).read_bytes();manifest=json.loads((HERE/'data_manifest.json').read_text())
if hashlib.sha256(raw).hexdigest()!=manifest['sha256']:raise ValueError('Data hash mismatch')
bars=json.loads(raw)

def aggregate(rows,minutes):
    result=[];step=minutes*60000
    for i in range(0,len(rows),minutes):
        group=rows[i:i+minutes]
        if len(group)!=minutes:break
        r=group[0]
        if int(r[0])%step:raise ValueError('Aggregation misaligned')
        result.append([r[0],r[1],max(float(x[2]) for x in group),min(float(x[3]) for x in group),
                       group[-1][4],sum(float(x[5]) for x in group),int(r[0])+step-1])
    return result
hour_bars=aggregate(bars,60)
hour_ends=[int(r[6]) for r in hour_bars]

def hourly_aligned(now,side):
    n=bisect.bisect_left(hour_ends,now)
    closes=[float(r[4]) for r in hour_bars[max(0,n-250):n]]
    if len(closes)<50:return False
    e20,e50=base.ema(closes,20),base.ema(closes,50)
    return closes[-1]>e20>e50 if side=='LONG' else closes[-1]<e20<e50

frames={'1m':bars,'5m':aggregate(bars,5),'15m':aggregate(bars,15)}
ends={k:[int(r[6]) for r in v] for k,v in frames.items()}
clock=[0];quote=[0.]
async def klines(symbol,interval,limit=250):
    count=bisect.bisect_left(ends[interval],clock[0])
    rows=frames[interval][max(0,count-limit+1):count]
    live=frames[interval][count]
    o=live[1]
    return rows+[[live[0],o,o,o,o,0,live[6]]]
async def live(*a,**k):return quote[0]
base.get_klines=klines;base.get_live_price=live
base.FEE_RATE=protocol['fee_per_side'];base.SLIPPAGE_RATE=protocol['slippage_per_side']
tv.base=base;tv.DATABASE_URL=None;tv.save_state=lambda:None;tv.save_trade=lambda t:None;tv.heartbeat_state=lambda *a,**k:None
tv.utcnow=lambda:datetime.fromtimestamp(clock[0]/1000,timezone.utc)
tv.RISK_PER_TRADE=protocol['risk_rate']
tv.portfolio_risk_allowance=lambda name,symbol,side,risk:(min(risk,tv.state['balance']*.0008),{})
tv.portfolio_entry_allowed=lambda *a:(True,'offline isolated replay')
# Reuse slow-frame computations across repeated 1m samples, with bounded caches.
for name in ('ema','rsi_wilder','atr_wilder','adx_wilder','macd_hist'):
    original=getattr(base,name)
    cached=functools.lru_cache(maxsize=512)(original)
    def wrapper(*args,_cached=cached):return _cached(*(tuple(x) if isinstance(x,list) else x for x in args))
    setattr(base,name,wrapper)

async def analyses():
    fingerprint=hashlib.sha256(raw+pathlib.Path(tv.__file__).read_bytes()+pathlib.Path(__file__).read_bytes()).hexdigest()[:16]
    cache=HERE/f'signals-{fingerprint}.json.gz'
    import gzip
    if cache.exists():return json.loads(gzip.decompress(cache.read_bytes()))
    rows=[];tv.state.update(previous_long_score=None,previous_short_score=None)
    start=ms(protocol['development'][0]);end=ms(protocol['chronological_check'][1])
    for i,r in enumerate(bars):
        now=int(r[0])
        if now<start or now>=end:continue
        clock[0]=now;quote[0]=float(r[1]);a=await tv.analyze_market()
        rows.append(a)
        if len(rows)%10000==0:print('Signals',len(rows),flush=True)
    cache.write_bytes(gzip.compress(json.dumps(rows,separators=(',',':')).encode()))
    return rows

async def replay(signals,start,end,adx,mult,slip,hour_filter=False):
    tv.MIN_ADX=adx;tv.ATR_STOP_MULT=mult;base.SLIPPAGE_RATE=slip
    tv.state.update(balance=10000.,equity=10000.,open_position=None,trades=[],last_entry_candle=None,
                    cooldown_until=None,status='running',previous_long_score=None,previous_short_score=None)
    trades=[];original_close=tv.close_trade
    def close(price,reason):
        original_close(price,reason);trades.append(copy.deepcopy(tv.state['trades'][-1]))
    tv.close_trade=close
    peak=10000.;dd=0.;index={int(r[0]):r for r in bars}
    for a0 in signals:
        now=int(a0['candle_time'])+60000
        if now<start or now>=end:continue
        bar=index[now];clock[0]=now;quote[0]=float(bar[1]);a=copy.deepcopy(a0)
        candidates=[s for s in ('LONG','SHORT') if not tv.entry_blockers(a,s) and (not hour_filter or hourly_aligned(now,s))]
        a['signal']=candidates[0] if len(candidates)==1 else 'WAIT'
        if a['signal']!='WAIT':
            s=a['signal'];a.update(score=a['long_score'] if s=='LONG' else a['short_score'],
                opposing_score=a['short_score'] if s=='LONG' else a['long_score'],
                score_accel=a['long_accel'] if s=='LONG' else a['short_accel'],setup='CONSENSUS_IMPULSE',countertrend=False)
        had=bool(tv.state['open_position'])
        if not had and not tv.cooldown_active() and not tv.loss_streak_pause_active() and a['signal']!='WAIT':
            tv.open_trade(a,quote[0])
        p=tv.state['open_position']
        if p:
            o,h,l,c=map(float,bar[1:5]);long=p['side']=='LONG'
            stop, tp=float(p['stop']),float(p['tp'])
            if (o<=stop if long else o>=stop):tv.close_trade(o,'GAP STOP')
            elif (l<=stop if long else h>=stop):tv.close_trade(stop,'TV PROFIT PROTECT' if p.get('profit_protected') else 'TV STOP')
            elif (h>=tp if long else l<=tp):tv.close_trade(tp,'TV TAKE PROFIT')
            else:
                # Only the close updates protection for the next bar. Entry-bar
                # analysis exits are deferred; the live cycle also returns on entry.
                quote[0]=c
                await tv.manage_position(a if had else None)
        peak=max(peak,tv.state['balance']);dd=max(dd,peak-tv.state['balance'])
    if tv.state['open_position']:
        last=index[end-60000];clock[0]=end;tv.close_trade(float(last[4]),'WINDOW END')
    peak=max(peak,tv.state['balance']);dd=max(dd,peak-tv.state['balance'])
    tv.close_trade=original_close
    net=tv.state['balance']-10000;gp=sum(max(t['net_pnl'],0) for t in trades);gl=-sum(min(t['net_pnl'],0) for t in trades)
    return {'net_pnl':net,'trades':len(trades),'profit_factor':gp/gl if gl else None,'max_drawdown':dd,
            'fees':sum(t['fees'] for t in trades),'wins':sum(t['net_pnl']>0 for t in trades),
            'window_end_closes':sum(t['reason']=='WINDOW END' for t in trades)},trades

async def main():
    signals=await analyses();results=[];all_trades={}
    for candidate in (False, True):
        row={'variant':'closed_1h_alignment' if candidate else 'production_baseline'}
        for period in ('development','chronological_check'):
            start,end=map(ms,protocol[period])
            with contextlib.redirect_stdout(io.StringIO()):r,tr=await replay(signals,start,end,22,1.5,protocol['slippage_per_side'],candidate)
            row[period]=r;all_trades[f"{row['variant']}-{period}"]=tr
        start,end=map(ms,protocol['chronological_check'])
        with contextlib.redirect_stdout(io.StringIO()):row['double_slippage'],_=await replay(signals,start,end,22,1.5,protocol['slippage_per_side']*2,candidate)
        c=row['chronological_check'];d=row['double_slippage']
        row['passes_numeric_gate']=c['net_pnl']>0 and c['trades']>=30 and (c['profit_factor'] or 0)>=1.1 and d['net_pnl']>0
        results.append(row);print(json.dumps(row),flush=True)
    (HERE/'tv_results.json').write_text(json.dumps(results,indent=2))
    import gzip
    (HERE/'tv_trades.json.gz').write_bytes(gzip.compress(json.dumps(all_trades,separators=(',',':')).encode(),mtime=0))
if __name__=='__main__':asyncio.run(main())
