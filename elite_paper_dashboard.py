"""Read-only forward-test card; historical backtest gains are never displayed."""
CARD='''<div class="card" id="elitePaper"><h2>ELITE V18 + V56 · experimentální PAPER</h2>
<p>Dva oddělené virtuální účty po 10 000 USDT. Riziko 0,5 % na obchod.
Ziskovost není ověřená; zde jsou pouze nové výsledky od spuštění.</p>
<div id="elitePaperState">Načítám stav…</div>
<p><a href="/elite-paper/status">Podrobný stav</a></p></div>'''
SCRIPT='''<script>
async function refreshElitePaper(){
 const root=document.getElementById('elitePaperState'); if(!root)return;
 const n=v=>Number(v).toLocaleString('cs-CZ',{maximumFractionDigits:2});
 try{
  const r=await fetch('/elite-paper/status',{cache:'no-store',signal:AbortSignal.timeout(8000)});
  if(!r.ok)throw Error('HTTP'); const d=await r.json(); root.replaceChildren();
  const status=document.createElement('p');
  status.textContent=(d.healthy?'Běží · ':'Čeká / stav není aktuální · ')+(d.last_saved_at?new Date(d.last_saved_at).toLocaleString('cs-CZ',{timeZone:'Europe/Prague'}):'Bez potvrzeného zápisu');root.append(status);
  for(const [name,a] of Object.entries(d.accounts||{})){
   const row=document.createElement('p');
   row.textContent=name+' · hodnota účtu '+n(a.equity)+' USDT · čistý uzavřený výsledek '+n(a.realized_pnl)+' USDT · propad '+n(a.drawdown_pct)+' % · uzavřeno '+a.trades+' · '+(a.position?'otevřená LONG pozice':'čeká na nový signál');root.append(row);
  }
 }catch(e){root.textContent='Stav se nepodařilo načíst.';}
}
refreshElitePaper();setInterval(refreshElitePaper,20000);
</script>'''


def enhance(html):
    return html.replace('<div class="card muted" id="health">',CARD+'<div class="card muted" id="health">').replace('</body>',SCRIPT+'</body>')
