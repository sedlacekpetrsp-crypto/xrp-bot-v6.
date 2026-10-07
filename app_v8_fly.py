from fastapi.responses import HTMLResponse, JSONResponse
# deploy marker 2026-09-26 quality fixes
from datetime import datetime, timezone, timedelta
import httpx
import app_v8 as base
import app_blue_whale_mirror as whale
import lead_lag_scalper as leadlag
import fast_scalper as fast
import news_signal
import tv_consensus_scalper as tv
import bestof_bot as bestof
import swing_paper
import swing_dashboard
import lh_whale
import lh_whale_dashboard
import lh_storage
from v8_fly_layer import install

install(base)

def _asset_key(symbol):
    s=str(symbol or "").upper()
    for q in ("USDC","USDT","USD"):
        if s.endswith(q):
            return s[:-len(q)]
    return s

PORTFOLIO_RISK_SHARES={
    "FLY":0.0014,
    "FAST":0.0008,
    "LEADLAG":0.0010,
    "TV":0.0008,
    "WHALE":0.0010,
    "BEST":0.0010,
}

def _portfolio_reference_balance():
    values=[
        float(getattr(base,"PAPER_BALANCE",0) or 0),
        float(fast.state.get("balance") or 0),
        float(leadlag.state.get("balance") or 0),
        float(tv.state.get("balance") or 0),
        float(whale.state.get("balance") or 0),
        float(getattr(bestof.core,"PAPER_BALANCE",0) or 0),
    ]
    values=[x for x in values if x>0]
    return min(values) if values else 10000.0

def portfolio_entry_allowed(bot_name, symbol, side):
    """Parallel positions are allowed; diversification comes from independent SL/TP logic."""
    return True,"parallel positions allowed"

def _same_direction_fly_exposure(symbol, side):
    """Count existing FLY exposure in the same crypto direction, excluding this asset."""
    asset=_asset_key(symbol)
    positions=[]
    p=getattr(base,"POSITION",None)
    if isinstance(p,dict):
        positions.append(p)
    extra=getattr(base,"OPEN_POSITIONS",None)
    if isinstance(extra,dict):
        positions.extend(extra.values())
    elif isinstance(extra,list):
        positions.extend(extra)
    seen=set()
    count=0
    for pos in positions:
        if not isinstance(pos,dict):
            continue
        key=(str(pos.get("symbol") or ""),str(pos.get("opened_at") or pos.get("entry_time") or ""))
        if key in seen:
            continue
        seen.add(key)
        if str(pos.get("side") or "").upper()==str(side or "").upper() and _asset_key(pos.get("symbol"))!=asset:
            count+=1
    return count

def portfolio_risk_allowance(bot_name, symbol, side, desired_risk):
    """Cap bot risk; reduce only additional correlated FLY positions, never block them."""
    ref=_portfolio_reference_balance()
    share=float(PORTFOLIO_RISK_SHARES.get(bot_name,0.0008))
    cap=max(1.0,ref*share)
    correlation_factor=1.0
    same_direction=0
    if bot_name=="FLY":
        same_direction=_same_direction_fly_exposure(symbol,side)
        if same_direction==1:
            correlation_factor=0.70
        elif same_direction>=2:
            correlation_factor=0.50
    cap*=correlation_factor
    allowed=min(max(0.0,float(desired_risk or 0)),cap)
    return allowed,{
        "asset":_asset_key(symbol),
        "side":side,
        "bot":bot_name,
        "reference_balance":ref,
        "risk_share":share,
        "risk_cap_usdc":cap,
        "same_direction_fly_positions":same_direction,
        "correlation_factor":correlation_factor,
    }

# Inject the coordinator without coupling the strategy modules to each other.
base.portfolio_entry_allowed=portfolio_entry_allowed
base.portfolio_risk_allowance=portfolio_risk_allowance
fast.portfolio_entry_allowed=portfolio_entry_allowed
fast.portfolio_risk_allowance=portfolio_risk_allowance
leadlag.portfolio_entry_allowed=portfolio_entry_allowed
leadlag.portfolio_risk_allowance=portfolio_risk_allowance
tv.portfolio_entry_allowed=portfolio_entry_allowed
tv.portfolio_risk_allowance=portfolio_risk_allowance
whale.portfolio_entry_allowed=portfolio_entry_allowed
whale.portfolio_risk_allowance=portfolio_risk_allowance
bestof.core.portfolio_entry_allowed=portfolio_entry_allowed
bestof.core.portfolio_risk_allowance=portfolio_risk_allowance

app = base.app
_original_analyze = base.analyze
_original_dashboard = base.dashboard
_whale_task = None
_tv_task = None
_bestof_task = None

app.router.routes[:] = [
    route for route in app.router.routes
    if not (
        getattr(route, "path", None) in ("/", "/analyze")
        and "GET" in (getattr(route, "methods", set()) or set())
    )
]


@app.get("/analyze")
async def analyze_with_pnl_breakdown():
    data = await _original_analyze()
    p = data.get("position")
    gross = net = costs = 0.0
    if p:
        cached = base.price_cache.get(p["symbol"])
        if cached:
            px = float(cached["price"])
            entry = float(p["entry_price"])
            qty = float(p["qty"])
            side = p["side"]
            gross = ((px - entry) if side == "LONG" else (entry - px)) * qty
            net = base.estimated_net_per_unit(side, entry, px) * qty
            costs = max(gross - net, 0.0)
    data["fly_build"] = base.FLY_LAYER_BUILD
    data["fly_entry_diagnostics"] = getattr(base, "FLY_ENTRY_DIAGNOSTICS", {})
    data["unrealized_gross_pnl"] = gross
    data["unrealized_pnl"] = net
    data["estimated_costs"] = costs
    data["equity"] = float(data.get("paper_balance", 0.0)) + net
    risk = data.get("risk_status") or {}
    recovery = base.recovery_status() if hasattr(base, "recovery_status") else {}
    data["recovery_status"] = recovery
    if recovery.get("breached") and not recovery.get("used"):
        data["trading_status"] = "RECOVERY_MODE"
        data["trading_status_label"] = "RECOVERY MODE – ČEKÁM NA A+ XRP LONG"
    elif risk.get("blocked"):
        data["trading_status"] = "DAILY_LOSS_LIMIT"
        data["trading_status_label"] = "BLOKOVÁNO – DAILY LOSS LIMIT"
    elif p:
        data["trading_status"] = "POSITION_OPEN"
        data["trading_status_label"] = "OBCHOD OTEVŘEN"
    else:
        data["trading_status"] = "WAITING"
        data["trading_status_label"] = "ČEKÁM NA SETUP"
    return JSONResponse(data, headers={"Cache-Control": "no-store"})


