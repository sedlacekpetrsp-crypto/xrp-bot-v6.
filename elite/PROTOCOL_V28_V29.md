# Frozen V28–V29 taker-flow experiment — 2026-10-14

Source schema verified against official Binance spot kline documentation:
https://github.com/binance/binance-public-data/blob/master/README.md
Zero-based column5 is XRP total base volume; column9 taker-buy base volume.
Use the same checksummed monthly XRP archives and exact matching OHLC/time
rows. Reject nonfinite/negative values or buy>total. No clipping/imputation.
Total minus taker-buy is taker-sell volume, not net money entering the asset.
Only completed UTC bars. Aggregate sums first, then divide buy/total; never
average ratios. Zero total cannot qualify. No tick-order/order-book claims.

V28: original V5 hourly breakout above previous72 highs, stop3ATR14, exit
below previous24 lows, no time exit; entry additionally requires sum taker-buy
/ sum total over latest3 completed hourly bars >0.55. V29: 4h lower wick at
least half range, positive body, close above previous close, low below
previous6 lows; require current completed4h buy/total<0.50 (sell majority).
Stop2ATR14,target4ATR14,timeout48h. V29 tests recovery despite sell pressure,
not a claim that passive buyers or liquidations are directly observed.
ATR simple14 true ranges; warmup200 aggregate bars; next5m open execution.
Related to V5 and V27 price families, not two independent strategy discoveries.
Predeclared controls remove only flow gating, run continuous base/stress,
and cannot qualify for challenge. Do not select controls post hoc.

Apr2023–Sep2026 remains DEVELOPMENT; four reset blocks Apr–Dec2023/H1 2024/
H2 2024/Jan2025–Sep2026 and continuous. Initial10000USDT,spot LONG,single
position,no leverage,0.5% risk including costs,max35% allocation. Per-side
fee/slip/halfspread .001/.0003/.0001; stress doubles all. Unchanged gates:
>=3/4 positive blocks,>=60 trades,PF>=1.2,closeDD<=10%,intrabar bound<=12%,
positive stress P/L,positive lower95% daily mean7day block-bootstrap CI
(2000 draws,seed713). No parameter grid or after-result threshold changes.
CI not adjusted for repeated searching. Save all failures and full evidence.
Only frozen survivors unlock reserved2022 challenge;2021 reserved. Adding a
new column does not make old XRP returns OOS. No PAPER approval from discovery,
no LIVE or modifications to other bots. Freeze code before evaluation.
