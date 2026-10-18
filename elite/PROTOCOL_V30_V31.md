# Frozen V30–V31 monthly causal strategy selection — 2026-10-14

Different question: can recent performance select among fixed price strategies
without using the selected month's returns? Fixed library, ordered ties:
V5,V8,V10,V18,V22,V25. No new entry parameters, no trailing-stop components.
Selection is itself a new strategy, not an independently validated ensemble.

At each UTC month start after >=180 days of available price history, simulate
each component separately on preceding180 and90 calendar days. Reset10000USDT
per scoring window, include forced final liquidation costs, use double costs
(fee/slip/halfspread .002/.0006/.0002). Training end excludes the first candle
of the new month. Signals may use earlier completed history for warmup.
V30 eligible:180day net P/L>0,>=5 trades,PF>=1.2,closeDD<=10%. Choose largest
180day net P/L among eligible, stable library-order ties, else cash.
V31 additionally requires90day P/L>0 and>=3 trades. Rank as V30.

Before sufficient history stay cash; first selection October2023. Hold selection
for the calendar month. Existing position retains original strategy exits
across month switches, including when new selection is cash. No forced monthly
liquidation. Only new entries use current choice; single shared position/account.
Prior closed5m signal may enter at month-start open using new selection based
only on data through the immediately preceding candle. Retain full score table.
Final stress runs double execution costs with SAME frozen baseline selection
schedule, which was itself fitted on stress-cost historical windows.

Development Apr2023–Sep2026,4 reset blocks and continuous as previous protocol.
Early warmup cash is included in returns and daily statistics, never removed.
Initial10000USDT,spot LONG,0.5% risk including costs,35% allocation,no leverage.
Baseline costs per side .001/.0003/.0001; stress doubles all. Unchanged gates:
>=3/4 positive blocks,>=60 trades,PF>=1.2,closeDD<=10%,intrabar bound<=12%,
stress P/L>0,positive lower95% daily mean7day-block-bootstrap CI,2000 draws,
seed713. No threshold tuning after results. All scores and failures retained.
Selection can be causal but this is NOT independent OOS: components and rules
were chosen after examining these development years. Multiple-search bias
remains; CI is not search-corrected. Only survivors unlock reserved2022 challenge,
2021 remains reserved. No PAPER acceptance from discovery,no LIVE/other bot changes.
