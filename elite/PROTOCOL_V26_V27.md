# Frozen V26–V27 base-volume hypotheses — 2026-10-14

New explanatory input: traded XRP base-asset volume from column5 (zero-based)
of the SAME checksummed Binance spot5m archive as OHLC. Not quote volume,
not buyer/seller imbalance, and not evidence of liquidation or manipulation.
Reject nonfinite/negative volume, timestamp/price/count/hash disagreement.
Sum volume over complete UTC4h bars. Current completed volume >=2 times
median of previous20 completed4h volumes, with positive baseline, gates entry.

V26 trend: 4h close above previous20 highs, volume gate; stop3ATR14, no target,
exit close below previous10 lows, maximum7days. V27 reversal: 4h lower wick
>=half of high-low, positive body, close>previous close, low<previous6 lows,
volume gate; stop2ATR14,target4ATR14,maximum48h. ATR simple14 true ranges.
Warmup2004h bars. Next5m-open execution. All positions spot LONG, no leverage.
Related to previously studied breakout/reversal families, not independent
strategies. Predeclared diagnostic controls use identical price/exit rules
without volume gate; report their continuous base/stress results. Controls
cannot qualify for challenge in this experiment; no post-result selection.

Development Apr2023–Sep2026, previously examined; adding volume does not
restore independence. Four reset blocks Apr–Dec2023/H1 2024/H2 2024/Jan2025–Sep2026
plus continuous. Initial10000USDT,0.5% planned risk inclusive of costs,35%
allocation cap. Per side fee/slip/halfspread .001/.0003/.0001; stress doubles all.
Unchanged gates: >=3/4 profitable blocks, >=60 continuous trades,PF>=1.2,
closeMTM DD<=10%, intrabar bound<=12%,stress P/L>0,lower95% daily mean>0
(7day block bootstrap,2000 draws,seed713). Report failures and full evidence.
No grid/threshold adjustment after results. CIs not multiple-search corrected.
Only qualifying frozen candidates unlock reserved2022 challenge;2021 reserved.
No PAPER acceptance from development only; no LIVE or other bot changes.
