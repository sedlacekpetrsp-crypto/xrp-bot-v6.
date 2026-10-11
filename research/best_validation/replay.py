"""Offline, isolated replay of original BEST sleeve. See protocol.json for limits."""
import argparse, bisect, contextlib, copy, hashlib, io, json, math, sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import bestof_bot as best
c=best.core
STEP=300000
VARIANTS=('baseline','hourly_filter','fib_structural_stop','no_xrp_breakout')

def stamp(s):return int(datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp()*1000)
def iso(ms):return datetime.fromtimestamp(ms/1000,timezone.utc).isoformat()
def validate(rows):
    for i,r in enumerate(rows):
        o,h,l,cl,v=map(float,r[1:6]);t=int(r[0])
        if t%STEP or int(r[6])!=t+STEP-1:raise ValueError('invalid timestamp')
        if i and t-int(rows[i-1][0])!=STEP:raise ValueError('gap or duplicate')
        if not all(math.isfinite(x) for x in (o,h,l,cl,v)) or not 0<l<=min(o,cl)<=max(o,cl)<=h or v<0:raise ValueError('invalid OHLCV')

def aggregate(rows,n):
    out=[]
    for i in range(0,len(rows)-n+1,n):
        part=rows[i:i+n]
        if int(part[0][0])%(STEP*n):raise ValueError('unaligned aggregate')
        out.append([part[0][0],part[0][1],max(r[2] for r in part),min(r[3] for r in part),part[-1][4],sum(r[5] for r in part),part[-1][6]])
    return out

def prepare(data):
    signals={}
    for sym,rows in data.items():
        frames={3:aggregate(rows,3),12:aggregate(rows,12)};out={};cache={}
        for i in range(1200,len(rows)):
            closed=rows[max(0,i-99):i]
            a=best.detect_bestof(closed);side=a.get('signal')
            if (sym,a.get('setup'),side) not in best.ALLOWED:continue
            j=i//3
            key=(3,j,side)
            if key not in cache:cache[key]=c.trend_filter(frames[3][max(0,j-99):j],side)
            ok,_,meta=cache[key]
            if not ok:continue
            a.update(meta);a['symbol']=sym
            j=i//12;key=(12,j,side)
            if key not in cache:cache[key]=c.trend_filter(frames[12][max(0,j-99):j],side)
            a['hourly_ok']=cache[key][0]
            if a['setup']=='FIB_0618_0786':
                fib=best.fib_pullback([r[2] for r in closed],[r[3] for r in closed],[r[4] for r in closed],[r[5] for r in closed],lookback=24,min_impulse_pct=.006,min_volume_ratio=.85)
                a['swing_low']=fib['swing_low'];a['swing_high']=fib['swing_high']
            assert int(closed[-1][6])<int(rows[i][0])
            out[i]=a
        signals[sym]=out
        print('prepared',sym,len(out),flush=True)
    return signals

def reset():
    c.PAPER_BALANCE=10000.;c.positions={};c.trade_history=[];c.cooldown_until={};c.last_entry_candle={}
    c.save_state=lambda:None

def bar_exit(p,row):
    """Old protective orders first. Adverse gap at open; ambiguity -> stop."""
    o,h,l=row[1:4];side=p['side'];stop=p['stop_loss'];target=p['take_profit']
    islong=side=='LONG'
    if (o<=stop if islong else o>=stop):return o,'BREAK EVEN' if p['breakeven_moved'] else 'STOP LOSS'
    if (o>=target if islong else o<=target):return target,'TAKE PROFIT'
    if (l<=stop if islong else h>=stop):return stop,'BREAK EVEN' if p['breakeven_moved'] else 'STOP LOSS'
    if (h>=target if islong else l<=target):return target,'TAKE PROFIT'
    return None

