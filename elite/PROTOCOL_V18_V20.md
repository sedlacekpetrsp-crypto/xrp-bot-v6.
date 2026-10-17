# Frozen V18–V20 cross-market experiment — 2026-10-14

Hypothesis: historical BTC context can help XRP entry selection where XRP-only
patterns failed. BTC is an explanatory series only; positions remain XRPUSDT
spot LONG, unlevered. No existing bots/Render settings or real orders are changed.
All April 2023–September 2026 remains DEVELOPMENT: adding BTC does not make the
already examined XRP returns independent OOS. No parameter grid or post-result
relaxation of gates. This is an experiment, not an assertion of predictive power.

## Exact signals on completed hourly bars
- V18: original V5 hourly 72-bar channel breakout/24-bar channel exit/3ATR stop,
  with entry-only gate BTC close>SMA168 and BTC SMA168 above its value 24h ago.
  Exit remains the original XRP channel exit, regardless of BTC gate changes.
  This isolates a BTC regime filter; no claim of a new unrelated strategy.
- V19: XRP 24h simple return exceeds BTC 24h return by >1 percentage point,
  BTC 24h return positive, XRP close>SMA168, and XRP crosses upward through
  its SMA24 (previous close<=previous SMA24, current close>current SMA24).
  Stop3ATR, no fixed target, exit XRP close<SMA72, max hold7days.
- V20: BTC 24h simple return>=2%, XRP 24h simple return<=0, BTC close>SMA168,
  XRP upward cross of SMA6. Stop3ATR, target6ATR, max hold48hours.
ATR is simple mean of 14 XRP true ranges through the closed signal candle.
One XRP position and one shared account. No BTC holdings or hedges.

## Data integrity
Download checksummed Binance Vision BTCUSDT 5m data over the exact same 42
complete months as XRP. Require exact timestamp equality, valid OHLC, full
month coverage and uninterrupted 5m cadence in both. No forward fills, silent
row dropping, interpolation or choosing convenient shorter periods. Both
markets' aggregate candle must be closed before a signal; execute at next
XRP 5m open. Save both symbol manifests and code/protocol checksums.
If data fail validation, report blocked experiment rather than manufactured
results. Incomplete current month is not included.

## Fixed evaluation and acceptance
Unchanged blocks Apr–Dec2023, H1 2024, H2 2024, Jan2025–Sep2026; continuous
account also reported. >=3/4 profitable blocks, >=60 continuous trades,
PF>=1.2, closeMTM DD<=10%, intrabar bound<=12%, positive 2x-cost P/L and positive
95% lower mean-daily-P/L bound (7-day block bootstrap,2000 draws,seed713).
10,000USDT start, risk0.5% inclusive of costs, max allocation35%; per-side
fee/slippage/halfspread .001/.0003/.0001. Stress doubles all. All candidates
reported, including failures. Acceptance rules are not weakened to get a pass.

Only discovery survivors can unlock 2022 historical challenge under previous
protocol rules; 2021 remains reserved. Historical backward challenge is not
prospective validation. No PAPER approval from development evidence alone.
