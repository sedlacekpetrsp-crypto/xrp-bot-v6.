# Frozen V34–V35 weekly VWAP hypotheses — 2026-10-14

Use actual cumulative USDT quote turnover / XRP base volume from matching
checksummed Binance spot5m archives (zero-based columns7/5). Not typical-price
approximation. Validate exact OHLC/time/count/hash equality,finite nonnegative
values and quote within low*base/high*base with rounding tolerance max(1e-6,
quote*1e-8). Zero cumulative volume gives unavailable VWAP. Monday00:00 UTC
resets accumulator; initial partial week unavailable. Only completed candles.
Hourly signals require>=24h since Monday and previous/current signal in same
week; warmup200 hours. No cross-reset entry. Entry executes next5m open.

V34: prior close<=prior weekly VWAP, current close>current weekly VWAP,
current close>SMA168 and SMA168 above its value24h earlier. Stop3ATR14,no target,
exit completed hourly close<VWAP,timeout7days. V35: prior close<prior weekly
VWAP minus2*prior ATR14,current close>prior high and below current weekly VWAP.
Stop2ATR14,target4ATR14,exit hourly close>=VWAP,timeout48h. ATR simple14 true
ranges. Explicitly both signal entries and VWAP exits are unavailable during
first24h of week (initial stop,target,timeout still active). Weekly anchor resets
for an existing position too; this is a predeclared feature, not an entry anchor.
These are trend/reversal variants, not independent strategy discoveries.

Consumed DEVELOPMENT Apr2023–Sep2026,4 reset blocks Apr–Dec2023/H1 2024/H2 2024/
Jan2025–Sep2026 plus continuous. Initial10000USDT,spot LONG,single position,
no leverage,risk0.5% including costs,max35% allocation. Per side fee/slip/
halfspread .001/.0003/.0001;stress doubles all. Unchanged gates:>=3/4 positive
blocks,>=60 trades,PF>=1.2,closeDD<=10%,intrabar bound<=12%,stress P/L>0,positive
lower95% daily mean7day-block-bootstrap CI(2000 draws,seed713). No grid or
post-result adjustment. Save all failures,full evidence,manifest/code hashes.
CI not search-corrected. A new input does not make old returns independent OOS.
Only survivors unlock reserved2022 challenge;2021 reserved. No PAPER acceptance
from development alone,no LIVE,no changes to other bots.
