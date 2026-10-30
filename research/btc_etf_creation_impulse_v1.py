"""Frozen US spot-BTC ETF creation impulse signal and XRP simulator."""
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
import datetime as dt
import re

DAY = 86_400_000
UTC = dt.timezone.utc

@dataclass(frozen=True)
class Config:
    atr_n: int = 14
    stop_atr: float = 2.0
    reward_r: float = 3.0
    max_hold: int = 5
    risk_fraction: float = .005
    notional_cap: float = .20
    fee: float = .00095
    slippage: float = .00020

class _ETFTable(HTMLParser):
    def __init__(self):
        super().__init__(); self.in_table=False; self.in_row=False; self.in_cell=False; self.depth=0; self.cell=[]; self.row=[]; self.rows=[]
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag=='table' and not self.in_table and 'etf' in a.get('class','').split(): self.in_table=True; self.depth=1; return
        if not self.in_table:return
        if tag=='table':self.depth+=1
        if tag=='tr':self.in_row=True;self.row=[]
        elif tag=='td' and self.in_row:self.in_cell=True;self.cell=[]
    def handle_data(self, data):
        if self.in_cell:self.cell.append(data)
    def handle_endtag(self, tag):
        if not self.in_table:return
        if tag=='td' and self.in_cell:
            self.row.append(re.sub(r'\s+',' ',unescape(''.join(self.cell))).strip());self.in_cell=False
        elif tag=='tr' and self.in_row:
            if self.row:self.rows.append(self.row)
            self.in_row=False
        elif tag=='table':
            self.depth-=1
            if self.depth==0:self.in_table=False

def _number(s):
    s=s.strip().replace(',','')
    if s in ('','-'):return None
    neg=s.startswith('(') and s.endswith(')')
    if neg:s=s[1:-1]
    v=float(s)
    return -v if neg else v

def parse_farside_html(raw):
    p=_ETFTable();p.feed(raw.decode('utf-8'));out=[]
    for row in p.rows:
        try:d=dt.datetime.strptime(row[0],'%d %b %Y').replace(tzinfo=UTC)
        except (ValueError,IndexError):continue
        if len(row)!=14:raise ValueError('unexpected ETF row width')
        vals=[_number(x) for x in row[1:]]
        out.append(dict(timestamp=int(d.timestamp()*1000),date=row[0],fund_values=vals[:-1],total_flow=vals[-1]))
    if not out:raise ValueError('no ETF flow rows')
    if any(b['timestamp']<=a['timestamp'] for a,b in zip(out,out[1:])):raise ValueError('ETF dates not strictly increasing')
    return out

def make_signals(flows):
    out={}
    for x in flows:
        if x['total_flow'] is not None and x['total_flow']>0:
            out[x['timestamp']+2*DAY]=dict(flow_timestamp=x['timestamp'],total_flow=x['total_flow'])
    return out

def validate(rows):
    for i,x in enumerate(rows):
        if i and x['timestamp']<=rows[i-1]['timestamp']:raise ValueError('price order')
        if not 0<x['low']<=min(x['open'],x['close'])<=max(x['open'],x['close'])<=x['high']:raise ValueError('OHLC')

def atr(rows,i,n):
    if i<n+1:return None
    if any(rows[j]['timestamp']-rows[j-1]['timestamp']!=DAY for j in range(i-n,i)):return None
    return sum(max(rows[j]['high']-rows[j]['low'],abs(rows[j]['high']-rows[j-1]['close']),abs(rows[j]['low']-rows[j-1]['close'])) for j in range(i-n,i))/n

def backtest(rows,start,end,c=Config(),initial=10000.):
    validate(rows);equity=initial;trades=[];curve=[dict(timestamp=start,equity=initial)];i=0
    while i<len(rows):
        b=rows[i];s=b.get('etf_signal');a=atr(rows,i,c.atr_n)
        if not s or not(start<=b['timestamp']<end) or a is None or s['flow_timestamp']+2*DAY!=b['timestamp']:i+=1;continue
        raw=b['open'];entry=raw*(1+c.slippage);stop=entry-c.stop_atr*a
        if stop<=0:i+=1;continue
        qty=min(equity*c.risk_fraction/(entry-stop),equity*c.notional_cap/entry);target=entry+c.reward_r*(entry-stop);entry_fee=qty*entry*c.fee;before=equity;j=i
        while j<len(rows) and rows[j]['timestamp']<end:
            x=rows[j]
            if j>i and x['timestamp']-rows[j-1]['timestamp']!=DAY:raw_exit,reason,ei,et=rows[j-1]['close'],'DATA_GAP',j-1,rows[j-1]['timestamp']
            elif x['open']<=stop:raw_exit,reason,ei,et=x['open'],'GAP_STOP',j,x['timestamp']
            elif x['low']<=stop:raw_exit,reason,ei,et=stop,'STOP',j,x['timestamp']
            elif x['open']>=target or x['high']>=target:raw_exit,reason,ei,et=target,'TARGET',j,x['timestamp']
            elif j-i+1>=c.max_hold:raw_exit,reason,ei,et=x['close'],'TIME',j,x['timestamp']
            else:
                mark=x['low']*(1-c.slippage);curve.append(dict(timestamp=x['timestamp'],equity=before+qty*(mark-entry)-entry_fee-qty*mark*c.fee));j+=1;continue
            fill=raw_exit*(1-c.slippage);exit_fee=qty*fill*c.fee;gross=qty*(raw_exit-raw);fill_pnl=qty*(fill-entry);fees=entry_fee+exit_fee;pnl=fill_pnl-fees;equity+=pnl
            trades.append(dict(flow_timestamp=s['flow_timestamp'],total_flow=s['total_flow'],entry_timestamp=b['timestamp'],exit_timestamp=et,entry_index=i,exit_index=ei,entry_equity=before,raw_entry=raw,raw_exit=raw_exit,entry=entry,exit=fill,qty=qty,atr=a,stop=stop,target=target,leg_notional=qty*entry,gross=gross,slippage_cost=gross-fill_pnl,fees=fees,pnl=pnl,equity=equity,reason=reason,cost_fee=c.fee,cost_slippage=c.slippage));curve.append(dict(timestamp=et,equity=equity));i=ei+1;break
        else:i+=1
    return trades,curve
