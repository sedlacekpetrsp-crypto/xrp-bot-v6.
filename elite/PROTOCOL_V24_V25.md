# Frozen V24–V25 hypotheses — 2026-10-14

V24: failed downside breakout on completed 4h XRP bars. Current low below
minimum low of PREVIOUS24 bars, close above that level AND open, close in
upper25% of its range. Stop2ATR14, target4ATR14, timeout48h. A price pattern,
not evidence of liquidations or manipulation. Related broadly to reversals
V8/V13, but uses a failed price-level break rather than shock or RSI.

V25: hourly delayed breakout retest, related to V5 trend family. Completed
close above previous72 highs arms a fixed level equal to that prior maximum.
Only a LATER hour (within24h inclusive) may enter if low<=level<close and
close>SMA168. Cancel when close<level minus ATR14 at setup, or age>24h.
One pending setup; do not replace while active. Consume on first retest;
a newly armed setup cannot enter same candle. Stop3ATR14 at entry signal,
no target, exit below previous24 lows or timeout7days. Signals maintain their
state irrespective of account occupancy; a consumed signal is not queued.
Both execute at next5m open. ATR uses completed candles, simple14 true ranges.

Fixed initial10000USDT, single unlevered XRP spot LONG, risk0.5% including
costs, allocation<=35%. Per-side fee/slip/halfspread .001/.0003/.0001; stress
2x all. Checked 5m full-month XRP data Apr2023–Sep2026. These are consumed
DEVELOPMENT data. Four blocks Apr–Dec2023/H1 2024/H2 2024/Jan2025–Sep2026,
each reset, plus continuous. All results reported, no parameter grid.
Unchanged gates: >=3/4 positive blocks, >=60 trades, PF>=1.2, closeMTM DD<=10%,
intrabar bound<=12%, positive stress P/L, positive lower95% daily mean
7day block-bootstrap CI (2000 draws,seed713). No search correction in CI.
Only survivors unlock reserved2022 historical challenge; 2021 stays reserved.
Neither development nor backward challenge alone authorizes PAPER or LIVE.
No other bot or deployment changes. Freeze before measuring results.