@app.get("/", response_class=HTMLResponse)
async def dashboard_with_pnl_breakdown():
    html = await _original_dashboard()
    old = "const p=d.position; document.getElementById('position').innerHTML=p?`<b>${p.symbol} ${p.side}</b> • entry ${f(p.entry_price,6)} • SL ${f(p.stop_loss,6)} • TP ${f(p.take_profit,6)} • uPnL ${f(d.unrealized_pnl,2)}`:'Žádná otevřená pozice';"
    new = "const p=d.position; document.getElementById('position').innerHTML=p?`<b>${p.symbol} ${p.side}</b> • entry ${f(p.entry_price,6)} • SL ${f(p.stop_loss,6)} • TP ${f(p.take_profit,6)}<br>Hrubý P/L <b class=\"${Number(d.unrealized_gross_pnl)>=0?'green':'red'}\">${Number(d.unrealized_gross_pnl)>=0?'+':''}${f(d.unrealized_gross_pnl,2)} USDC</b> • Čistý P/L <b class=\"${Number(d.unrealized_pnl)>=0?'green':'red'}\">${Number(d.unrealized_pnl)>=0?'+':''}${f(d.unrealized_pnl,2)} USDC</b> • Náklady ${f(d.estimated_costs,2)} USDC`:'Žádná otevřená pozice';"
    html = html.replace(old, new)
    html = html.replace("⚡ BOT V8 ADAPTIVE BREAKOUT SCALPER", "⚡ FLY + 🐋 WHALE + 🔗 LEAD-LAG — 24/7 PAPER")
    html = html.replace("PAPER • pouze BREAKOUT • čisté R:R 1:1,3", "FLY: BREAKOUT + TREND PULLBACK • WHALE • LEAD-LAG • FAST • PAPER")
    fly_guard_card = """
<div class="card" id="flyGuardCard" style="display:none;border:1px solid #7a2b2b;background:#2a1518">
  <h2 style="margin-top:0">🛑 FLY BLOKOVÁN</h2>
  <div id="flyGuardText" class="red" style="font-weight:700">BLOKOVÁNO – DAILY LOSS LIMIT</div>
</div>
"""
    html = html.replace('<div class="card"><h2>📡 Trhy</h2>', fly_guard_card + '<div class="card" style="border:2px solid #5ce68b;background:rgba(92,230,139,.035)"><h2>✈️ FLY · TRHY</h2>')
    html = html.replace('document.getElementById(\'trades\').innerHTML=(d.trade_history||[]).slice(0,20).map(t=>`<div class="trade"><span>${t.symbol}</span><span>${t.side}</span><span>${t.reason}<br><small class="muted">Uzavřeno: ${closedTime(t.closed_at)}</small></span><span class="${Number(t.pnl)>=0?\'green\':\'red\'}">${f(t.pnl,2)}</span></div>`).join(\'\')||\'<div class="muted">Zatím bez obchodů.</div>\';', "document.getElementById('trades').innerHTML=renderTradeHistory(d.trade_history||[], 'USDC');")
    whale_card = """
<div class="card" style="border:2px solid #7dd3fc;background:rgba(125,211,252,.03)">
  <h2>🐋 BLUE WHALE · FIB + VWAP</h2>
  <div class="muted">PAPER • Fibonacci 0,618–0,786 + návrat k VWAP • BTC / ETH / SOL / XRP</div>
  <div id="whaleSignals" class="coin muted" style="margin-top:10px"></div>
  <div id="whaleStats" class="grid"></div>
  <div id="whalePosition" class="coin muted" style="margin-top:10px">Načítám…</div>
  <div id="whaleTrades" style="display:none;margin-top:10px"></div>
  <div id="whaleHealth" class="muted" style="margin-top:10px">Načítám…</div>
</div>
"""
    fast_card = """
<div class="card" style="border:2px solid #ffd166;background:rgba(255,209,102,.025)">
  <h2 style="color:#ffd166">⚡ FAST EDGE SCALPER</h2>
  <div class="muted" style="margin-bottom:10px">XRP / ETH / SOL • rychlý momentum scalp • PAPER</div>
  <div id="fastStats" class="grid"></div>
  <div id="fastTrades" style="display:none;margin-top:10px"></div>
  <div id="fastPosition" class="coin muted" style="margin-top:10px">Načítám…</div>
  <div id="fastAnalysis" style="margin-top:10px"></div>
  <div id="fastHealth" class="muted" style="margin-top:10px">Načítám…</div>
</div>
"""
    leadlag_card = """
<div class="card" style="border:2px solid #4fc3f7;background:rgba(79,195,247,.03)">
  <h2 style="color:#4fc3f7">🔗 XRP LEAD-LAG SCALPER</h2>
  <div class="muted" style="margin-bottom:10px">BTC + ETH lead • XRP lag • order book potvrzení • PAPER</div>
  <div id="leadlagStats" class="grid"></div>
  <div id="leadlagPosition" class="coin muted" style="margin-top:10px">Načítám…</div>
  <div id="leadlagAnalysis" class="coin muted" style="margin-top:10px">Načítám analýzu…</div>
  <div style="margin-top:12px"><b>Poslední obchody</b></div>
  <div id="leadlagTrades" style="display:none;margin-top:6px"></div>
  <div id="leadlagHealth" class="muted" style="margin-top:10px">Načítám…</div>
</div>
"""
    tv_card = """
<div class="card" style="border:2px solid #4fc3f7;background:rgba(79,195,247,.03)">
  <h2 style="color:#4fc3f7">📊 TV CONSENSUS XRP</h2>
  <div class="muted" style="margin-bottom:10px">MA + MACD/Momentum + RSI/Stoch/CCI + ADX • 15m trend • PAPER</div>
  <div id="tvPosition" role="status" aria-live="polite" style="padding:18px;border:2px solid #566475;border-radius:14px;margin-bottom:14px">Načítám stav pozice…</div>
  <div id="tvStats" class="grid"></div>
  <div id="tvSignal" class="coin muted" style="margin-top:10px">Načítám…</div>
  <div id="tvTrades" style="margin-top:10px"></div>
</div>
"""
    bestof_card = """
<div class="card" style="border:2px solid #b388ff;background:rgba(179,136,255,.03)">
  <h2 style="color:#b388ff">🏆 BEST-OF</h2>
  <div class="muted" style="margin-bottom:10px">Výběr nejlepších setupů • 24/7 • PAPER</div>
  <div id="bestofStats" class="grid"></div>
  <div id="bestofStrategies" style="margin-top:12px"></div>
  <div id="bestofPosition" class="coin muted" style="margin-top:10px">Načítám…</div>
  <div style="margin-top:12px"><b>Poslední obchody</b></div>
  <div id="bestofTrades" style="margin-top:6px"></div>
  <div id="bestofHealth" class="muted" style="margin-top:10px">Načítám…</div>
</div>
"""
    html = html.replace('<div class="card muted" id="health">', whale_card + fast_card + leadlag_card + tv_card + bestof_card + '<div class="card muted" id="health">')
    whale_js = """

function historyEscape(v){
 return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function historyDate(v){
 if(!v)return null;
 const d=new Date(v);
 return Number.isFinite(d.getTime())?d:null;
}
function historyTime(v){
 const d=historyDate(v);
 if(!d)return '—';
 const date=d.toLocaleDateString('cs-CZ',{timeZone:'Europe/Prague',day:'2-digit',month:'2-digit',year:'numeric'});
 const time=d.toLocaleTimeString('cs-CZ',{timeZone:'Europe/Prague',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'});
 return `${date}<br>${time}`;
}
function renderTradeHistory(trades,currency){
 const rows=trades.slice().sort((a,b)=>(historyDate(b.closed_at)?.getTime()??0)-(historyDate(a.closed_at)?.getTime()??0)).slice(0,20);
 if(!rows.length)return '<div class="muted">Zatím žádné uzavřené obchody.</div>';
 const colors={BTC:'#f7931a',ETH:'#8c9eff',SOL:'#14f195',XRP:'#4fc3f7'};
 return '<div class="muted history-note">Posledních 20 obchodů · datum a čas uzavření · český čas</div><div class="trade history-row history-heading"><span>Obchod / uzavřeno</span><span>Vstup → výstup</span><span>Důvod ukončení</span><span>Čistý výsledek</span></div>'+rows.map(t=>{
  const symbol=String(t.symbol||'—');
  const asset=symbol.replace(/(USDC|USDT|USD)$/,'');
  const color=colors[asset]||'#a7b6c6';
  const value=t.net_pnl??t.pnl;
  const pnl=value==null?NaN:Number(value);
  const valid=Number.isFinite(pnl);
  const detail=t.setup==='EMA_4H'?'BEST – EMA 4h':(t.strategy||t.setup||'');
  return `<div class="trade history-row"><span><b style="color:${color}">${historyEscape(symbol)}</b><br><b class="${t.side==='LONG'?'green':t.side==='SHORT'?'red':'muted'}">${historyEscape(t.side||'—')}</b><br><span class="history-time">${historyTime(t.closed_at)}</span></span><span>${f(t.entry??t.entry_price,6)}<br>→<br>${f(t.exit??t.exit_price,6)}</span><span>${historyEscape(t.reason||'—')}${detail?'<br><small class="muted">'+historyEscape(detail)+'</small>':''}</span><span class="${valid?(pnl>=0?'green':'red'):'muted'}">${valid?(pnl>=0?'+':'')+f(pnl,2):'—'} ${historyEscape(currency)}</span></div>`;
 }).join('');
}
async function refreshFlyGuard(){
 try{
  const r=await fetch('/analyze',{cache:'no-store'}),d=await r.json();
  const guard=document.getElementById('flyGuardCard');
  const guardText=document.getElementById('flyGuardText');
  if(!guard)return;
  const rs=d.risk_status||{};
  const rec=d.recovery_status||{};
  if(rec.breached && !rec.used){
   guard.style.display='block';
   guard.querySelector('h2').innerHTML='🟠 FLY RECOVERY MODE';
   guardText.className='yellow';
   guardText.innerHTML=`ČEKÁM NA 1× A+ XRP LONG • risk 0,15 % • dnešní PnL ${f(rec.today_pnl,2)} USDC • limit -${f(rec.daily_loss_limit,2)} USDC`;
  }else if(rs.blocked){
   guard.style.display='block';
   guard.querySelector('h2').innerHTML='🛑 FLY BLOKOVÁN';
   guardText.className='red';
   guardText.innerHTML=`BLOKOVÁNO – DAILY LOSS LIMIT • dnešní PnL ${f(rs.today_pnl,2)} USDC • limit -${f(rs.daily_loss_limit,2)} USDC`;
  }else{
   guard.style.display='none';
  }
 }catch(e){}
}
async function refreshWhale(){
 try{
  const r=await fetch('/whale/status',{cache:'no-store'}),w=await r.json(),ts=w.trades||[];
  const wins=ts.filter(t=>Number(t.net_pnl)>0).length;
  const pnl=ts.reduce((a,t)=>a+Number(t.net_pnl||0),0);
  const wr=ts.length?100*wins/ts.length:0;
  const ps=w.open_positions||[];
  const p=ps[0]||w.open_position||null;
  const unreal=w.equity==null?NaN:Number(w.equity)-Number(w.balance);
  const unrealText=`<span class="${unreal>=0?'green':'red'}">${unreal>=0?'+':''}${Number.isFinite(unreal)?f(unreal,2):'—'} USD</span>`;
  const realizedText=`<span class="${pnl>=0?'green':'red'}">${pnl>=0?'+':''}${f(pnl,2)} USD</span>`;
  document.getElementById('whaleStats').innerHTML=[
   ['Balance',f(w.balance,2)+' USD'],['Equity',w.equity==null?'Data nejsou aktuální':f(w.equity,2)+' USD'],
   ['Uzavřené obchody',ts.length],['Otevřené obchody',ps.length|| (p?1:0)],
   ['Win rate',f(wr,1)+' %'],['Realizované PnL',realizedText],
   ['Nerealizované PnL',unrealText],['Status',w.status||'—'],
   ['Obchodní stav',p?'OBCHOD OTEVŘEN':'⏳ ČEKÁM NA OBCHOD']
  ].map(x=>x[0]==='Uzavřené obchody' ? `<div class="coin" onclick="const e=document.getElementById('whaleTrades');const o=e.style.display!=='block';e.style.display=o?'block':'none';this.querySelector('.whale-arrow').textContent=o?'▲':'▼'" style="cursor:pointer"><div class="muted">Uzavřené obchody <span class="whale-arrow">▼</span></div><b>${x[1]}</b><div class="muted" style="font-size:12px;margin-top:5px">Klepni pro historii</div></div>` : `<div class="coin"><div class="muted">${x[0]}</div><b>${x[1]}</b></div>`).join('');
  document.getElementById('whalePosition').innerHTML=ps.length
   ? ps.map((p,i)=>`<div style="${i?'margin-top:10px;padding-top:10px;border-top:1px solid #29343e':''}"><b>#${i+1} ${p.symbol||'BTCUSDT'} ${p.side} · ${p.strategy||'Původní signál'}</b> • entry ${f(p.entry,6)} • SL ${f(p.stop,6)} • TP ${f(p.tp,6)} • risk ${f(p.risk_dollars,2)} USD</div>`).join('')+`<div style="margin-top:8px">Celkové uPnL <b class="${unreal>=0?'green':'red'}">${unreal>=0?'+':''}${f(unreal,2)} USD</b></div>`
   : (p
      ? `<b>${p.symbol||'BTCUSDT'} ${p.side} · ${p.strategy||'Původní signál'}</b> • entry ${f(p.entry,6)} • SL ${f(p.stop,6)} • TP ${f(p.tp,6)} • risk ${f(p.risk_dollars,2)} USD • uPnL ${unreal>=0?'+':''}${f(unreal,2)} USD`
      : '<b class="yellow">⏳ ČEKÁM NA OBCHOD</b><div style="margin-top:6px">Žádná otevřená Whale pozice.</div>');
  document.getElementById('whaleTrades').innerHTML=renderTradeHistory(ts, 'USD');
  const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const symbolStyle={
   BTCUSDT:{label:'BTC',accent:'#f7931a',bg:'rgba(247,147,26,.08)'},
   ETHUSDT:{label:'ETH',accent:'#8c9eff',bg:'rgba(140,158,255,.08)'},
   SOLUSDT:{label:'SOL',accent:'#14f195',bg:'rgba(20,241,149,.07)'},
   XRPUSDT:{label:'XRP',accent:'#4fc3f7',bg:'rgba(79,195,247,.08)'}
  };
  const checks=w.signal_checks||[];
  const grouped={};
  checks.forEach(a=>(grouped[a.symbol]||(grouped[a.symbol]=[])).push(a));
  const order=['BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT'];
  document.getElementById('whaleSignals').innerHTML=order.map(sym=>{
   const rows=grouped[sym]||[];
   if(!rows.length)return '';
   const s=symbolStyle[sym]||{label:sym,accent:'#a7b6c6',bg:'rgba(167,182,198,.06)'};
   const body=rows.map(a=>{
    const reason=String(a.reason||'');
    const ready=/Obchod otevřen|potvrzen/i.test(reason);
    const waiting=/Čekám|Swing je příliš malý|příliš malý/i.test(reason);
    const stateColor=ready?'#5ce68b':waiting?'#ffd166':'#ff8a80';
    return `<div style="padding:9px 0;border-top:1px solid rgba(255,255,255,.07)">
      <div style="font-weight:800">${esc(a.strategy)}</div>
      <div style="margin-top:3px;color:${stateColor};font-weight:700">${esc(reason)}</div>
      ${a.fib_618!=null?`<div class="muted" style="margin-top:4px">0,618: ${f(a.fib_618,6)} · 0,786: ${f(a.fib_786,6)}</div>`:''}
      ${a.vwap!=null?`<div class="muted" style="margin-top:4px">VWAP: ${f(a.vwap,6)}</div>`:''}
     </div>`;
   }).join('');
   return `<div style="margin:10px 0;padding:12px 14px;border:2px solid ${s.accent};border-radius:14px;background:${s.bg}">
     <div style="font-size:22px;font-weight:900;color:${s.accent};letter-spacing:.3px">${s.label}</div>
     ${body}
    </div>`;
  }).join('')||'Načítám podmínky vstupu…';
  document.getElementById('whaleHealth').innerHTML=
   `<b>BTC cena:</b> ${w.market_price ? f(w.market_price,2)+" USD" : "—"} • <b>Scan:</b> ${w.last_scan||'—'}<br><b>Ukládání:</b> ${w.persistence||'memory'} • <b>Chyba:</b> ${esc(w.error||w.persistence_error||'žádná')}`;
 }catch(e){
  document.getElementById('whaleHealth').textContent='Whale dashboard error: '+e;
 }
}
"""
    fast_js = """
async function refreshFast(){
 try{
  const r=await fetch('/fast/status',{cache:'no-store'}),w=await r.json(),ts=w.trades||[];
  const wins=ts.filter(t=>Number(t.net_pnl)>0).length;
  const pnl=ts.reduce((a,t)=>a+Number(t.net_pnl||0),0);
  const wr=ts.length?100*wins/ts.length:0;
  const p=w.open_position;
  const unreal=Number(w.equity||0)-Number(w.balance||0);
  const assetStyle={
   XRPUSDC:{label:'XRP',accent:'#4fc3f7',bg:'rgba(79,195,247,.08)'},
   ETHUSDC:{label:'ETH',accent:'#8c9eff',bg:'rgba(140,158,255,.08)'},
   SOLUSDC:{label:'SOL',accent:'#14f195',bg:'rgba(20,241,149,.07)'}
  };
  const pnlText=`<span class="${pnl>=0?'green':'red'}">${pnl>=0?'+':''}${f(pnl,2)} USDC</span>`;
  document.getElementById('fastStats').innerHTML=[
   ['Balance',f(w.balance,2)+' USDC'],['Equity',f(w.equity,2)+' USDC'],
   ['Obchody',ts.length],['Win rate',f(wr,1)+' %'],['Realizované PnL',pnlText],
   ['Status',w.status||'—']
  ].map(x=>x[0]==='Obchody'
    ? `<div class="coin" id="fastTradesToggle" role="button" tabindex="0" style="cursor:pointer;border:1px solid #6b5b2a;touch-action:manipulation;user-select:none"><div class="muted">Obchody <span id="fastTradesArrow">▼</span></div><b>${x[1]}</b><div class="muted" style="font-size:12px;margin-top:5px">Klepni pro historii</div></div>`
    : `<div class="coin"><div class="muted">${x[0]}</div><b>${x[1]}</b></div>`).join('');
  const fastToggle=document.getElementById('fastTradesToggle');
  if(fastToggle){
   const toggleFastTrades=()=>{
    const e=document.getElementById('fastTrades'),arrow=document.getElementById('fastTradesArrow');
    if(!e)return;
    const open=e.style.display!=='block';
    e.style.display=open?'block':'none';
    if(arrow)arrow.textContent=open?'▲':'▼';
    if(open)setTimeout(()=>e.scrollIntoView({behavior:'smooth',block:'nearest'}),0);
   };
   fastToggle.onclick=toggleFastTrades;
   fastToggle.onkeydown=(ev)=>{if(ev.key==='Enter'||ev.key===' '){ev.preventDefault();toggleFastTrades();}};
  }
  document.getElementById('fastPosition').innerHTML=p
   ? `<b style="color:${(assetStyle[p.symbol]||{}).accent||'#eef4f8'}">${(assetStyle[p.symbol]||{}).label||p.symbol}</b> <b>${p.side}</b> • entry ${f(p.entry,6)} • SL ${f(p.stop,6)} • TP ${f(p.tp,6)} • uPnL <b class="${unreal>=0?'green':'red'}">${unreal>=0?'+':''}${f(unreal,2)} USDC</b>`
   : '<b class="yellow">⏳ ČEKÁM NA OBCHOD</b>';
  document.getElementById('fastAnalysis').innerHTML=(w.analysis||[]).map(a=>{
   const st=assetStyle[a.symbol]||{label:a.symbol,accent:'#a7b6c6',bg:'rgba(167,182,198,.06)'};
   const sig=a.fast_signal||'WAIT';
   const stateColor=sig==='LONG'?'#5ce68b':sig==='SHORT'?'#ff6b6b':'#ffd166';
   return `<div style="margin:9px 0;padding:12px 14px;border:2px solid ${st.accent};border-radius:14px;background:${st.bg}">
    <div style="font-size:21px;font-weight:900;color:${st.accent}">${st.label}</div>
    <div style="margin-top:5px">Signál <b style="color:${stateColor}">${sig}</b> • score ${a.fast_score??'—'} • vol ${f(a.volume_ratio,2)}x • z ${f(a.z_momentum,2)} • book ${f(a.book_imbalance,3)}</div>
    <div class="muted" style="margin-top:4px">${(a.fast_blockers||[]).length?'Blokuje: '+a.fast_blockers.join(' • '):'Podmínky bez blokace'}</div>
   </div>`;
  }).join('')||'<div class="coin muted">Načítám analýzu…</div>';
  document.getElementById('fastTrades').innerHTML=renderTradeHistory(ts, 'USDC');
  document.getElementById('fastHealth').textContent=`Scan: ${w.last_scan||'—'} • ukládání: ${w.persistence||'memory'} • chyba: ${w.error||w.persistence_error||'žádná'}`;
 }catch(e){
  document.getElementById('fastHealth').textContent='FAST dashboard error: '+e;
 }
}
"""
    leadlag_js = """
async function refreshLeadLag(){
 try{
  const r=await fetch('/leadlag/status',{cache:'no-store'}),w=await r.json(),ts=w.trades||[];
  const wins=ts.filter(t=>Number(t.net_pnl)>0).length;
  const pnl=ts.reduce((a,t)=>a+Number(t.net_pnl||0),0);
  const fees=ts.reduce((a,t)=>a+Number(t.fees||0),0);
  const wr=ts.length?100*wins/ts.length:0;
  const p=w.open_position;
  const unreal=Number(w.equity||0)-Number(w.balance||0);
  const pnlText=`<span class="${pnl>=0?'green':'red'}">${pnl>=0?'+':''}${f(pnl,2)} USDC</span>`;
  const unrealText=`<span class="${unreal>=0?'green':'red'}">${unreal>=0?'+':''}${f(unreal,2)} USDC</span>`;
  document.getElementById('leadlagStats').innerHTML=[
   ['Balance',f(w.balance,2)+' USDC'],['Equity',f(w.equity,2)+' USDC'],
   ['Obchody',ts.length],['Win rate',f(wr,1)+' %'],
   ['Realizované PnL',pnlText],['Poplatky',f(fees,2)+' USDC'],
   ['Nerealizované PnL',unrealText],['Status',w.status||'—'],
   ['Obchodní stav',p?'OBCHOD OTEVŘEN':'⏳ ČEKÁM NA OBCHOD']
  ].map(x=>x[0]==='Obchody' ? `<div class="coin" onclick="const e=document.getElementById('leadlagTrades');const open=e.style.display!=='block';e.style.display=open?'block':'none';this.querySelector('.leadlag-arrow').textContent=open?'▲':'▼'" style="cursor:pointer"><div class="muted">Obchody <span class="leadlag-arrow">▼</span></div><b>${x[1]}</b><div class="muted" style="font-size:12px;margin-top:5px">Klepni pro historii</div></div>` : `<div class="coin"><div class="muted">${x[0]}</div><b>${x[1]}</b></div>`).join('');
  document.getElementById('leadlagPosition').innerHTML=p
   ? `<b>XRPUSDC ${p.side}</b> • entry ${f(p.entry,6)} • SL ${f(p.stop,6)} • TP ${f(p.tp,6)} • risk ${f(p.risk_dollars,2)} USDC • uPnL ${unreal>=0?'+':''}${f(unreal,2)} USDC`
   : '<b class="yellow">⏳ ČEKÁM NA OBCHOD</b><div style="margin-top:6px">Žádná otevřená Lead-Lag pozice.</div>';
  const a=w.analysis||{};
  const scanText=w.last_scan?new Date(w.last_scan).toLocaleString('cs-CZ'):'—';
  const blockerList=a.blockers||[];
  const blockerText=blockerList.length
   ? 'Blokuje vstup: '+blockerList.slice(0,5).join(' • ')
   : (a.signal==='WAIT'?'Čekám na nový setup':'Vstupní podmínky splněny');
  const tradeState=p?'🟢 OBCHOD OTEVŘEN':'⏳ ČEKÁM NA OBCHOD';
  document.getElementById('leadlagAnalysis').innerHTML=
   `<b class="${p?'green':'yellow'}">${tradeState}</b> • poslední scan ${scanText}<br>
   Signal <b>${a.signal||'WAIT'}</b> •
   <span style="color:#f7931a;font-weight:800">BTC ${f(Number(a.btc_return||0)*100,3)} %</span> •
   <span style="color:#8c9eff;font-weight:800">ETH ${f(Number(a.eth_return||0)*100,3)} %</span> •
   <span style="color:#4fc3f7;font-weight:800">XRP ${f(Number(a.xrp_return||0)*100,3)} %</span> •
   lag ${f(Number(a.lag_return||0)*100,3)} % • book ${f(a.book_imbalance,3)}<br><span class="muted">${blockerText}</span>`;
  document.getElementById('leadlagTrades').innerHTML=renderTradeHistory(ts, 'USDC');
  document.getElementById('leadlagHealth').textContent=
   `Scan: ${w.last_scan||'—'} • ukládání: ${w.persistence||'memory'} • chyba: ${w.error||w.persistence_error||'žádná'}`;
 }catch(e){
  document.getElementById('leadlagHealth').textContent='Lead-Lag dashboard error: '+e;
 }
}
"""
    tv_js = """
async function refreshTV(){
 try{
  const r=await fetch('/tv/status',{cache:'no-store'});
  if(!r.ok)throw new Error('HTTP '+r.status);
  const w=await r.json(),a=w.analysis||{},ts=w.trades||[];
  const p=w.open_position;
  const updated=Date.parse(w.last_scan||'');
  const stale=!Number.isFinite(updated)||Date.now()-updated>60000||Boolean(w.error)||Boolean(w.exit_error);
  const net=Number(w.equity)-Number(w.balance);
  const validNet=w.equity!=null&&w.balance!=null&&Number.isFinite(net);
  const color=stale?'#ffd166':p?(net>=0?'#5ce68b':'#ff6b6b'):'#a7b6c6';
  const positionBox=document.getElementById('tvPosition');
  positionBox.style.borderColor=color;
  positionBox.style.background=p&&!stale?(net>=0?'#10271d':'#2c171d'):'#10171f';
  const signedNet=validNet?(net>=0?'+':'')+f(net,2):'—';
  positionBox.innerHTML=p
    ? `<div style="font-size:22px;font-weight:800">● ${stale?'POSLEDNÍ ZNÁMÁ POZICE':'V POZICI'} — ${p.side}</div>
       <div style="margin-top:6px;font-weight:700">${p.symbol||'XRPUSDC'} • PAPER</div>
       <div style="margin-top:16px">${stale?'Poslední známý':'Aktuální'} čistý zisk / ztráta</div>
       <div style="font-size:clamp(30px,8vw,48px);font-weight:800;line-height:1.2;color:${color};margin:6px 0">${signedNet} <span style="font-size:18px">USDC</span></div>
       <div style="font-size:13px;opacity:.8">Po poplatcích a simulovaném skluzu při uzavření</div>
       <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:12px;margin-top:18px">
       <div>Vstup<br><b>${f(p.entry,6)}</b></div><div>Aktuální cena<br><b style="font-size:22px">${f(w.current_price??a.price,6)}</b></div><div>Stop-loss<br><b>${f(p.stop,6)}</b></div><div>Cíl zisku<br><b>${f(p.tp,6)}</b></div></div>
       <div style="margin-top:12px">${p.profit_protected?'🛡 Ochrana zisku aktivní':'Stop-loss aktivní'} • Otevřeno ${closedTime(p.opened_at)}</div>`
    : `<div style="font-size:22px;font-weight:800">${stale?'POSLEDNÍ ZNÁMÝ STAV: BEZ POZICE':'BEZ POZICE — ČEKÁ NA OBCHOD'}</div><div style="margin-top:12px">Žádný otevřený obchod • PAPER</div>`;
  positionBox.innerHTML+=`<div style="margin-top:12px;font-size:13px;color:${stale?'#ffd166':'#a7b6c6'}">${stale?'⚠ Data nejsou aktuální. ':''}Poslední výpočet: ${closedTime(w.last_scan)}</div>`;
  const wins=ts.filter(t=>Number(t.net_pnl)>0).length;
  const wr=ts.length?100*wins/ts.length:0;
  const pnl=ts.reduce((s,t)=>s+Number(t.net_pnl||0),0);
  document.getElementById('tvStats').innerHTML=`
   <div class="coin"><div class="muted">Balance</div><b>${f(w.balance,2)} USDC</b></div>
   <div class="coin"><div class="muted">Equity</div><b>${f(w.equity,2)} USDC</b></div>
   <div class="coin" id="tvTradesToggle" style="cursor:pointer;border:1px solid #334155">
    <div class="muted">Obchody <span id="tvTradesArrow">▼</span></div><b>${ts.length}</b>
    <div class="muted" style="font-size:12px;margin-top:5px">Klepni pro historii</div>
   </div>
   <div class="coin"><div class="muted">Win rate</div><b>${f(wr,1)} %</b></div>
   <div class="coin"><div class="muted">Zisk / ztráta uzavřených obchodů</div><b>${pnl>=0?'+':''}${f(pnl,2)} USDC</b></div>
   <div class="coin"><div class="muted">Status</div><b>${w.status||'—'}</b></div>`;
  const toggle=document.getElementById('tvTradesToggle');
  if(toggle) toggle.onclick=()=>{
   const e=document.getElementById('tvTrades'),arrow=document.getElementById('tvTradesArrow');
   const open=e.style.display!=='block'; e.style.display=open?'block':'none'; if(arrow)arrow.textContent=open?'▲':'▼';
  };
  const sig=a.signal||'WAIT', cls=sig==='LONG'?'green':sig==='SHORT'?'red':'yellow';
  document.getElementById('tvSignal').innerHTML=`<b class="${cls}">${sig}</b> • L/S ${f(a.long_score,1)} / ${f(a.short_score,1)} • accel ${f(a.long_accel,1)} / ${f(a.short_accel,1)} • 15m ${a.trend_15m||'—'}<br><span class="muted">MA buy/sell ${a.ma_buy??'—'}/${a.ma_sell??'—'} • ADX ${f(a.adx5,1)} • volume ${f(a.volume_ratio,2)}x • ${p?'OBCHOD OTEVŘEN':'ČEKÁM NA SETUP'}</span>`;
  const tvDetails = p
    ? `<br><b>XRPUSDC ${p.side}</b> • vstup ${f(p.entry,6)} • SL ${f(p.stop,6)} • TP ${f(p.tp,6)}<br>Čistý otevřený P/L ${f(Number(w.equity)-Number(w.balance),2)} USDC • ${p.profit_protected?'OCHRANA ZISKU AKTIVNÍ':'Základní stop-loss'}`
    : `<br>${w.status==='daily_loss_guard'?'Denní limit ztráty — nové vstupy pozastaveny do '+closedTime(w.guard_until):((a.blockers||[]).join(' • ') || 'Signál připraven / kontroluji rizikové limity')}${w.cooldown_until&&Date.parse(w.cooldown_until)>Date.now()?' • Pauza do '+closedTime(w.cooldown_until):''}<br>Cena ${f(w.current_price??a.price,6)} • ${w.build||''}`;
  document.getElementById('tvSignal').innerHTML += tvDetails;
  if(!document.getElementById('tvTrades').dataset.init){document.getElementById('tvTrades').style.display='none';document.getElementById('tvTrades').dataset.init='1';}
  document.getElementById('tvTrades').innerHTML=renderTradeHistory(ts, 'USDC');
 }catch(e){
  document.getElementById('tvPosition').innerHTML='<b style="font-size:22px;color:#ffd166">⚠ STAV POZICE NELZE OVĚŘIT</b><div style="margin-top:10px">Spojení se nezdařilo. Čekám na nová data.</div>';
  document.getElementById('tvPosition').style.borderColor='#ffd166';
  document.getElementById('tvSignal').textContent='TV Consensus error: '+e;
 }
}
"""
    bestof_js = """
function renderBestOfPosition(p){
 const finite=v=>v!=null&&Number.isFinite(Number(v));
 const valid=finite(p.unrealized_net_pnl),net=Number(p.unrealized_net_pnl);
 const age=Date.now()-Date.parse(p.price_updated_at||'');
 const stale=p.price_stale||!Number.isFinite(age)||age>30000;
 const color=stale||!valid?'#ffd166':net>=0?'#5ce68b':'#ff6b6b';
 const signed=v=>(Number(v)>=0?'+':'')+f(v,2);
 return `<div style="border:2px solid ${color};border-radius:14px;padding:16px;margin-top:12px;background:#10171f">
 <div style="font-size:22px;font-weight:800">${historyEscape(p.symbol)} <span class="${p.side==='LONG'?'green':'red'}">${historyEscape(p.side)}</span></div>
 <div style="margin-top:6px">OTEVŘENÝ OBCHOD • PAPER • ${p.setup==='EMA_4H'?'BEST – EMA 4h':historyEscape(p.setup||'BEST')}</div>
 <div style="margin-top:14px">${stale?'Poslední známý':'Průběžný'} čistý zisk / ztráta</div>
 <div style="font-size:32px;font-weight:800;color:${color}">${valid?signed(net):'—'} USDT</div>
 <div>${finite(p.unrealized_net_pct)?signed(p.unrealized_net_pct)+' % z hodnoty pozice':''}</div>
 <div class="muted" style="font-size:12px;margin-top:5px">Odhad po vstupním a výstupním poplatku a skluzu při uzavření</div>
 <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-top:16px">
 <div>Vstupní cena<br><b>${f(p.entry_price,6)}</b></div>
 <div>${stale?'Poslední cena':'Aktuální cena'}<br><b>${finite(p.current_price)?f(p.current_price,6):'—'}</b></div>
 <div>Stop-loss<br><b>${f(p.stop_loss,6)}</b></div><div>Take-profit<br><b>${p.take_profit==null?'Posouvaný SL + EMA výstup':f(p.take_profit,6)}</b></div></div>
 <div style="margin-top:12px">Otevřeno: ${historyTime(p.opened_at)}</div>
 <div class="muted" style="margin-top:8px">Cena aktualizována: ${historyTime(p.price_updated_at)}</div>
 ${stale?'<div style="color:#ffd166;margin-top:8px">⚠ Cena není aktuální — čekám na nová data.</div>':''}</div>`;
}
async function refreshBestOf(){
 const box=document.getElementById('bestofPosition');
 try{
  const r=await fetch('/bestof/status',{cache:'no-store',signal:AbortSignal.timeout(10000)});
  if(!r.ok)throw new Error('HTTP '+r.status);
  const d=await r.json(),ts=d.trades||[];
  const wins=ts.filter(t=>Number(t.pnl)>0).length,wr=ts.length?100*wins/ts.length:0;
  const ps=Array.isArray(d.positions)?d.positions:Object.values(d.positions||{});
  document.getElementById('bestofStats').innerHTML=[['Balance',f(d.balance,2)+' USDT'],['Uzavřené obchody',ts.length],['Otevřené obchody',ps.length],['Win rate',f(wr,1)+' %']].map(x=>`<div class="coin"><div class="muted">${x[0]}</div><b>${x[1]}</b></div>`).join('');
  const ema=d.ema4h||{};
  document.getElementById('bestofStrategies').innerHTML=(ema.groups||[]).map(g=>`<div class="coin" style="margin-top:8px;border:1px solid ${g.setup==='EMA_4H'?'#b388ff':'#334155'}"><b>${historyEscape(g.label)}</b><br>Uzavřené: ${g.trades} • Otevřené: ${g.open_positions} • Win rate: ${g.win_rate==null?'—':f(g.win_rate,1)+' %'}<br>Čistý výsledek: <b class="${g.net_pnl>=0?'green':'red'}">${g.net_pnl>=0?'+':''}${f(g.net_pnl,2)} USDT</b></div>`).join('')+
   '<div class="muted" style="margin-top:8px">Statistiky: '+historyEscape(ema.stats_scope||'')+'<br>EMA 4h: PAPER LONG • risk 0,1 % • společně max. '+historyEscape(ema.max_shared_positions??2)+' pozice</div>'+Object.entries(ema.checks||{}).map(([sym,a])=>`<div class="muted" style="margin-top:5px"><b>${historyEscape(sym)}</b>: ${historyEscape(a.reason)}${a.candle_time?'<br>Poslední uzavřená 4h svíčka: '+historyTime(a.candle_time):''}</div>`).join('');
  box.innerHTML=ps.length?ps.map(renderBestOfPosition).join(''):'Žádná otevřená pozice — čekám na obchod';
  document.getElementById('bestofTrades').innerHTML=renderTradeHistory(ts,'USDT');
  const cycle=Date.parse(d.last_cycle_at||'');
  const healthy=Number.isFinite(cycle)&&Date.now()-cycle<90000&&!d.last_error;
  document.getElementById('bestofHealth').innerHTML='Build: '+historyEscape(d.build||'—')+' • '+(healthy?'<span class="green">Běží</span>':'<span class="yellow">Stav není aktuální</span>')+' • '+historyEscape(d.persistence||'—')+'<br>Obnova přehledu každých 5 sekund'+(d.last_error?'<br>'+historyEscape(d.last_error):'');
 }catch(e){
  box.innerHTML='<b class="yellow">⚠ Stav pozic nelze ověřit. Spojení se nezdařilo — čekám na nová data.</b>';
  document.getElementById('bestofHealth').textContent='BEST-OF status nedostupný';
 }
}
"""
    html = html.replace("refresh();setInterval(refresh,10000);", whale_js + fast_js + leadlag_js + tv_js + bestof_js + "refresh();refreshFlyGuard();refreshWhale();refreshFast();refreshLeadLag();refreshTV();refreshBestOf();setInterval(refresh,3000);setInterval(refreshFlyGuard,5000);setInterval(refreshWhale,5000);setInterval(refreshFast,5000);setInterval(refreshLeadLag,5000);setInterval(refreshTV,5000);setInterval(refreshBestOf,5000);")
    html = html.replace('</style>', """
/* Shared trade history: 2026-09-28 */
.history-note{font-size:12px;margin:8px 0}
.trade.history-row{grid-template-columns:1.2fr 1fr 1fr 1fr;align-items:start;gap:8px;padding:12px 0}
.history-row>span{min-width:0;overflow-wrap:anywhere}
.history-time{font-variant-numeric:tabular-nums}
.trade.history-heading{font-size:11px;color:#a7b6c6;padding:8px 0}
@media(max-width:420px){.trade.history-row{font-size:11px;gap:5px}.trade.history-heading{font-size:10px}}
</style>""")
    html = swing_dashboard.enhance(html)
    html = lh_whale_dashboard.enhance(html)
    return HTMLResponse(html, headers={"Cache-Control": "no-store"})


