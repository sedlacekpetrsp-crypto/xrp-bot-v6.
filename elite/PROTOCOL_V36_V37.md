# Frozen V36–V37 Boolean entry-filter composition — 2026-10-15

Test the exact trade-off observed in V18/V28, not a new parameter grid. Both
share original V5 hourly breakout72/exit24/3ATR rules. V18 gates entries by
BTC close>SMA168 and rising SMA168 vs24h ago. V28 gates by XRP taker-buy share
over latest3 completed hours>55%. Neither constituent is accepted for PAPER.
V36: permit V5 entry when either original gate permits it (OR). V37: both
must permit it (AND). Exact reuse of frozen source functions. Reject mismatched
signal timestamps, exit/target/timeout semantics or conflicting stop distances.
One position/one sizing, never add two position sizes. No forced exit when a
gate turns false; original XRP channel exit and fixed stop retained. No target
or time limit, as V5/V18/V28. Signals from closed candles,next5m open execution.
Record overlap of ENTRY SIGNALS, not fictitious independent trades. Union can
change occupancy and suppress later entries; its trade count need not equal
sum of constituent counts. Intersection is not independent confirmation when
signals are correlated. This experiment is informed by prior development audit.

Same consumed Apr2023–Sep2026 DEVELOPMENT,4 original reset blocks and continuous.
Do NOT replace original gates with favorable six-month counts from recent audit.
Initial10000USDT,spot LONG,no leverage,0.5% planned risk including costs,max35%
allocation. Per-side fee/slip/halfspread .001/.0003/.0001; stress doubles all.
Unchanged acceptance:>=3/4 positive blocks,>=60 trades,PF>=1.2,closeDD<=10%,
intrabar bound<=12%,positive stress P/L,positive lower95% daily mean7day-block
bootstrap CI(2000 draws,seed713). No threshold relaxation after results.
CI not search-corrected; more trials increase selection bias. Save both failures
and full ledger/daily equity evidence. No new independent OOS. Only qualifying
frozen candidates unlock reserved2022 challenge;2021 stays reserved. No PAPER
acceptance from discovery,no LIVE,no other bot modifications.
