"""Additive EMA20/50 4h PAPER strategy for BEST. No exchange order APIs.
Legacy strategies retain their handlers. Positions, cash and slots are shared.
"""
import math
from datetime import timedelta

SETUP='EMA_4H'
LABEL='BEST – EMA 4h'
BUILD='BESTOF-2026-10-02-EMA4H'
TF_MS=4*60*60*1000
FEE=.00095
SLIP=.0002
RISK=.001
ENTRY_WINDOW_MS=120000
_cache={}
checks={}
errors={}


def ema(values,period):
    value=values[0];a=2/(period+1)
    for x in values[1:]:value=a*x+(1-a)*value
    return value


def analyze_rows(rows,now_ms):
    closed=[r for r in rows if int(r[6])<now_ms]
    if len(closed)<250:raise ValueError('EMA 4h: chybí historie pro EMA200')
    if any(int(b[0])-int(a[0])!=TF_MS for a,b in zip(closed,closed[1:])):
        raise ValueError('EMA 4h: mezera v historii')
    close_ms=int(closed[-1][6])+1
    if now_ms-close_ms>TF_MS+45000:raise ValueError('EMA 4h: zastaralá data')
    for r in closed:
        o,h,l,c=map(float,r[1:5])
        if not all(math.isfinite(x) for x in (o,h,l,c)) or not 0<l<=min(o,c)<=max(o,c)<=h:
            raise ValueError('EMA 4h: neplatná svíčka')
    c=[float(r[4]) for r in closed]
    e20,e50,e200=(ema(c,p) for p in (20,50,200))
    prev20,prev50=(ema(c[:-1],p) for p in (20,50))
    tr=[max(float(b[2])-float(b[3]),abs(float(b[2])-float(a[4])),abs(float(b[3])-float(a[4]))) for a,b in zip(closed,closed[1:])]
    atr=sum(tr[-14:])/14
    return dict(setup=SETUP,timeframe='4h',side='LONG',candle_time=close_ms,
                price_closed=c[-1],ema20=e20,ema50=e50,ema200=e200,atr=atr,
                entry_signal=e20>e50 and prev20<=prev50 and c[-1]>e200,
                exit_signal=e20<e50)


async def frame(core,symbol):
    now_ms=int(core.utcnow().timestamp()*1000)
    saved=_cache.get(symbol)
    if saved and now_ms<saved['expires']:
        return dict(saved['data'])
    raw=await core.get_klines(symbol,'4h',500)
    data=analyze_rows(raw,now_ms)
    _cache[symbol]=dict(data=data,expires=min(now_ms+300000,data['candle_time']+TF_MS))
    return dict(data)


def net_per_unit(position,market_price):
    fee=position.get('fee_rate',FEE);slip=position.get('slippage_rate',SLIP)
    entry=float(position['entry_price']);exit_price=float(market_price)*(1-slip)
    return exit_price-entry-fee*(entry+exit_price)


def close_ema(core,symbol,market_price,reason):
    p=core.positions.get(symbol)
    if not p:return
    entry=float(p['entry_price']);qty=float(p['qty']);exit_price=market_price*(1-p['slippage_rate'])
    ideal=(market_price-p['entry_market'])*qty;gross=(exit_price-entry)*qty
    fees=(entry+exit_price)*qty*p['fee_rate'];net=gross-fees;at=core.utcnow()
    trade=dict(symbol=symbol,side='LONG',setup=SETUP,entry_market=p['entry_market'],
        entry_price=entry,exit_market=market_price,exit_price=exit_price,qty=qty,
        gross_pnl=ideal,slippage=max(0,ideal-gross),fees=fees,pnl=net,reason=reason,
        opened_at=p['opened_at'],closed_at=at.isoformat())
    core.PAPER_BALANCE+=net
    core.save_trade(trade)
    core.trade_history.insert(0,trade);core.trade_history=core.trade_history[:500]
    core.positions.pop(symbol,None)
    minutes=core.COOLDOWN_AFTER_LOSS_MIN if net<0 else core.COOLDOWN_AFTER_WIN_MIN
    core.cooldown_until[symbol]=(at+timedelta(minutes=minutes)).isoformat()
    core.save_state()
    print('BEST EMA_4H CLOSE',symbol,reason,net,flush=True)