@app.on_event("startup")
async def start_whale_worker():
    global _whale_task, _tv_task, _bestof_task
    whale.init_persistence()
    leadlag.install(base)
    fast.install(base)
    tv.install(base)
    if _whale_task is None or _whale_task.done():
        _whale_task = __import__("asyncio").create_task(whale.bot_loop())
    if not getattr(app.state, "leadlag_task", None) or app.state.leadlag_task.done():
        app.state.leadlag_task = __import__("asyncio").create_task(leadlag.bot_loop())
    if not getattr(app.state, "fast_task", None) or app.state.fast_task.done():
        app.state.fast_task = __import__("asyncio").create_task(fast.bot_loop())
    if _tv_task is None or _tv_task.done():
        _tv_task = __import__("asyncio").create_task(tv.bot_loop())
    if bestof.core.http_client is None:
        bestof.core.http_client = __import__("httpx").AsyncClient(
            timeout=__import__("httpx").Timeout(10.0),
            limits=__import__("httpx").Limits(max_connections=8,max_keepalive_connections=4,keepalive_expiry=30.0),
            headers={"User-Agent":"bestof-paper-24-7/1.0"},
        )
    bestof.core.init_db()
    bestof.core.load_state()
    if _bestof_task is None or _bestof_task.done():
        _bestof_task = __import__("asyncio").create_task(bestof.core.trading_loop())

