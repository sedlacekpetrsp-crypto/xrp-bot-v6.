from fastapi.responses import HTMLResponse
from app_v8 import app

# Replace the original root dashboard with a more robust mobile dashboard.
app.router.routes = [r for r in app.router.routes if not (getattr(r, 'path', None) == '/' and 'GET' in getattr(r, 'methods', set()))]

@app.get('/', response_class=HTMLResponse)
async def dashboard_v8():
    return '''
<!doctype html><html lang="cs"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>V8</title>
<style>
body{background:#0b1118;color:#fff;font-family:Arial,sans-serif;margin:0;padding:16px}.wrap{max-width:900px;margin:auto}.card{background:#151c24;border-radius:22px;padding:20px;margin:14px 0}.row{display:flex;justify-content:space-between;gap:12px;margin:9px 0}.green{color:#5ee08a}.red{color:#ff6b6b}.yellow{color:#ffd166}.muted{opacity:.75}.market,.trade{border-top:1px solid #29313b;padding-top:12px;margin-top:12px}.err{color:#ff8a8a;white-space:pre-wrap}</style></head>
<body><div class="wrap">
<div class="card"><h1>🧠 V8 ADAPTIVE LIQUIDITY SCALPER</h1><div>PAPER · XRP/USDC · ETH/USDC · SOL/USDC</div><div id="best" class="yellow">Načítám…</div><div id="error" class="err"></div></div>
<div class="card"><h2>💧 Trhy</h2><div id="markets">Načítám…</div></div>
<div class="card"><h2>📋 Otevřený obchod</h2><div id="position">Načítám…</div></div>
<div class="card"><h2>💰 Účet</h2><div id="account">Načítám…</div></div>
<div class="card"><h2>📊 Statistiky</h2><div id="stats">Načítám…</div></div>
<div class="card"><h2>📜 Historie</h2><div id="history">Načítám…</div></div>
</div>
<script>
const $=id=>document.getElementById(id);
const n=(v,d=2)=>Number.isFinite(Number(v))?Number(v).toFixed(d):'---';
const pretty=s=>String(s||'').replace('USDC','/USDC').replace('USDT','/USDT');
const cls=s=>s==='LONG'?'green':s==='SHORT'?'red':'yellow';
async function refresh(){
  try{
    const resp=await fetch('/analyze',{cache:'no-store'});
    if(!resp.ok) throw new Error('HTTP '+resp.status);
    const d=await resp.json();
    $('error').innerText='';
    const b=d.best_signal;
    $('best').innerText=b?`${pretty(b.symbol)} · ${b.signal} · ${b.setup||'---'} · score ${b.score||0}/8`:'WAIT';
    const prices=d.prices||{};
    const aa=d.analyses||[];
    $('markets').innerHTML=aa.length?aa.map(a=>`<div class="market">
      <div class="row"><b>${pretty(a.symbol)}</b><span>${n(prices[a.symbol],String(a.symbol).startsWith('XRP')?5:2)} USDC</span></div>
      <div class="row"><span>Signál</span><b class="${cls(a.signal)}">${a.signal||'WAIT'}</b></div>
      <div class="row"><span>Raw signal</span><span>${a.raw_signal||'WAIT'}</span></div>
      <div class="row"><span>Setup / režim</span><span>${a.setup||'---'} / ${a.regime||'---'}</span></div>
      <div class="row"><span>LONG / SHORT score</span><span>${a.long_score||0}/8 · ${a.short_score||0}/8</span></div>
      <div class="row"><span>RSI / ADX5</span><span>${n(a.rsi,1)} / ${n(a.adx5,1)}</span></div>
      <div class="row"><span>Volume</span><span>${n(a.volume_ratio,2)}×</span></div>
      <div class="row"><span>Order book</span><span>${n(a.book_imbalance,3)} · stabilita ${n(a.book_spread,3)}</span></div>
      <div class="row"><span>Liquidity high / low</span><span>${n(a.liquidity_high,5)} / ${n(a.liquidity_low,5)}</span></div>
      <div class="row"><span>Sweep high / low</span><span>${a.sweep_high?'ANO':'ne'} / ${a.sweep_low?'ANO':'ne'}</span></div>
      <div class="muted">${a.reason||''}</div></div>`).join(''):'Žádná data z trhů';
    const p=d.position;
    $('position').innerHTML=p?`<div class="row"><span>${pretty(p.symbol)} ${p.side} ${p.setup}</span><b>${n(p.entry_price,5)}</b></div><div class="row"><span>SL / TP</span><span>${n(p.stop_loss,5)} / ${n(p.take_profit,5)}</span></div><div class="row"><span>MAE / MFE</span><span>${n(p.mae_r,2)}R / ${n(p.mfe_r,2)}R</span></div>`:'Zatím žádný otevřený obchod';
    $('account').innerHTML=`<div class="row"><span>Balance</span><b>${n(d.paper_balance)} USDC</b></div><div class="row"><span>Equity</span><b>${n(d.equity)} USDC</b></div><div class="row"><span>Otevřený P&L</span><b>${n(d.unrealized_pnl)} USDC</b></div>`;
    const s=d.stats||{};
    $('stats').innerHTML=`<div class="row"><span>Obchody</span><span>${s.count||0}</span></div><div class="row"><span>WIN</span><span>${s.wins||0}</span></div><div class="row"><span>Win rate</span><span>${n(s.win_rate,1)} %</span></div><div class="row"><span>Čistý P&L</span><span>${n(s.total_pnl)} USDC</span></div><div class="row"><span>Poplatky</span><span>${n(s.fees)} USDC</span></div><div class="row"><span>Profit factor</span><span>${n(s.profit_factor,2)}</span></div>`;
    const h=d.trade_history||[];
    $('history').innerHTML=h.length?h.map(t=>`<div class="trade"><div class="row"><span>${pretty(t.symbol)} · ${t.side} · ${t.setup}</span><b>${n(t.pnl)} USDC</b></div><div class="muted">MAE ${n(t.mae_r,2)}R · MFE ${n(t.mfe_r,2)}R · ${t.reason||''}</div></div>`).join(''):'Zatím žádné uzavřené obchody';
  }catch(e){
    $('error').innerText='Dashboard chyba: '+e.message;
    $('markets').innerText='Data se nepodařilo načíst.';
    $('account').innerText='Data se nepodařilo načíst.';
    $('stats').innerText='Data se nepodařilo načíst.';
    $('history').innerText='Data se nepodařilo načíst.';
  }
}
refresh();setInterval(refresh,5000);
</script></body></html>
'''
