"""Dashboard cards for the two isolated PAPER portfolios."""
CARD = '''
<div class="card" id="swingPaper" style="border:2px solid #64d9b8;background:rgba(100,217,184,.03)">
<h2>📈 AROON + SUPERTREND · PAPER</h2>
<div class="muted">Dva samostatné virtuální účty · každý začíná s 10 000 USDT · riziko 0,5 % na obchod · max. 2 pozice na strategii</div>
<div id="swingAccounts">Načítám nové strategie…</div>
</div>
'''
SCRIPT = '''
<script>
async function refreshSwingPaper(){
 const root=document.getElementById('swingAccounts');
 const num=(v,n=2)=>v==null?'—':Number(v).toLocaleString('cs-CZ',{maximumFractionDigits:n,minimumFractionDigits:n});
 const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const when=v=>v?new Date(v).toLocaleString('cs-CZ',{timeZone:'Europe/Prague'}):'—';
 const pnl=v=>`<b class="${v>=0?'green':'red'}">${v==null?'—':(v>=0?'+':'')+num(v)} USDT</b>`;
 try{
  const response=await fetch('/swing/status',{cache:'no-store',signal:AbortSignal.timeout(10000)});
  if(!response.ok)throw new Error('HTTP '+response.status);
  const data=await response.json();
  const openDetails=Array.from(root.querySelectorAll('details'),d=>d.open);
  root.innerHTML=data.accounts.map(a=>`<section style="border:1px solid #465666;border-radius:14px;padding:16px;margin-top:16px">
  <h3>${esc(a.label)}</h3><div>PAPER · ${esc(a.mode==='PAPER'?a.id==='aroon_1h_4h'?'LONG':'LONG / SHORT':a.mode)} · ${a.healthy?'🟢 Běží':'🟠 Čekám na aktuální data'}</div>
  <div class="grid" style="margin-top:12px">
  <div class="coin">Zůstatek<br><b>${num(a.balance)} USDT</b></div><div class="coin">Hodnota účtu včetně pozic<br><b>${num(a.equity)} USDT</b></div>
  <div class="coin">Čistý realizovaný výsledek<br>${pnl(a.net_pnl)}</div><div class="coin">Největší propad<br><b>${num(a.max_drawdown_pct)} %</b></div>
  <div class="coin">Uzavřené / otevřené<br><b>${a.trades_count} / ${a.positions.length}</b></div><div class="coin">Win rate<br><b>${num(a.win_rate)} %</b></div></div>
  <div style="margin-top:12px">${a.positions.length?a.positions.map(p=>`<div class="coin" style="margin-top:8px"><b>${esc(p.symbol)} ${esc(p.side)}</b><br>Průběžný čistý P/L: ${pnl(p.unrealized_net_pnl)}${p.price_stale?' · ⚠ cena není aktuální':''}<br>Vstup ${num(p.entry_price,6)} · Cena ${num(p.current_price,6)}<br>Stop-loss ${num(p.stop_loss,6)} · výstup signálem nebo posouvaným SL<br>Otevřeno ${when(p.opened_at)}</div>`).join(''):'⏳ Žádná otevřená pozice — čekám na nový signál'}</div>
  <details open style="margin-top:12px"><summary>Historie obchodů (${a.trades_count})</summary>${a.trades.length?a.trades.map(t=>`<div class="coin" style="margin-top:8px"><b>${esc(t.symbol)} ${esc(t.side)}</b> · ${pnl(t.pnl)}<br>${when(t.closed_at)}<br>${num(t.entry_price,6)} → ${num(t.exit_price,6)}<br>${esc(t.reason)}<br>Poplatky ${num(t.fees)} · náklad SHORT ${num(t.carry)} USDT</div>`).join(''):'Zatím žádné uzavřené obchody.'}</details>
  <details style="margin-top:12px"><summary>Kontrola signálů</summary>${Object.entries(a.checks).map(([sym,c])=>`<div style="margin-top:8px"><b>${esc(sym)}</b> · poslední uzavřená svíčka ${when(c.candle)}<br>${c.side?'Signál na poslední svíčce; vstup podléhá času a limitům':'Čekám na nový signál'}${c.filter_ok===false?' · 4h filtr nepovoluje LONG':''}</div>`).join('')}</details>
  ${a.last_error?'<p class="red">'+esc(a.last_error)+'</p>':''}${Object.entries(a.errors).map(([sym,err])=>'<p class="yellow">'+esc(sym)+': '+esc(err)+'</p>').join('')}
  <div class="muted" style="font-size:12px;margin-top:12px">Poslední kontrola: ${when(a.last_cycle_at)}<br>Spuštěno: ${when(a.activated_at)} · Ukládání: ${esc(a.persistence)}<br>Výsledky zahrnují modelované poplatky a skluz. Historie ukazuje posledních 50 obchodů; souhrny jsou za celé období.</div></section>`).join('');
  root.querySelectorAll('details').forEach((d,i)=>{d.open=openDetails[i] ?? d.open});
 }catch(e){root.innerHTML='<p class="yellow">Stav nových strategií nelze ověřit. Čekám na obnovení spojení.</p>';}
}
refreshSwingPaper();setInterval(refreshSwingPaper,5000);
</script>
'''

def enhance(html):
    return html.replace('<div class="card muted" id="health">',CARD+'<div class="card muted" id="health">').replace('</body>',SCRIPT+'</body>')