def simulate(data,signals,variant,start,end,slip=.0002):
    reset();c.SLIPPAGE_RATE=slip
    rows0=next(iter(data.values()));times=[int(r[0]) for r in rows0]
    first=bisect.bisect_left(times,stamp(start));last=bisect.bisect_left(times,stamp(end))
    records=[];c.save_trade=lambda t:records.append(copy.deepcopy(t));counts=Counter();peak=10000.;dd=0.;monthly={}
    def now(ms):c.utcnow=lambda:datetime.fromtimestamp(ms/1000,timezone.utc)
    with contextlib.redirect_stdout(io.StringIO()):
        for i in range(first,last):
            ms=times[i];now(ms)
            # Execute at open before any knowledge of this candle's high/low/close.
            for sym in c.SYMBOLS:
                a=signals.get(sym,{}).get(i)
                if not a:continue
                counts['candidates']+=1
                if variant=='hourly_filter' and not a['hourly_ok']:counts['hourly_reject']+=1;continue
                if variant=='no_xrp_breakout' and sym=='XRPUSDT' and a['setup']=='BREAKOUT':counts['xrp_reject']+=1;continue
                if sym in c.positions or c.cooldown_active(sym) or c.last_entry_candle.get(sym)==a['candle_time']:continue
                a=copy.deepcopy(a)
                if variant=='fib_structural_stop' and a['setup']=='FIB_0618_0786':a['signal_low']=a['swing_low'];a['signal_high']=a['swing_high']
                if c.open_trade(sym,a,data[sym][i][1]):counts['opened']+=1
            assert len(c.positions)<=2
            # No entries can use capital or slots freed later in this candle.
            for sym,p in list(c.positions.items()):
                row=data[sym][i];ex=bar_exit(p,row);now(ms+STEP)
                if ex:c.close_trade(sym,*ex);continue
                net=c.estimated_net_per_unit(p['side'],p['entry_price'],row[4])*p['qty']
                if not p['breakeven_moved'] and net>=p['risk_usdt']*c.BREAKEVEN_TRIGGER_R:
                    p['stop_loss']=c.target_market_for_net_profit(p['side'],p['entry_price'],0.)
                    p['breakeven_moved']=True
            equity=c.PAPER_BALANCE+sum(c.estimated_net_per_unit(p['side'],p['entry_price'],data[sym][i][4])*p['qty'] for sym,p in c.positions.items())
            peak=max(peak,equity);dd=max(dd,100*(peak-equity)/peak)
            monthly[iso(ms)[:7]]=equity-10000.
        forced=len(c.positions)
        now(times[last-1]+STEP)
        for sym in list(c.positions):c.close_trade(sym,data[sym][last-1][4],'END_OF_WINDOW')
    net=sum(t['pnl'] for t in records)
    assert abs(c.PAPER_BALANCE-10000-net)<1e-7
    assert all(abs(t['gross_pnl']-t['fees']-t['slippage']-t['pnl'])<1e-7 for t in records)
    profits=sum(max(t['pnl'],0) for t in records);loss=-sum(min(t['pnl'],0) for t in records)
    return dict(variant=variant,start=start,end_exclusive=end,slippage_per_side=slip,trades=len(records),forced_exits=forced,net=net,return_pct=net/100,pf=profits/loss if loss else None,win_rate=100*sum(t['pnl']>0 for t in records)/len(records) if records else None,drawdown_pct=dd,fees=sum(t['fees'] for t in records),slippage=sum(t['slippage'] for t in records),counts=dict(counts),month_end_cumulative=monthly),records

def run(folder,out):
    data={};manifest=[]
    for sym in c.SYMBOLS:
        p=folder/(sym+'_5m.json');raw=p.read_bytes();rows=json.loads(raw)
        rows=[[int(r[0]),*map(float,r[1:6]),int(r[6])] for r in rows]
        validate(rows);data[sym]=rows
        manifest.append(dict(symbol=sym,sha256=hashlib.sha256(raw).hexdigest(),bars=len(rows),start=iso(rows[0][0]),end=iso(rows[-1][6]+1)))
    ts=[r[0] for r in next(iter(data.values()))]
    assert all([r[0] for r in rows]==ts for rows in data.values())
    signals=prepare(data);results=[];trades={}
    for period,start,end in [('train','2026-07-04','2026-09-01'),('validation','2026-09-01','2026-10-02')]:
        for v in VARIANTS:
            r,t=simulate(data,signals,v,start,end);r['period']=period;results.append(r);trades[period+':'+v]=t
            print(period,v,round(r['net'],2),r['trades'],flush=True)
    for v in VARIANTS:
        r,t=simulate(data,signals,v,'2026-09-01','2026-10-02',.0004);r['period']='validation_double_slippage';results.append(r)
        trades[r['period']+':'+v]=t
    out.mkdir(parents=True,exist_ok=True)
    (out/'results.json').write_text(json.dumps(results,indent=2))
    (out/'trades.json').write_text(json.dumps(trades,separators=(',',':')))
    (out/'data_manifest.json').write_text(json.dumps(manifest,indent=2))
    (out/'runtime_parameters.json').write_text(json.dumps({k:getattr(c,k) for k in ['RISK_PER_TRADE','NET_RISK_REWARD','FEE_RATE','MIN_STOP_RATE','MAX_STOP_RATE','MIN_TARGET_MOVE_RATE','MAX_NOTIONAL_SHARE','MAX_OPEN_POSITIONS','BREAKEVEN_TRIGGER_R','MIN_TREND_STRENGTH','MIN_VOLUME_BREAKOUT','BREAKOUT_BODY_RATIO','BREAKOUT_BUFFER_RATE']},indent=2))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--data',type=Path,required=True);ap.add_argument('--output',type=Path,default=Path(__file__).parent/'results');a=ap.parse_args();run(a.data,a.output)
