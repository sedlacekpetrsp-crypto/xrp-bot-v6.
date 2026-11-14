CARD = '''<div class="card" style="border:2px solid #66e0c1;background:rgba(102,224,193,.03)">
<h2>🎯 LIQUIDITY HUNTER · XRP · 24/7</h2>
<div class="muted">PAPER · sweep + reclaim · 5m / 15m / 1h · OI + Top Traders + Taker · risk max. 0,5 % · SL ≥ 2× ATR · čisté R:R 2,5:1</div>
<div id="lhWhaleStatus" style="margin-top:12px">Načítám Liquidity Hunter…</div></div>'''
SCRIPT = '''<script>
async function refreshLHWhale(){
 const root=document.getElementById('lhWhaleStatus');if(!root)return;
 const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const num=(v,n=2)=>v==null?'—':Number(v).toLocaleString('cs-CZ',{minimumFractionDigits:n,maximumFractionDigits:n});
 const pnl=v=>'<b class="'+(v==null?'muted':v>=0?'green':'red')+'">'+(v==null?'—':(v>=0?'+':'')+num(v))+' USDT</b>';
 const when=v=>v?new Date(v).toLocaleString('cs-CZ',{timeZone:'Europe/Prague'}):'—';
 try{
  const r=await fetch('/lh-whale/status',{cache:'no-store',signal:AbortSignal.timeout(10000)});if(!r.ok)throw Error(r.status);
  const d=await r.json(),a=d.analysis||{},f=a.futures||{};
  const opened=root.querySelector('details')?.open ?? true;
  const trades=Array.isArray(d.trades)?d.trades:[];
  const wins=trades.filter(t=>Number(t.pnl)>0).length,losses=trades.filter(t=>Number(t.pnl)<0).length;
  const epochCount=Number(d.trades_count)||0;
  const historyNote=trades.length<epochCount?'Zobrazeno '+trades.length+' z '+epochCount+' obchodů aktuální epochy.':'Historie aktuální PAPER epochy.';
  root.innerHTML='<b>'+(d.healthy?'🟢 Běží':d.running?'🟠 Běží · čekám na aktuální data':'🟠 Stav nelze ověřit')+'</b><div class="grid" style="margin-top:12px">'+
   [['Zůstatek',num(d.balance)+' USDT'],['Hodnota účtu',num(d.equity)+' USDT'],['Čistý realizovaný výsledek',pnl(d.net_pnl)],['Uzavřené / otevřené',d.trades_count+' / '+d.positions.length],['Win rate',num(d.win_rate)+' %'],['Cena XRP',num(d.market_price,6)]].map(x=>'<div class="coin">'+x[0]+'<br><b>'+x[1]+'</b></div>').join('')+'</div>'+
   '<div class="coin" style="margin-top:12px"><b>Signál '+esc(a.signal||'WAIT')+'</b><br>'+esc(a.reason||'Čekám na data')+'<br>Zdroj '+esc(a.futures_provider||'—')+' · OI změna '+num(f.oi_change_pct)+' % · Top L/S '+num(f.top_ratio)+' · Taker B/S '+num(f.taker_ratio)+'</div>'+
   (d.positions.length?d.positions.map(p=>'<div class="coin" style="margin-top:8px"><b class="'+(p.side==='LONG'?'green':'red')+'">'+esc(p.symbol)+' '+esc(p.side)+'</b><br>Čistý průběžný P/L '+pnl(p.unrealized_net_pnl)+'<br>Vstup '+num(p.entry_price,6)+' · cena '+num(p.current_price,6)+'<br>SL '+num(p.stop_loss,6)+' · TP '+num(p.take_profit,6)+'<br>Otevřeno '+when(p.opened_at)+'</div>').join(''):'<p>⏳ Čekám na potvrzený obchod</p>')+
   '<div class="grid" style="margin-top:12px">'+[['Ziskové obchody',num(d.trades_count?Math.round(Number(d.win_rate||0)*epochCount/100):0,0)],['Ztrátové obchody',num(d.trades_count?epochCount-Math.round(Number(d.win_rate||0)*epochCount/100):0,0)],['Úspěšnost',d.win_rate==null?'—':num(d.win_rate)+' %']].map(x=>'<div class="coin">'+x[0]+'<br><b>'+x[1]+'</b></div>').join('')+'</div>'+
   '<details><summary>▼ Historie obchodů ('+epochCount+')</summary><p class="muted">Posledních '+trades.length+' uzavřených obchodů · český čas · '+historyNote+'</p>'+(trades.length?'<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:13px"><thead><tr><th style="text-align:left">Obchod / uzavřeno</th><th style="text-align:left">Vstup → výstup</th><th style="text-align:left">Důvod ukončení</th><th style="text-align:right">Čistý výsledek</th></tr></thead><tbody>'+trades.map(t=>'<tr style="border-top:1px solid #555"><td style="padding:12px 6px 12px 0"><b>'+esc(t.symbol)+'</b><br><b class="'+(t.side==='LONG'?'green':'red')+'">'+esc(t.side)+'</b><br>'+when(t.closed_at)+'</td><td style="padding:12px 6px">'+num(t.entry_price,6)+'<br>→ '+num(t.exit_price,6)+'</td><td style="padding:12px 6px">'+esc(t.reason)+'<br><span class="muted">LH_WHALE · poplatky '+num(t.fees)+' USDT</span></td><td style="padding:12px 0;text-align:right;white-space:nowrap">'+pnl(t.pnl)+'</td></tr>').join('')+'</tbody></table></div>':'<p class="muted">Zatím žádné uzavřené obchody v aktuální epoše.</p>')+'</details>'+
   (d.last_error?'<p class="red">'+esc(d.last_error)+'</p>':'')+(d.data_error?'<p class="yellow">Nové vstupy pozastavené: '+esc(d.data_error)+'</p>':'')+
   '<div class="muted" style="margin-top:12px">Poslední kontrola '+when(d.last_cycle_at)+' · ukládání '+esc(d.persistence)+'</div>';
  root.querySelector('details').open=!!opened;
 }catch(e){root.innerHTML='<p class="yellow">Stav Liquidity Hunter není dostupný. Čekám na obnovení spojení.</p>';}
}
refreshLHWhale();setInterval(refreshLHWhale,5000);
</script>'''

def enhance(html):
    return html.replace('<div class="card muted" id="health">',CARD+'<div class="card muted" id="health">').replace('</body>',SCRIPT+'</body>')
