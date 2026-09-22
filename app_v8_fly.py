from fastapi.responses import HTMLResponse, JSONResponse
from datetime import datetime, timezone
import app_v8 as base
import app_blue_whale_mirror as whale
import lead_lag_scalper as leadlag
import fast_scalper as fast
import news_signal
from v8_fly_layer import install

install(base)
app = base.app
_original_analyze = base.analyze
_original_dashboard = base.dashboard
_whale_task = None

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
  <h2>🐋 BLUE WHALE</h2>
  <div id="whaleStats" class="grid"></div>
  <div id="whalePosition" class="coin muted" style="margin-top:10px">Načítám…</div>
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
  <div id="leadlagTrades" style="margin-top:6px"></div>
  <div id="leadlagHealth" class="muted" style="margin-top:10px">Načítám…</div>
</div>
"""
    html = html.replace('<div class="card muted" id="health">', whale_card + leadlag_card + '<div class="card muted" id="health">')
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
  const unreal=Number(w.equity||0)-Number(w.balance||0);
  const unrealText=`<span class="${unreal>=0?'green':'red'}">${unreal>=0?'+':''}${f(unreal,2)} USD</span>`;
  const realizedText=`<span class="${pnl>=0?'green':'red'}">${pnl>=0?'+':''}${f(pnl,2)} USD</span>`;
  document.getElementById('whaleStats').innerHTML=[
   ['Balance',f(w.balance,2)+' USD'],['Equity',f(w.equity,2)+' USD'],
   ['Uzavřené obchody',ts.length],['Otevřené obchody',ps.length|| (p?1:0)],
   ['Win rate',f(wr,1)+' %'],['Realizované PnL',realizedText],
   ['Nerealizované PnL',unrealText],['Status',w.status||'—'],
   ['Obchodní stav',p?'OBCHOD OTEVŘEN':'⏳ ČEKÁM NA OBCHOD']
  ].map(x=>`<div class="coin"><div class="muted">${x[0]}</div><b>${x[1]}</b></div>`).join('');
  document.getElementById('whalePosition').innerHTML=ps.length
   ? ps.map((p,i)=>`<div style="${i?'margin-top:10px;padding-top:10px;border-top:1px solid #29343e':''}"><b>#${i+1} BTCUSDT ${p.side}</b> • entry ${f(p.entry,2)} • SL ${f(p.stop,2)} • TP ${f(p.tp,2)} • risk ${f(p.risk_dollars,2)} USD</div>`).join('')+`<div style="margin-top:8px">Celkové uPnL <b class="${unreal>=0?'green':'red'}">${unreal>=0?'+':''}${f(unreal,2)} USD</b></div>`
   : (p
      ? `<b>BTCUSDT ${p.side}</b> • entry ${f(p.entry,2)} • SL ${f(p.stop,2)} • TP ${f(p.tp,2)} • risk ${f(p.risk_dollars,2)} USD • uPnL ${unreal>=0?'+':''}${f(unreal,2)} USD`
      : '<b class="yellow">⏳ ČEKÁM NA OBCHOD</b><div style="margin-top:6px">Žádná otevřená Whale pozice.</div>');
  document.getElementById('whaleHealth').textContent=
   `Scan: ${w.last_scan||'—'} • ukládání: ${w.persistence||'memory'} • chyba: ${w.error||w.persistence_error||'žádná'}`;
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
  ].map(x=>`<div class="coin"><div class="muted">${x[0]}</div><b>${x[1]}</b></div>`).join('');
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
    html = html.replace("refresh();setInterval(refresh,10000);", whale_js + leadlag_js + "refresh();refreshFlyGuard();refreshWhale();refreshLeadLag();setInterval(refresh,3000);setInterval(refreshFlyGuard,5000);setInterval(refreshWhale,5000);setInterval(refreshLeadLag,5000);")
    return HTMLResponse(html, headers={"Cache-Control": "no-store"})


@app.on_event("startup")
async def start_whale_worker():
    global _whale_task
    whale.init_persistence()
    leadlag.install(base)
    fast.install(base)
    if _whale_task is None or _whale_task.done():
        _whale_task = __import__("asyncio").create_task(whale.bot_loop())
    if not getattr(app.state, "leadlag_task", None) or app.state.leadlag_task.done():
        app.state.leadlag_task = __import__("asyncio").create_task(leadlag.bot_loop())
    if not getattr(app.state, "fast_task", None) or app.state.fast_task.done():
        app.state.fast_task = __import__("asyncio").create_task(fast.bot_loop())

@app.get("/whale/status")
async def whale_status():
    return JSONResponse(whale.state, headers={"Cache-Control":"no-store"})


@app.get("/leadlag/status")
async def leadlag_status():
    return JSONResponse(leadlag.state, headers={"Cache-Control":"no-store"})

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
    fly_ok = fly_age is not None and fly_age < 90 and not getattr(base, "last_error", None)
    whale_ok = whale_age is not None and whale_age < 180 and whale.state.get("persistence") == "postgres" and not whale.state.get("error")
    leadlag_ok = leadlag_age is not None and leadlag_age < 90 and leadlag.state.get("persistence") == "postgres" and not leadlag.state.get("error")
    fast_ok = fast_age is not None and fast_age < 90 and fast.state.get("persistence") == "postgres" and not fast.state.get("error")
    return JSONResponse({
        "ok": bool(fly_ok and whale_ok and leadlag_ok and fast_ok),
        "fly": {
            "healthy": fly_ok,
            "age_seconds": fly_age,
            "last_cycle_at": getattr(base, "last_cycle_at", None),
            "last_error": getattr(base, "last_error", None),
            "persistence": "postgres" if getattr(base, "DATABASE_URL", None) else "memory",
            "recovery": base.recovery_status() if hasattr(base, "recovery_status") else {},
            "balance": getattr(base, "PAPER_BALANCE", None),
            "open_position": getattr(base, "paper_position", None),
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
        "news": news_signal.cached_state(),
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
async def news_status():
    data = await news_signal.get_xrp_news()
    return JSONResponse(data, headers={"Cache-Control":"no-store"})


@app.get("/fast/status")
async def fast_status():
    return JSONResponse(fast.state, headers={"Cache-Control":"no-store"})