def open_ema(core,symbol,a,market_price):
    if core.TRADING_MODE!='PAPER' or not core.DATABASE_URL:return False
    if symbol not in core.SYMBOLS or a.get('signal')!='LONG':return False
    if symbol in core.positions or len(core.positions)>=core.MAX_OPEN_POSITIONS:return False
    if core.cooldown_active(symbol):return False
    now_ms=int(core.utcnow().timestamp()*1000);stamp=int(a['candle_time'])
    if not 0<=now_ms-stamp<=ENTRY_WINDOW_MS:return False
    key=SETUP+':'+symbol
    if core.last_entry_candle.get(key)==stamp:return False
    stop=float(a['price_closed'])-2.5*float(a['atr'])
    entry=float(market_price)*(1+SLIP);rate=(entry-stop)/entry
    if not all(math.isfinite(x) for x in (entry,stop,rate)) or not .002<=rate<=.12:return False
    entry_check=getattr(core,'portfolio_entry_allowed',None)
    if callable(entry_check) and not entry_check('BEST',symbol,'LONG')[0]:return False
    # Never expand the original BEST maximum budget: original risk * original slots.
    budget=max(0.,core.PAPER_BALANCE*core.RISK_PER_TRADE*core.MAX_OPEN_POSITIONS)
    open_risk=sum(float(p.get('risk_usdt',0)) for p in core.positions.values())
    risk=min(core.PAPER_BALANCE*RISK,max(0.,budget-open_risk))
    allowance=getattr(core,'portfolio_risk_allowance',None)
    if callable(allowance):risk,_=allowance('BEST',symbol,'LONG',risk)
    if risk<=0:return False
    stop_fill=stop*(1-SLIP);loss=entry-stop_fill+FEE*(entry+stop_fill)
    exposure=sum(float(p['qty'])*float(p['entry_price']) for p in core.positions.values())
    position_cap=min(.5,getattr(core,'MAX_NOTIONAL_SHARE',.35))
    total_cap=min(1.,getattr(core,'MAX_NOTIONAL_SHARE',.35)*core.MAX_OPEN_POSITIONS)
    notional=min(core.PAPER_BALANCE*position_cap,max(0,core.PAPER_BALANCE*total_cap-exposure))
    qty=min(risk/loss,notional/entry)
    if qty<=0:return False
    core.positions[symbol]=dict(symbol=symbol,side='LONG',setup=SETUP,strategy_label=LABEL,
        timeframe='4h',entry_market=float(market_price),entry_price=entry,qty=qty,
        stop_loss=stop,initial_stop=stop,take_profit=None,risk_usdt=qty*loss,
        expected_reward_usdt=None,net_rr=None,breakeven_moved=False,
        opened_at=core.utcnow().isoformat(),signal_candle=stamp,
        last_trail_candle=stamp,best_close=float(a['price_closed']),
        fee_rate=FEE,slippage_rate=SLIP,volume_ratio=None,trend='LONG')
    core.last_entry_candle[key]=stamp
    core.last_entry_candle[symbol]=stamp
    core.save_state()
    print('BEST EMA_4H OPEN',symbol,'entry',entry,'SL',stop,'risk',qty*loss,flush=True)
    return True


async def manage_ema(core,symbol):
    p=core.positions.get(symbol)
    if not p:return
    price=await core.get_live_price(symbol,max_age=1.)
    if not math.isfinite(price) or price<=0:
        errors[symbol]='EMA 4h: neplatná aktuální cena';return
    if price<=float(p['stop_loss']):
        close_ema(core,symbol,price,'EMA 4h TRAILING SL' if p['stop_loss']>p['initial_stop'] else 'EMA 4h STOP LOSS');return
    # A failed 4h read never suppresses the existing hard stop check above.
    try:
        d=await frame(core,symbol);errors.pop(symbol,None)
    except Exception as e:
        errors[symbol]=str(e);return
    if d['candle_time']<=p.get('last_trail_candle',p['signal_candle']):return
    if d['exit_signal']:
        close_ema(core,symbol,price,'EMA 4h CROSS DOWN');return
    p['best_close']=max(float(p.get('best_close',p['entry_market'])),d['price_closed'])
    p['stop_loss']=max(float(p['stop_loss']),p['best_close']-3*d['atr'])
    p['last_trail_candle']=d['candle_time']
    core.save_state()
    if price<=p['stop_loss']:close_ema(core,symbol,price,'EMA 4h TRAILING SL')


