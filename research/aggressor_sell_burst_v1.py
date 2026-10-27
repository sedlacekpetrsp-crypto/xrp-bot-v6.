"""Tick-sequence sell-burst reversal, isolated from production code."""
from dataclasses import dataclass
from math import isfinite

STEP=60_000
TS,O,H,L,C,EVENTS,SELLS,MAXSELL,VALID=range(9)

@dataclass(frozen=True)
class Config:
    min_sell_run:int=25; min_sell_share:float=.75; min_drop:float=.002
    stop_pct:float=.006; target_pct:float=.012; max_hold:int=30
    fee:float=.00095; slippage:float=.0002; risk:float=.005; notional_cap:float=.20

class MinuteBuilder:
    """Streaming conversion from ordered aggregate trades to compact minute bars."""
    def __init__(self):
        self.bars=[]; self.current=None; self.prev_id=None; self.prev_ts=None; self.id_gaps=0; self.records=0
    def _flush(self):
        if self.current is not None:
            x=self.current; self.bars.append((x['minute'],x['open'],x['high'],x['low'],x['close'],x['events'],x['sells'],x['maxsell'],x['valid']))
    def feed(self,trade_id,timestamp,price,seller):
        trade_id=int(trade_id); timestamp=int(timestamp); price=float(price); seller=bool(seller)
        if not isfinite(price) or price<=0: raise ValueError('price')
        if self.prev_id is not None and trade_id<=self.prev_id: raise ValueError('aggregate trade id')
        if self.prev_ts is not None and timestamp<self.prev_ts: raise ValueError('trade timestamp')
        minute=timestamp//STEP*STEP; gap=self.prev_id is not None and trade_id!=self.prev_id+1
        if gap: self.id_gaps+=1
        if self.current is None or minute!=self.current['minute']:
            if self.current is not None and gap: self.current['valid']=False
            self._flush()
            self.current=dict(minute=minute,open=price,high=price,low=price,close=price,events=0,sells=0,maxsell=0,run=0,valid=not gap)
        elif gap:
            self.current['valid']=False
        x=self.current; x['high']=max(x['high'],price); x['low']=min(x['low'],price); x['close']=price; x['events']+=1
        if seller: x['sells']+=1; x['run']+=1; x['maxsell']=max(x['maxsell'],x['run'])
        else: x['run']=0
        self.prev_id=trade_id; self.prev_ts=timestamp; self.records+=1
    def finish(self):
        self._flush(); self.current=None; return self.bars

def validate(bars):
    if not bars: raise ValueError('empty')
    if any(b[TS]%STEP for b in bars) or any(b[TS]<=a[TS] for a,b in zip(bars,bars[1:])): raise ValueError('timestamp')
    for b in bars:
        if not 0<b[L]<=min(b[O],b[C])<=max(b[O],b[C])<=b[H] or b[EVENTS]<=0 or not 0<=b[SELLS]<=b[EVENTS] or not 0<=b[MAXSELL]<=b[SELLS]: raise ValueError('bar')

def signal(bar,c=Config()):
    if not bar[VALID] or bar[MAXSELL]<c.min_sell_run or bar[SELLS]/bar[EVENTS]<c.min_sell_share or bar[C]>bar[O]*(1-c.min_drop): return None
    return dict(events=bar[EVENTS],seller_events=bar[SELLS],max_sell_run=bar[MAXSELL],seller_share=bar[SELLS]/bar[EVENTS],minute_return=bar[C]/bar[O]-1)

def backtest(bars,start,end,c=Config(),initial=10_000.):
    validate(bars); out=[]; equity=initial; i=0
    while i+1<len(bars):
        if bars[i+1][TS]<start: i+=1; continue
        if bars[i+1][TS]>=end: break
        found=signal(bars[i],c)
        if found is None or not bars[i+1][VALID] or bars[i+1][TS]-bars[i][TS]!=STEP: i+=1; continue
        ei=i+1; raw_entry=bars[ei][O]; entry=raw_entry*(1+c.slippage); stop=entry*(1-c.stop_pct); target=entry*(1+c.target_pct)
        qty=min(equity*c.risk/(entry-stop),equity*c.notional_cap/entry); raw_exit=None; reason=None; xi=ei
        for held in range(c.max_hold):
            j=ei+held
            if j>=len(bars) or bars[j][TS]>=end: break
            if not bars[j][VALID] or (j>ei and bars[j][TS]-bars[j-1][TS]!=STEP):
                xi=max(ei,j-1); raw_exit=bars[xi][C]; reason='DATA_GAP'; break
            b=bars[j]; xi=j
            if b[O]<=stop: raw_exit=b[O]; reason='GAP_STOP'; break
            if b[L]<=stop: raw_exit=stop; reason='STOP'; break
            if b[H]>=target: raw_exit=target; reason='TARGET'; break
            if held+1==c.max_hold: raw_exit=b[C]; reason='TIME'; break
        if raw_exit is None: raw_exit=bars[xi][C]; reason='END'
        fill=raw_exit*(1-c.slippage); fees=c.fee*qty*(entry+fill); gross=qty*(raw_exit-raw_entry); pnl=qty*(fill-entry)-fees; equity+=pnl
        out.append(dict(signal_index=i,entry_index=ei,exit_index=xi,entry=entry,exit=fill,raw_entry=raw_entry,raw_exit=raw_exit,stop=stop,target=target,qty=qty,pnl=pnl,equity=equity,fees=fees,gross=gross,slippage_cost=gross-fees-pnl,reason=reason,**found))
        if equity<=0: break
        i=xi+1
    return out

