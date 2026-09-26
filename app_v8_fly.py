from fastapi.responses import HTMLResponse, JSONResponse
# deploy marker 2026-09-26 quality fixes
from datetime import datetime, timezone, timedelta
import app_v8 as base
import app_blue_whale_mirror as whale
import lead_lag_scalper as leadlag
import fast_scalper as fast
import news_signal
import tv_consensus_scalper as tv
from v8_fly_layer import install

install(base)
app = base.app
_original_analyze = base.analyze
_original_dashboard = base.dashboard
_whale_task = None
_tv_task = None

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
    html = html.replace('<div class="card"><h2>📡 Trhy</h2>', fly_guard_card + '<div class="card"><h2>📡 Trhy</h2>')
    whale_card = """
<div class="card">
  <h2>🐋 BLUE WHALE · FIB + VWAP</h2>
  <div class="muted">PAPER • Fibonacci 0,618–0,786 + návrat k VWAP • BTC / ETH / SOL / XRP</div>
  <div id="whaleSignals" class="coin muted" style="margin-top:10px"></div>
  <div id="whaleStats" class="grid"></div>
  <div id="whalePosition" class="coin muted" style="margin-top:10px">Načítám…</div>
  <div id="whaleTrades" style="display:none;margin-top:10px"></div>
  <div id="whaleHealth" class="muted" style="margin-top:10px">Načítám…</div>
</div>
"""
    leadlag_card = """
<div class="card">
  <h2>🔗 XRP LEAD-LAG SCALPER</h2>
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
<div class="card">
  <h2>📊 TV CONSENSUS XRP</h2>
  <div class="muted" style="margin-bottom:10px">MA + MACD/Momentum + RSI/Stoch/CCI + ADX • 15m trend • PAPER</div>
  <div id="tvPosition" role="status" aria-live="polite" style="padding:18px;border:2px solid #566475;border-radius:14px;margin-bottom:14px">Načítám stav pozice…</div>
  <div id="tvStats" class="grid"></div>
  <div id="tvSignal" class="coin muted" style="margin-top:10px">Načítám…</div>
  <div id="tvTrades" style="margin-top:10px"></div>
</div>
"""
    html = html.replace('<div class="card muted" id="health">', whale_card + leadlag_card + tv_card + '<div class="card muted" id="health">')
    whale_js = """
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
  document.getElementById('whaleTrades').innerHTML=ts.slice().reverse().slice(0,20).map(t=>`<div class="trade"><span><b>${t.symbol||'BTCUSDT'}</b> ${t.side}</span><span>${f(t.entry,6)} → ${f(t.exit,6)}</span><span>${t.reason||'—'} · ${t.strategy||'Původní signál'} · ${t.closed_at?new Date(t.closed_at).toLocaleString('cs-CZ'):''}</span><span class="${Number(t.net_pnl)>=0?'green':'red'}">${Number(t.net_pnl)>=0?'+':''}${f(t.net_pnl,2)} USD</span></div>`).join('')||'<div class="coin muted">Zatím žádné uzavřené obchody.</div>';
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
   `<b class="${p?'green':'yellow'}">${tradeState}</b> • poslední scan ${scanText}<br>Signal <b>${a.signal||'WAIT'}</b> • BTC ${f(Number(a.btc_return||0)*100,3)} % • ETH ${f(Number(a.eth_return||0)*100,3)} % • XRP ${f(Number(a.xrp_return||0)*100,3)} % • lag ${f(Number(a.lag_return||0)*100,3)} % • book ${f(a.book_imbalance,3)}<br><span class="muted">${blockerText}</span>`;
  document.getElementById('leadlagTrades').innerHTML=ts.slice().reverse().slice(0,8).map(t=>
    `<div class="trade"><span><b>${t.symbol||'XRPUSDC'}</b> ${t.side}</span><span>${f(t.entry,6)} → ${f(t.exit,6)}</span><span>${t.reason||'—'}</span><span class="${Number(t.net_pnl)>=0?'green':'red'}">${Number(t.net_pnl)>=0?'+':''}${f(t.net_pnl,2)} USDC</span><span>${t.closed_at?new Date(t.closed_at).toLocaleString('cs-CZ'):'—'}</span></div>`
  ).join('') || '<div class="coin muted">Zatím žádné uzavřené obchody.</div>';
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
  document.getElementById('tvTrades').innerHTML=ts.slice().reverse().slice(0,20).map(t=>`<div class="trade"><span><b>${t.side}</b><br>${closedTime(t.closed_at)}</span><span>${f(t.entry,6)} → ${f(t.exit,6)}</span><span>${t.reason||'—'}<br>${t.strategy_build?'V3':'V2'}</span><span class="${Number(t.net_pnl)>=0?'green':'red'}">${Number(t.net_pnl)>=0?'+':''}${f(t.net_pnl,2)} USDC</span></div>`).join('')||'<div class="muted">Zatím žádné uzavřené obchody.</div>';
 }catch(e){
  document.getElementById('tvPosition').innerHTML='<b style="font-size:22px;color:#ffd166">⚠ STAV POZICE NELZE OVĚŘIT</b><div style="margin-top:10px">Spojení se nezdařilo. Čekám na nová data.</div>';
  document.getElementById('tvPosition').style.borderColor='#ffd166';
  document.getElementById('tvSignal').textContent='TV Consensus error: '+e;
 }
}
"""
    html = html.replace("refresh();setInterval(refresh,10000);", whale_js + leadlag_js + tv_js + "refresh();refreshFlyGuard();refreshWhale();refreshLeadLag();refreshTV();setInterval(refresh,3000);setInterval(refreshFlyGuard,5000);setInterval(refreshWhale,5000);setInterval(refreshLeadLag,5000);setInterval(refreshTV,5000);")
    return HTMLResponse(html, headers={"Cache-Control": "no-store"})


@app.on_event("startup")
async def start_whale_worker():
    global _whale_task, _tv_task
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


@app.get("/combined/health")
async def combined_health():
    fly_age = _age_seconds(getattr(base, "last_cycle_at", None))
    whale_age = _age_seconds(whale.state.get("last_scan"))
    leadlag_age = _age_seconds(leadlag.state.get("last_scan"))
    fast_age = _age_seconds(fast.state.get("last_scan"))
    tv_age = _age_seconds(tv.state.get("last_scan"))
    fly_ok = fly_age is not None and fly_age < 90 and not getattr(base, "last_error", None)
    whale_ok = whale_age is not None and whale_age < 180 and whale.state.get("persistence") == "postgres" and not whale.state.get("error")
    leadlag_ok = leadlag_age is not None and leadlag_age < 90 and leadlag.state.get("persistence") == "postgres" and not leadlag.state.get("error")
    fast_ok = fast_age is not None and fast_age < 90 and fast.state.get("persistence") == "postgres" and not fast.state.get("error")
    tv_ok = tv_age is not None and tv_age < 90 and tv.state.get("persistence") == "postgres" and not tv.state.get("error")
    return JSONResponse({
        "ok": bool(fly_ok and whale_ok and leadlag_ok and fast_ok and tv_ok),
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

