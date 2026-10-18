# Frozen V38–V39 closed-loss streak overlays — 2026-10-15

Underlying entries/exits exactly V18; position sizing/stops unchanged. After
THREE consecutive closed trades with net P/L<0 (fees included), activate7-day
entry overlay. Breakeven/profit resets streak. Trigger resets streak to0;
subsequent losses can trigger a new window. Time starts at close of exit5m
candle (stored exit timestamp+5min), so no intrabar feedback/lookahead.
V38: no new entries until window expires. V39: during window require V37
(BTC gate AND taker-flow gate), then restore V18. Exact reuse of original
functions. Expiry is inclusive: entry allowed at timestamp==until. Exit
signals are never disabled by pause. One position,same risk,never double size.

Simulator delivers copies of newly closed trades only after processing the
entire candle. Reset all overlay state at start of EVERY simulation, including
new cost scenario/block; do not train state on other blocks. Final boundary
liquidation may create a recorded event but affects no subsequent run. Stress
uses its OWN realized net losses, hence may trigger different windows. Log
all events. Unchanged V18 continuous base/stress control checks simulator
regression. No virtual trades during pause. No parameter grid or post-result
tuning of streak/time. Loss clusters do not prove future losses are predictable.

Same consumed DEVELOPMENT Apr2023–Sep2026,4 original reset blocks and continuous,
initial10000USDT,spot LONG,no leverage,risk0.5% including costs,allocation<=35%.
Per-side fee/slip/halfspread .001/.0003/.0001;stress doubles all. Original gates:
>=3/4 positive blocks,>=60 trades,PF>=1.2,closeDD<=10%,intrabar bound<=12%,positive
stress P/L,positive lower95% daily mean7day-block-bootstrap CI(2000 draws,seed713).
No changes to gates;CI not search-corrected. Full ledgers and event evidence.
No independent OOS from reused data. Only survivors unlock reserved2022 challenge;
2021 reserved. No PAPER approval from discovery,no LIVE,no other bot changes.
