# Frozen V32–V33 15m entries with 4h confirmation — 2026-10-14

Both: completed15m entry candles, completed4h trend close>SMA60 and SMA60
above its value6 bars earlier. Join by final constituent5m index, never use
unfinished higher candle. ATR simple14 true ranges on15m. Minimum planned
target/current close>=2%; fixed economic hurdle, not guaranteed attainable
profit. Baseline nominal round-trip costs about0.28%, stress about0.56%.
No proof that ATR targets predict future prices. Exit if confirmed4h trend
turns false (via next15m signal), or stop/target, or48h timeout.

V32: average true range of PREVIOUS8 completed15m candles <0.7 times mean
true range of24 candles before those8; current close>previous16 highs.
Stop3ATR,target6ATR. V33: previous15m low below its previous16 lows, previous
close below its SMA20, current close above previous high and current open.
Stop2ATR,target4ATR. Higher trend and2% hurdle gate both entries. Execute at
next5m open; risk0.5% inclusive of costs, allocation<=35%,no leverage,spot LONG.
These are variants of breakout/pullback families, not independent discoveries.
Predeclared controls remove only2% hurdle, continuous base/stress; not eligible
for promotion. Retain all results, no grid or threshold changes after results.

Same consumed DEVELOPMENT Apr2023–Sep2026. Four reset blocks Apr–Dec2023,
H1 2024,H2 2024,Jan2025–Sep2026,plus continuous,initial10000USDT. Per-side
fee/slip/halfspread .001/.0003/.0001; stress doubles all. Unchanged gates:
>=3/4 profitable blocks,>=60 trades,PF>=1.2,closeDD<=10%,intrabar bound<=12%,
positive stress P/L,positive lower95% daily mean7day-block-bootstrap CI
(2000 draws,seed713). Full ledger/daily equity,checksums and manifest retained.
No multiple-search correction; lower timeframe does not create independent
OOS. Only frozen survivors unlock reserved2022 challenge;2021 reserved.
No PAPER acceptance from discovery,no LIVE,no other bot changes.