@app.get("/whale/status")
async def whale_status():
    return JSONResponse(whale.state, headers={"Cache-Control":"no-store"})


@app.get("/leadlag/status")
async def leadlag_status():
    return JSONResponse(leadlag.state, headers={"Cache-Control":"no-store"})


def _fly_trade_metrics(rows):
    rows=list(rows or [])
    wins=[t for t in rows if float(t.get("pnl") or 0)>0]
    losses=[t for t in rows if float(t.get("pnl") or 0)<0]
    pnl=sum(float(t.get("pnl") or 0) for t in rows)
    fees=sum(float(t.get("fees") or 0) for t in rows)
    avg_win=(sum(float(t.get("pnl") or 0) for t in wins)/len(wins)) if wins else 0.0
    avg_loss=(sum(float(t.get("pnl") or 0) for t in losses)/len(losses)) if losses else 0.0
    equity=peak=max_dd=0.0
    for t in reversed(rows):
        equity+=float(t.get("pnl") or 0)
        peak=max(peak,equity)
        max_dd=max(max_dd,peak-equity)
    return {
        "count":len(rows),"wins":len(wins),"losses":len(losses),
        "win_rate":(100.0*len(wins)/len(rows)) if rows else 0.0,
        "net_pnl":pnl,"fees":fees,"avg_win":avg_win,"avg_loss":avg_loss,
        "max_drawdown":max_dd,
    }


