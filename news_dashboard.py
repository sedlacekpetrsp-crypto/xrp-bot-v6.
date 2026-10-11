"""Visible independent NEWS_LONG account and feed freshness."""
CARD = '''
<div class="card" style="border:2px solid #f9cb65;background:rgba(249,203,101,.03)">
<h2>📰 NEWS LONG · XRP · PAPER</h2>
<div class="muted">Pozitivní zprávy + potvrzení trhu · vlastní simulovaný účet · riziko 0,14 % · čisté R:R 1,6:1</div>
<div id="newsPaper">Načítám zprávovou strategii…</div></div>
'''
SCRIPT = '''<script>
async function refreshNewsPaper(){
 const root=document.getElementById('newsPaper');
 const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const num=v=>v==null?'—':Number(v).toLocaleString('cs-CZ',{maximumFractionDigits:4});
 const when=v=>v?new Date(v).toLocaleString('cs-CZ',{timeZone:'Europe/Prague'}):'—';
 try{
  const r=await fetch('/news-paper/status',{cache:'no-store',signal:AbortSignal.timeout(10000)});
  if(!r.ok)throw Error(r.status);const d=await r.json(),n=d.news||{},p=d.position;
  root.innerHTML='<p><b>'+ (d.healthy?'🟢 Běží':'🟠 Stav vyžaduje kontrolu')+'</b> · '+esc(d.reason)+'</p>'+
   '<div class="grid">'+[['Zůstatek',num(d.balance)+' USDC'],['Čistý výsledek',num(d.net_pnl)+' USDC'],['Uzavřené / otevřené',d.trades_count+' / '+(p?1:0)]].map(x=>'<div class="coin">'+x[0]+'<br><b>'+x[1]+'</b></div>').join('')+'</div>'+
   '<p>Zprávy: <b>'+esc(n.status)+'</b> · poslední kontrola '+when(n.checked_at)+' · dostupné zdroje '+num(n.active_sources)+' / 3<br>Skóre XRP '+num(n.score)+' · '+(n.bullish?'pozitivní signál':n.bearish?'negativní signál':'čekám na zprávu')+'</p>'+
   (n.headlines||[]).map(h=>'<div class="coin">'+esc(h.title)+'<br><small>'+esc(h.source)+' · '+when(h.seen_at)+'</small></div>').join('')+
   (p?'<div class="coin"><b class="green">XRP LONG</b> · průběžný čistý P/L '+num(p.unrealized_net_pnl)+' USDC<br>Vstup '+num(p.entry_price)+' · cena '+num(p.current_price)+' · SL '+num(p.stop_loss)+' · TP '+num(p.take_profit)+'<br>Otevřeno '+when(p.opened_at)+'</div>':'<p>Žádná otevřená pozice</p>')+
   '<details><summary>Historie zprávových obchodů ('+d.trades_count+')</summary>'+(d.trades.length?d.trades.map(t=>'<div class="coin">XRP LONG · '+num(t.pnl)+' USDC<br>'+when(t.closed_at)+' · '+esc(t.reason)+'<br>'+num(t.entry_price)+' → '+num(t.exit_price)+' · poplatky '+num(t.fees)+' USDC</div>').join(''):'Zatím bez uzavřených obchodů.')+'</details>'+
   [d.last_error,d.data_error,n.upstream_error].filter(Boolean).map(e=>'<p class="yellow">'+esc(e)+'</p>').join('')+
   '<div class="muted">Poslední cyklus '+when(d.last_cycle_at)+' · ukládání '+esc(d.persistence)+'</div>';
 }catch(e){root.innerHTML='<p class="yellow">Stav NEWS LONG není dostupný. Čekám na obnovení spojení.</p>';}
}
refreshNewsPaper();setInterval(refreshNewsPaper,5000);
</script>'''


def enhance(html):
    return html.replace('<div class="card muted" id="health">',CARD+'<div class="card muted" id="health">',1).replace('</body>',SCRIPT+'</body>')