def summary(core):
    groups=[]
    for label,ema_group in [('BEST – původní strategie',False),(LABEL,True)]:
        rows=[t for t in core.trade_history if (t.get('setup')==SETUP)==ema_group]
        ps=[p for p in core.positions.values() if (p.get('setup')==SETUP)==ema_group]
        wins=sum(float(t.get('pnl',0))>0 for t in rows)
        groups.append(dict(label=label,setup=SETUP if ema_group else 'LEGACY',trades=len(rows),
            wins=wins,win_rate=100*wins/len(rows) if rows else None,
            net_pnl=sum(float(t.get('pnl',0)) for t in rows),open_positions=len(ps)))
    return dict(build=BUILD,mode='PAPER',timeframe='4h',risk_per_trade=RISK,
        max_shared_positions=core.MAX_OPEN_POSITIONS,
        max_shared_initial_risk_rate=core.RISK_PER_TRADE*core.MAX_OPEN_POSITIONS,
        stats_scope='posledních 500 uzavřených obchodů Bestu',groups=groups,
        checks=dict(checks),errors=dict(errors),fee_rate=FEE,slippage_rate=SLIP)


def install(core):
    if getattr(core,'_ema4h_installed',False):return
    core._ema4h_installed=True
    original_strategy=core.strategy_analysis;original_open=core.open_trade;original_manage=core.manage_position
    async def strategy(symbol):
        a=await original_strategy(symbol)
        try:
            d=await frame(core,symbol);errors.pop(symbol,None)
            now_ms=int(core.utcnow().timestamp()*1000)
            fresh=0<=now_ms-d['candle_time']<=ENTRY_WINDOW_MS
            ready=d['entry_signal'] and fresh and core.last_entry_candle.get(SETUP+':'+symbol)!=d['candle_time']
            reason='Čekám na nové překřížení EMA20 nad EMA50 při ceně nad EMA200'
            if d['entry_signal'] and not fresh:reason='Starý 4h signál – čekám na nový, nevstupuji zpětně'
            if ready:reason='EMA 4h LONG potvrzen'
            if ready and a.get('signal') in ('LONG','SHORT'):reason='Přednost má původní BEST signál'
            if symbol in core.positions:reason='Best už na tomto trhu drží pozici'
            elif core.cooldown_active(symbol):reason='Společná pauza Bestu po obchodu'
            elif len(core.positions)>=core.MAX_OPEN_POSITIONS:reason='Společný limit pozic Bestu'
            checks[symbol]={**d,'fresh':fresh,'reason':reason,'checked_at':core.utcnow().isoformat()}
            if a.get('signal') not in ('LONG','SHORT') and ready:
                return {**d,'symbol':symbol,'signal':'LONG','reason':'BEST – EMA 4h','signal_low':d['price_closed']-2.5*d['atr'],'signal_high':d['price_closed']}
        except Exception as e:
            errors[symbol]=str(e);checks[symbol]={'reason':str(e),'error':True,'checked_at':core.utcnow().isoformat()}
        return a
    def open_trade(symbol,a,price):
        return open_ema(core,symbol,a,price) if a.get('setup')==SETUP else original_open(symbol,a,price)
    async def manage(symbol):
        p=core.positions.get(symbol)
        if p and p.get('setup')==SETUP:return await manage_ema(core,symbol)
        return await original_manage(symbol)
    core.strategy_analysis=strategy;core.open_trade=open_trade;core.manage_position=manage