@app.get("/fly/status")
async def fly_status():
    rows=list(getattr(base,"trade_history",[]) or [])
    cutoff=datetime.now(timezone.utc)-timedelta(hours=24)
    recent=[]
    for t in rows:
        try:
            raw=t.get("closed_at")
            if raw and datetime.fromisoformat(str(raw).replace("Z","+00:00"))>=cutoff:
                recent.append(t)
        except Exception:
            pass
    return JSONResponse({
        "build":getattr(base,"FLY_LAYER_BUILD",None),
        "mode":"PAPER",
        "status":"running" if getattr(base,"last_cycle_at",None) and not getattr(base,"last_error",None) else "error",
        "last_cycle_at":getattr(base,"last_cycle_at",None),
        "error":getattr(base,"last_error",None),
        "persistence":"postgres" if getattr(base,"DATABASE_URL",None) else "memory",
        "balance":getattr(base,"PAPER_BALANCE",None),
        "open_position":getattr(base,"paper_position",None),
        "all_time":_fly_trade_metrics(rows),
        "last_24h":_fly_trade_metrics(recent),
        "last_trade_at":rows[0].get("closed_at") if rows else None,
    },headers={"Cache-Control":"no-store"})


@app.get("/tv/status")
async def tv_status():
    return JSONResponse(tv.state, headers={"Cache-Control":"no-store"})

