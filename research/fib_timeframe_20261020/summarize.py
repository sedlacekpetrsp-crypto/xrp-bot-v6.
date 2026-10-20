"""Normalize floating-point breakevens and publish a reproducible research decision."""
import gzip,hashlib,json,pathlib
H=pathlib.Path(__file__).resolve().parent
r=json.loads((H/'results.json').read_text());ext=json.loads((H/'extension_results.json').read_text())
tr=json.loads(gzip.decompress((H/'trades.json.gz').read_bytes()));et=json.loads(gzip.decompress((H/'extension_trades.json.gz').read_bytes()))
def normalize(stats,trades):
 p=[float(t['net_pnl']) for t in trades];wins=[x for x in p if x>1e-8];losses=[x for x in p if x < -1e-8]
 stats.update(wins=len(wins),losses=len(losses),breakevens=sum(abs(x)<=1e-8 for x in p),profit_factor=sum(wins)/-sum(losses) if losses else None)
for name in ('baseline_5m','candidate_15m'):
 for period in ('development','holdout','stress'):normalize(r[name][period],tr[name+'_'+period])
for period in ('development','holdout','stress'):normalize(ext[period],et[period])
(H/'results.json').write_text(json.dumps(r,indent=2));(H/'extension_results.json').write_text(json.dumps(ext,indent=2))
lines=['# FIB timeframe screening — 20 October 2026','','Decision: no production filter/timeframe change. PAPER v13 remains deployed. Paused strategies remain paused.','','## Results','','All figures are simulated USDC after fees/slippage. Independent 10,000 USDC starting account for each period, cash risk capped near 9.18 USDC per trade.','','| Variant | Apr–Jun trades | Apr–Jun net | Jul–Sep trades | Jul–Sep net | Jul–Sep double-slip net |','|---|---:|---:|---:|---:|---:|']
for name,row in [('Current 5m',r['baseline_5m']),('15m candidate',r['candidate_15m']),('1h exploratory',ext)]:
 a,b,c=[row[k] for k in ('development','holdout','stress')]
 lines.append(f"| {name} | {a['trades']} | {a['net_pnl']:.2f} | {b['trades']} | {b['net_pnl']:.2f} | {c['net_pnl']:.2f} |")
lines+=['','The preregistered 15m screening gate failed. The 1h extension was added after seeing the 15m result and reuses the date windows; it is exploratory, not independent confirmation. No result establishes future profitability.','','## Method and limits','','- 246,528 five-minute bars across BTC/ETH/SOL/XRP, March–September 2026. March is warmup; evaluation is April–September. Monthly ZIP SHA-256 values checked against Binance CHECKSUM files; derived dataset hashes retained.','- Production FIB candidate, multi-timeframe confirmation (score 4 and 1h veto), entry sizing, cash caps and fee arithmetic reused from c111da1. Only the FIB signal timeframe changes.','- Fee 0.095% per side, slippage 0.02% per side; stress uses 0.04% slippage per side. Stop multiplier 1.15. Two-position maximum and original stop/target restrictions retained.','- No future candles: closed input only, next 5m open entry, gap-aware stop; stop wins if stop and target both touched in one bar. Breakeven moves only after bar close.','- FIB-only approximation, not the full production portfolio: no VWAP/4h interactions, no historical news veto, no 10-second exit path, no minute-by-minute entry retry. Intrabar ordering is not observable.','- 1e-8 USDC tolerance classifies floating-point breakevens; raw trade values are retained.','','## Verification','','Five simulator tests passed: aggregation close timing, future-bar isolation, gap rejection, stop-first ordering/next-open entry and worse-price gap fill. Sixteen production regression tests passed for stop-risk sizing, execution freshness and paused reversion.','','## Reproduce','','```sh','python -m pip install -r requirements.txt','python research/fib_timeframe_20261020/download.py /tmp/fib-data','python research/fib_timeframe_20261020/test_replay.py','python research/fib_timeframe_20261020/run.py /tmp/fib-data','python research/fib_timeframe_20261020/extension.py /tmp/fib-data','python research/fib_timeframe_20261020/summarize.py','```','','Signals and simulated fills are research output only. No live orders or database writes are performed.']
(H/'README.md').write_text('\n'.join(lines)+'\n')
files=['app_blue_whale_mirror.py','paper_stop_policy.py','news_signal.py']
root=H.parents[1]
hashes={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in files}
hashes.update({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in H.glob('*.py')})
(H/'source_hashes.json').write_text(json.dumps(hashes,indent=2))
print('\n'.join(lines[:15]))
