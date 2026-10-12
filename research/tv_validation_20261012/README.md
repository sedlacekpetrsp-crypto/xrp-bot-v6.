# TV Consensus validation — 12 October 2026

All nine variants remain negative after modeled fees/slippage. No variant passes the numeric gate, so TV new entries are paused. Existing exit management remains enabled. No new strategy or increased risk is promoted.

Data: 69,360 validated 1m XRPUSDC bars, 25 August–12 October 04:00 UTC. Warmup precedes 1 September. Development 1–20 September; chronological check 21 September–12 October 04:00 UTC. Each period starts independently at 10,000 USDC; do not add them as a continuous equity curve. This market period overlaps earlier research and the choice of hypotheses; it is not unseen data.

The runner uses production TV consensus analysis, entry gating, structural/ATR stops, sizing, net targets, exit management and cooldown formulas. Scan rate is one sample per minute instead of 15 seconds; signal acceleration may differ within the minute. Only closed 1m/5m/15m inputs are available. Entry at the next minute open, costs 0.095%/side plus 0.02%/side slippage; risk <=0.08%. Stop wins simultaneous SL/TP; adverse gaps fill at open. Intrabar favorable peaks are not used: profit protection changes at close for the next minute. This approximates the live 2-second exit checks and does not reproduce ticks, latency, news, multiple portfolios or financing. Max drawdown is on closed balance.

| Min ADX | ATR multiplier | Development net | Check net | Check trades | Check PF | Check at 2x slippage |
|---:|---:|---:|---:|---:|---:|---:|
| 20 | 1.5 | -78.42 | -130.90 | 47 | 0.463 | -127.99 |
| 20 | 2 | -78.42 | -130.90 | 47 | 0.463 | -127.99 |
| 20 | 2.5 | -78.32 | -139.58 | 47 | 0.445 | -136.68 |
| 22 | 1.5 | -62.06 | -105.94 | 41 | 0.512 | -110.38 |
| 22 | 2 | -62.06 | -105.94 | 41 | 0.512 | -110.38 |
| 22 | 2.5 | -61.96 | -114.64 | 41 | 0.491 | -119.08 |
| 25 | 1.5 | -73.63 | -61.48 | 30 | 0.626 | -63.82 |
| 25 | 2 | -73.63 | -61.48 | 30 | 0.626 | -63.82 |
| 25 | 2.5 | -73.52 | -70.22 | 30 | 0.593 | -72.56 |

Raising ADX reduces trade count but does not create positive expectancy. ATR multiplier changes are often dominated by the pre-existing minimum stop and 5m/structural distance. No further variants were added after reading results.

Reproduction: `python research/tv_validation_20261012/download.py /tmp/tv-data` then `python research/tv_validation_20261012/run.py /tmp/tv-data/XRPUSDC_1m.json`. Hashes and parameters are retained. Generated signal cache and raw batches are ignored; trades/results are committed. Future unused data is required before promoting a profitable candidate.