def _age_seconds(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return max(0.0, (datetime.now(timezone.utc) - dt).total_seconds())
    except Exception:
        return None


@app.api_route("/combined/health", methods=["GET", "HEAD"])
async def combined_health():
    fly_age = _age_seconds(getattr(base, "last_cycle_at", None))
    whale_age = _age_seconds(whale.state.get("last_scan"))
    leadlag_age = _age_seconds(leadlag.state.get("last_scan"))
    fast_age = _age_seconds(fast.state.get("last_scan"))
    tv_age = _age_seconds(tv.state.get("last_scan"))
    best_age = _age_seconds(getattr(bestof.core,"last_cycle_at",None))
    fly_ok = fly_age is not None and fly_age < 90 and not getattr(base, "last_error", None)
    whale_ok = whale_age is not None and whale_age < 180 and whale.state.get("persistence") == "postgres" and not whale.state.get("error")
    leadlag_ok = leadlag_age is not None and leadlag_age < 90 and leadlag.state.get("persistence") == "postgres" and not leadlag.state.get("error")
    fast_ok = fast_age is not None and fast_age < 90 and fast.state.get("persistence") == "postgres" and not fast.state.get("error")
    tv_ok = tv_age is not None and tv_age < 90 and tv.state.get("persistence") == "postgres" and not tv.state.get("error")
    best_ok = best_age is not None and best_age < 90 and bool(bestof.core.DATABASE_URL) and not bestof.core.last_error
    return JSONResponse({
        "ok": bool(fly_ok and whale_ok and leadlag_ok and fast_ok and tv_ok and best_ok),
        "fly": {
            "healthy": fly_ok,
            "age_seconds": fly_age,
            "last_cycle_at": getattr(base, "last_cycle_at", None),
            "last_error": getattr(base, "last_error", None),
            "persistence": "postgres" if getattr(base, "DATABASE_URL", None) else "memory",
            "recovery": base.recovery_status() if hasattr(base, "recovery_status") else {},
            "balance": getattr(base, "PAPER_BALANCE", None),
            "open_position": getattr(base, "paper_position", None),
            "stats": base.stats() if hasattr(base, "stats") else {},
            "last_trade_at": (base.trade_history[0].get("closed_at") if getattr(base, "trade_history", None) else None),
        },
        "whale": {
            "healthy": whale_ok,
            "age_seconds": whale_age,
            "status": whale.state.get("status"),
            "error": whale.state.get("error"),
            "last_scan": whale.state.get("last_scan"),
            "persistence": whale.state.get("persistence"),
            "persistence_error": whale.state.get("persistence_error"),
            "balance": whale.state.get("balance"),
            "open_position": whale.state.get("open_position"),
            "open_positions": whale.state.get("open_positions", []),
        },
        "news": news_signal.cached_all(),
        "fast": {
            "healthy": fast_ok,
            "age_seconds": fast_age,
            "status": fast.state.get("status"),
            "error": fast.state.get("error"),
            "last_scan": fast.state.get("last_scan"),
            "persistence": fast.state.get("persistence"),
            "persistence_error": fast.state.get("persistence_error"),
            "balance": fast.state.get("balance"),
            "equity": fast.state.get("equity"),
            "open_position": fast.state.get("open_position"),
            "trades": len(fast.state.get("trades", [])),
        },
        "tv_consensus": {
            "healthy": tv_ok,
            "age_seconds": tv_age,
            "status": tv.state.get("status"),
            "error": tv.state.get("error"),
            "last_scan": tv.state.get("last_scan"),
            "persistence": tv.state.get("persistence"),
            "persistence_error": tv.state.get("persistence_error"),
            "balance": tv.state.get("balance"),
            "equity": tv.state.get("equity"),
            "open_position": tv.state.get("open_position"),
            "analysis": tv.state.get("analysis"),
            "trades": len(tv.state.get("trades", [])),
        },
        "bestof": {"healthy":best_ok,"age_seconds":best_age,"last_cycle_at":bestof.core.last_cycle_at,"last_error":bestof.core.last_error,"persistence":"postgres" if bestof.core.DATABASE_URL else "memory","balance":bestof.core.PAPER_BALANCE,"open_positions":bestof.core.positions,"trades":len(bestof.core.trade_history)},
        "leadlag": {
            "healthy": leadlag_ok,
            "age_seconds": leadlag_age,
            "status": leadlag.state.get("status"),
            "error": leadlag.state.get("error"),
            "last_scan": leadlag.state.get("last_scan"),
            "persistence": leadlag.state.get("persistence"),
            "persistence_error": leadlag.state.get("persistence_error"),
            "balance": leadlag.state.get("balance"),
            "open_position": leadlag.state.get("open_position"),
        }
    }, headers={"Cache-Control":"no-store"})



@app.get("/news/status")
async def news_status(symbol: str = "ALL"):
    try:
        if symbol.upper() == "ALL":
            await news_signal.get_news("XRP")
            data = news_signal.cached_all()
        else:
            data = await news_signal.get_news(symbol)
    except ValueError:
        return JSONResponse({"error": "Supported assets: XRP, BTC, ETH, SOL"}, status_code=400)
    return JSONResponse(data, headers={"Cache-Control":"no-store"})


@app.get("/fast/status")
async def fast_status():
    return JSONResponse(fast.state, headers={"Cache-Control":"no-store"})



def _bestof_position_snapshot():
    """Read cached execution quotes without changing positions or placing orders."""
    import math
    rows = {}
    for symbol, position in list(bestof.core.positions.items()):
        p = dict(position)
        quote = dict(bestof.core.price_cache.get(symbol) or {})
        raw = quote.get("price")
        try:
            price = float(raw)
            if not math.isfinite(price) or price <= 0:
                price = None
        except (TypeError, ValueError):
            price = None
        updated = quote.get("updated_at")
        age = _age_seconds(updated)
        p.update(current_price=price, price_updated_at=updated,
                 price_stale=price is None or age is None or age > 30,
                 unrealized_net_pnl=None, unrealized_net_pct=None)
        if price is not None:
            entry, qty = float(p["entry_price"]), float(p["qty"])
            net = (bestof.ema4h.net_per_unit(p, price) if p.get("setup")==bestof.ema4h.SETUP else bestof.core.estimated_net_per_unit(p["side"], entry, price)) * qty
            p["unrealized_net_pnl"] = net
            p["unrealized_net_pct"] = net / (entry * qty) * 100 if entry * qty > 0 else None
        rows[symbol] = p
    return rows


@app.get("/bestof/status")
async def combined_bestof_status():
    return JSONResponse({
        "mode":"PAPER","build":bestof.ema4h.BUILD,
        "ema4h":bestof.ema4h.summary(bestof.core),
        "allowed":[{"symbol":s,"setup":u,"side":d} for s,u,d in sorted(bestof.ALLOWED)]+[{"symbol":s,"setup":bestof.ema4h.SETUP,"side":"LONG"} for s in bestof.core.SYMBOLS],
        "balance":bestof.core.PAPER_BALANCE,
        "positions":_bestof_position_snapshot(),
        "trades":bestof.core.trade_history[:50],
        "last_cycle_at":bestof.core.last_cycle_at,
        "last_error":bestof.core.last_error,
        "persistence":"postgres" if bestof.core.DATABASE_URL else "memory"
    },headers={"Cache-Control":"no-store"})


@app.get("/liquidity-hunter/status")
async def liquidity_hunter_status():
    """Same-origin proxy for the isolated Liquidity Hunter PAPER service."""
    url = "https://xrp-liquidity-hunter-24-7.onrender.com/liquidity/status"
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            r = await client.get(url, headers={"User-Agent":"xrp-shared-dashboard/1.0"})
            r.raise_for_status()
            return JSONResponse(r.json(), headers={"Cache-Control":"no-store"})
    except Exception as e:
        return JSONResponse({"bot":"LIQUIDITY HUNTER","mode":"PAPER","running":False,
                             "error":str(e)}, status_code=503,
                            headers={"Cache-Control":"no-store"})

# Independent PAPER portfolios; deliberately separate from BEST balances and risk hooks.
swing_paper.install(app, bestof.core)
lh_whale.install(app, bestof.core)
lh_storage.install(app, bestof.core)
