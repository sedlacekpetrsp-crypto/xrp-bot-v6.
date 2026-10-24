# Research decision — 2026-10-20

## SWEEP_TREND_V1: rejected

Retrieved completed run https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./actions/runs/39411477438 (commit ca83f945e2194178458e4008c035cc5906c398a7).
All eight jobs completed and logs contain 12 monthly coverage checks and valid JSON reports. 105120 bars for 5m, 35040 bars for 15m, October 2025–September 2026. Historical run success is execution success, not profitability.

| Market/timeframe | Train trades | Test trades | Test win rate | Test profit factor |
|---|---:|---:|---:|---:|
| (XRPUSDT, 5m) | 312 | 137 | 24.09% | 0.3412 |
| (SOLUSDT, 15m) | 146 | 54 | 35.19% | 0.5343 |
| (SOLUSDT, 5m) | 345 | 157 | 25.48% | 0.3302 |
| (BTCUSDT, 5m) | 337 | 147 | 21.09% | 0.2532 |
| (XRPUSDT, 15m) | 117 | 44 | 29.55% | 0.3818 |
| (ETHUSDT, 15m) | 156 | 60 | 38.33% | 0.6923 |
| (ETHUSDT, 5m) | 309 | 147 | 21.09% | 0.2250 |
| (BTCUSDT, 15m) | 151 | 59 | 20.34% | 0.3066 |

All eight variants lose after assumed costs in both chronological 70/30 segments. Do not deploy or optimize against these test segments. The old simulator has gap-stop fill limitations and a full-notional compounding convention; its returns are not actual account P/L. Rejection stands; no positive performance claim.

## FLOW_PRESSURE_V1: new hypothesis, first implementation, rejected on XRP 15m

Standalone spot LONG strategy. Three closed candles must have aggregate taker-buy base volume share >=60%, mean volume >=1.25 times prior 20-bar mean, close above prior close-volume-weighted reference and above close three bars earlier. Enter next open, stop distance 1.5 average true ranges, target 2R, maximum hold 16 bars. One position at a time. No order APIs or runtime imports.

Fixed before historical evaluation: 0.095% fee per side and 0.02% adverse slippage per side. Gap stops fill at worse opening price; ambiguous stop/target candle counts as stop first. Five local deterministic regression tests passed (PYTHONPATH=. python tests/test_flow_pressure_v1.py). Synthetic tests verify mechanics only.

35040 actual XRPUSDT 15m bars, October 2025–September 2026. Monthly coverage and continuous timestamps verified; archive URLs and SHA256 fingerprints in flow_pressure_results_20261020.json (fingerprints are provenance, not independently verified published checksums). Raw archive taker-buy base field retained. No fabricated volume proxy.

| Segment | Trades | Win rate | Profit factor | Mean net return per trade |
|---|---:|---:|---:|---:|
| Oct 2025–Jun 2026 | 138 | 23.91% | 0.3189 | -31.26 bps |
| Jul–Sep 2026 | 38 | 44.74% | 0.8196 | -5.72 bps |
| Jul–Sep, double fees and slippage | 37 | 37.84% | 0.3843 | -27.79 bps |

Trade counts can differ under stress because entry prices, brackets and position duration change. Each segment starts without prior warmup; no cross-boundary positions. This is a single-market screen, not portfolio results. The calendar period was already used for other hypotheses and is not an untouched final holdout. No parameter tuning performed after these results. Neither strategy qualifies for deployment.

## Continuation constraints

Keep PAPER-only scope and existing paused strategies paused. No Render, runtime configuration or production branch changes made. Future candidates require a distinct hypothesis, provenance-preserving data, realistic costs, and fresh forward evidence before acceptance. Do not revive failed variants by tuning to the same test window.

## CROSS_SECTIONAL_ROTATION_V1: distinct hypothesis, historically rejected

Protocol and all fixed parameters were committed before historical performance was read. This is a long-only, one-position portfolio rotation strategy: at each UTC day boundary it selects the strongest positive 21-day return among BTC, ETH, SOL and XRP only while the last completed BTC daily close is above its 60-day EMA. It allocates 35% of account equity, enters or rotates at the next 15-minute open, and uses a fixed 3.0 x completed 20-day ATR stop. It is not a sweep, breakout, order-flow, VWAP reversion, Fibonacci, Aroon or Supertrend variant.

The test used 192 public Binance Vision monthly spot archives from October 2022 through September 2026. SHA256 fingerprints and coverage counts are in `cross_sectional_rotation_results_20261020.json`. One exchange-wide outage affected all four assets on 24 March 2023; the incomplete UTC day was recorded and excluded for every asset rather than filled. The resulting common dataset has 1,460 complete aligned days. Five deterministic engine tests passed, including next-open causality, one-position overlap, gap-stop fill at the worse open, increased-cost monotonicity and timestamp misalignment rejection.

Normal costs are 0.095% fee and 0.02% adverse slippage per side; the stress run doubles both. Results use 10,000 USDT initial equity, no leverage, 35% maximum active notional and intraday 15-minute mark-to-market drawdown.

| Period | Trades | Normal net return | Normal PF | Normal max DD | Double-cost net return | Double-cost PF |
|---|---:|---:|---:|---:|---:|---:|
| 2023 | 42 | +90.42% | 2.7647 | 19.37% | +84.05% | 2.5888 |
| 2024 | 41 | +79.56% | 3.2945 | 21.41% | +73.69% | 3.0457 |
| 2025 | 28 | +10.83% | 1.4879 | 10.54% | +8.37% | 1.3600 |
| Jan-Sep 2026 | 26 | -0.34% | 0.9777 | 12.06% | -2.40% | 0.8530 |
| Combined continuous path | 136 | +277.47% | 2.1129 | 21.41% | +238.21% | 1.9583 |

The combined return and profit factor pass their thresholds, but the preregistered gate requires every period to be positive normally and combined maximum drawdown no more than 15%. January-September 2026 is negative and drawdown is 21.41%; no new 30-trade forward PAPER sample exists. Therefore `passes_historical_gate=false` and `robust_candidate=false`. Reject without tuning these parameters on the revealed periods. Do not deploy, start a PAPER service, change Render or touch `v8-fly-layer-test`.

## SOL_ETH_PAIRS_V1: distinct market-neutral hypothesis, rejected

The protocol and fixed parameters were committed before historical performance was read. The strategy trades mean reversion in the 720-hour log(SOL/ETH) ratio as an equal-notional two-leg pair: enter beyond absolute z=2.25, exit inside 0.40, stop at absolute z=4.0, after 336 hours, or at a 12% adverse move in either leg. Gross exposure is 35% of equity. Normal costs include 0.095% fees and 0.02% adverse slippage per leg and side plus 8% annualized short borrow; stress doubles all three. This is cross-asset statistical arbitrage, not another single-asset reversion filter.

The test used 94 public Binance Vision SOLUSDT and ETHUSDT 1-hour monthly archives from November 2022 through September 2026. URLs, SHA256 fingerprints and missing-bar counts are stored in `sol_eth_pairs_results_20261021.json`. One exchange-wide incomplete UTC day, 24 March 2023, was recorded and excluded from both legs without fabricated candles, leaving 1,429 complete aligned days. Four deterministic engine tests passed: causal next-open entry, conservative gap-stop fill, cost monotonicity/position non-overlap and timestamp-alignment rejection.

| Period | Trades | Normal net | Normal PF | Normal max DD | Double-cost net | Double-cost PF |
|---|---:|---:|---:|---:|---:|---:|
| 2023 | 50 | -24.31% | 0.2365 | 27.55% | -27.69% | 0.1862 |
| 2024 | 36 | -3.03% | 0.7855 | 9.32% | -6.14% | 0.6157 |
| 2025 | 43 | -8.34% | 0.6272 | 12.14% | -11.84% | 0.5120 |
| Jan-Sep 2026 | 38 | -0.17% | 0.9776 | 5.54% | -3.51% | 0.6426 |
| Combined continuous path | 167 | -32.26% | 0.4992 | 35.05% | -41.78% | 0.3874 |

The strategy fails every profitability and stability gate except sample size. Reject it without parameter tuning on the revealed periods; do not start forward PAPER because the historical prerequisite failed. No Render, deployed branch, paused bot or real account was touched.

Next concrete research step: preregister a genuinely different volatility-conditioned directional hypothesis using a new chronological holdout, rather than modifying SOL/ETH z-score thresholds or reusing this failed pair relationship.

## BROAD_SHOCK_REBOUND_V1: distinct event hypothesis, rejected

The hypothesis and gates were committed before performance was read. A completed-hour signal requires a median six-hour return of -3% or worse across BTC, ETH, SOL and XRP, at least three declining assets, and median six-hour volume at least 1.35 times the preceding 48-hour baseline. The strategy buys a 35%-gross equal-weight spot basket at the next open, holds at most 18 hours, uses a 6% stop on every leg and enforces a 12-hour cooldown. It is a synchronized liquidation-event hypothesis rather than a VWAP/RSI, sweep, breakout, flow, rotation or pair threshold change.

The test used 292 public Binance Vision 1-hour monthly archives from September 2020 through September 2026. Archive URLs, SHA256 fingerprints, missing-bar counts and the ten excluded incomplete UTC dates are in `broad_shock_rebound_results_20261021.json`; no candles were fabricated. The aligned dataset contains 2,211 complete days. Four deterministic tests passed for causal next-open entry, conservative gap stops, one-basket overlap/cost monotonicity and alignment rejection.

| Period | Trades | Normal net | Normal PF | Normal max DD | Double-cost net | Double-cost PF |
|---|---:|---:|---:|---:|---:|---:|
| 2021 | 74 | -18.89% | 0.6241 | 20.43% | -23.95% | 0.5413 |
| 2022 | 75 | -12.10% | 0.7376 | 16.20% | -17.18% | 0.6403 |
| 2023 | 33 | +5.61% | 1.5987 | 3.75% | +2.84% | 1.2680 |
| 2024 | 47 | -11.12% | 0.5531 | 11.39% | -14.37% | 0.4601 |
| 2025 | 58 | -8.03% | 0.7171 | 10.23% | -12.19% | 0.5978 |
| Jan-Sep 2026 | 29 | +0.17% | 1.0210 | 3.93% | -2.14% | 0.7671 |
| Combined continuous path | 316 | -38.34% | 0.7201 | 41.42% | -52.34% | 0.6086 |

Only sample size passes. All profitability, cross-period stability, drawdown and profit-concentration gates fail, so `passes_historical_gate=false` and `robust_candidate=false`. Reject without tuning the revealed -3%, volume, stop or holding-period parameters. Do not start forward PAPER and do not touch Render, `v8-fly-layer-test`, paused bots or real accounts.

Next concrete step: test a non-event, volatility-managed directional allocation with parameters fixed on pre-2023 data and a later chronological validation, rather than altering this failed rebound rule.

## VOLATILITY_MANAGED_MOMENTUM_V1: positive aggregate, preregistered gate failed

The hypothesis and gates were committed before performance was read. At each UTC month boundary the strategy holds only BTC, ETH, SOL and XRP assets with positive completed 90-day return, weighted by inverse completed 30-day realized volatility. Total spot allocation is capped at 35% of equity and each raw asset share at half that allocation; each leg has a fixed 12% stop. This is a monthly absolute-momentum allocation rule rather than a winner rotation, breakout, event rebound, order-flow or pair strategy.

The run used the same 292 public Binance Vision 1-hour archives from September 2020 through September 2026, but a separately preregistered chronological protocol: 2021–2022 development and 2023–September 2026 validation. URLs, SHA256 fingerprints, missing-bar counts and ten excluded incomplete UTC dates are stored in `volatility_managed_momentum_results_20261022.json`; no candles were filled. Four deterministic tests passed for causal allocation, month-open entries and non-overlap, gap-stop/cost handling and alignment rejection.

| Block | Trades | Normal net | Normal PF | Normal max DD | Double-cost net | Double-cost PF |
|---|---:|---:|---:|---:|---:|---:|
| Development 2021 | 38 | +74.74% | 2.6821 | 19.03% | +73.20% | 2.6303 |
| Development 2022 | 8 | -7.62% | 0.2645 | 9.26% | -8.51% | 0.2391 |
| Validation 2023 | 28 | +14.50% | 2.0245 | 15.11% | +13.65% | 1.9427 |
| Validation 2024 | 32 | +19.40% | 1.8436 | 11.76% | +18.44% | 1.7905 |
| Validation 2025 | 30 | -1.98% | 0.8964 | 11.34% | -2.64% | 0.8640 |
| Validation Jan-Sep 2026 | 5 | +0.96% | 1.4500 | 3.92% | +0.84% | 1.3881 |
| Continuous validation | 95 | +35.31% | 1.5084 | 15.11% | +32.15% | 1.4597 |

Aggregate validation, both profit-factor thresholds, sample size, cost stress and concentration checks pass. The preregistered overall gate nevertheless fails because development 2022 and validation 2025 are negative and validation drawdown is 15.108%, above the fixed 15% ceiling; no new 30-trade forward PAPER sample exists. Therefore `passes_historical_gate=false` and `robust_candidate=false`. Reject without changing the revealed 90/30-day windows, stop, caps or rebalance schedule. No PAPER service, Render setting, deployed branch, paused strategy or real account was changed.

Next concrete step: preserve these results as a rejected benchmark and preregister a structurally different downside-asymmetry strategy; do not mine the same validation years for a filter that rescues this model.

## DOWNSIDE_IMBALANCE_SHORT_V1: distinct downside-asymmetry hypothesis, rejected

The hypothesis, fixed parameters and gates were committed before historical performance was
read. On each asset independently, a completed 24-hour window must have squared negative-return
energy at least 2.5 times positive energy, a close return of -2% or worse, at least eight negative
hours, and a close in the bottom quarter of the range. The portfolio shorts the strongest signals
at the next open, at most two concurrent 17.5%-equity positions, with a 3.5% stop, 4% target,
eight-hour timeout and 12-hour per-symbol cooldown. This is a short continuation model rather
than a modification of the rejected long/event, flow, pair, rotation or monthly momentum rules.

The run used 292 public Binance Vision spot 1-hour archives from September 2020 through September
2026 as a short-execution proxy. URLs, ZIP SHA256 fingerprints and missing-bar counts are in
`downside_imbalance_short_results_20261022.json`. The ten incomplete or unaligned UTC days were
removed across every asset without filling; causal lookbacks cannot cross those gaps. The aligned
dataset contains 2,211 complete days. Normal costs are 0.095% fee and 0.02% adverse slippage per
side plus 8% annualized borrow accrued hourly; stress doubles all three. Six deterministic tests
passed, including completed-bar causality, next-open entry, gap-stop fill, stop-first ambiguous
candles, borrow accounting and rejection of lookbacks across data gaps.

| Block | Trades | Normal net | Normal PF | Normal max DD | Double-cost net | Double-cost PF |
|---|---:|---:|---:|---:|---:|---:|
| Development 2021 | 457 | -13.89% | 0.8677 | 21.76% | -29.90% | 0.7183 |
| Development 2022 | 539 | +4.45% | 1.0483 | 10.53% | -16.34% | 0.8268 |
| Validation 2023 | 338 | -16.05% | 0.6437 | 16.12% | -26.88% | 0.4655 |
| Validation 2024 | 431 | -10.83% | 0.8413 | 14.59% | -25.11% | 0.6532 |
| Validation 2025 | 445 | -20.67% | 0.7093 | 22.94% | -33.80% | 0.5513 |
| Validation Jan-Sep 2026 | 339 | -9.54% | 0.7717 | 13.05% | -21.58% | 0.5449 |
| Continuous validation | 1,553 | -46.28% | 0.7435 | 46.44% | -71.57% | 0.5573 |

Only the minimum validation sample-size gate passes. Development consistency, both profit-factor
thresholds, every normal validation block, stress stability, stressed total return, drawdown and
profit-concentration gates fail. Thus `passes_historical_gate=false` and `robust_candidate=false`.
No forward PAPER run is warranted. Do not optimize the revealed energy ratio, return, bracket or
holding thresholds and do not deploy, start paused strategies, touch Render, modify
`v8-fly-layer-test` or trade a real account.

Next concrete step: preregister a structurally different time-series volatility-risk-premium
screen that operates on daily regime transitions and uses a future chronological slice, rather
than reversing this failed short or retuning its intraday thresholds.

## WEEKEND_CARRY_V1: distinct calendar-risk hypothesis, rejected

The calendar rule and all gates were committed before historical returns were read. The strategy
buys an equal-weight BTC, ETH, SOL and XRP spot basket every Saturday at 00:00 UTC and exits at the
first open at or after 48 hours. Gross exposure is 35% of current equity, each leg has a 6% stop,
and no baskets overlap. It contains no trend, flow, shock, spread, volatility-sizing or
cross-sectional price signal used by earlier rejected models.

The test used 292 public Binance Vision 1-hour archives from September 2020 through September
2026. URLs, ZIP SHA256 fingerprints, coverage counts and ten excluded incomplete or unaligned UTC
days are in `weekend_carry_results_20261023.json`; no candle was synthesized. The shared dataset
contains 2,211 complete days. Costs are 0.095% fee and 0.02% adverse slippage per leg and side;
stress doubles both. Five deterministic tests passed for calendar causality, 48-hour exit,
non-overlap, worse-open gap stops, cost sensitivity and timestamp alignment.

| Block | Baskets | Normal net | Normal PF | Normal max DD | Double-cost net | Double-cost PF |
|---|---:|---:|---:|---:|---:|---:|
| Development 2021 | 51 | +8.24% | 1.1772 | 11.42% | +4.00% | 1.0834 |
| Development 2022 | 53 | -19.55% | 0.4384 | 21.32% | -22.85% | 0.3733 |
| Validation 2023 | 52 | +3.36% | 1.1630 | 6.35% | -0.86% | 0.9618 |
| Validation 2024 | 52 | +5.16% | 1.2217 | 6.38% | +0.88% | 1.0353 |
| Validation 2025 | 52 | +3.27% | 1.1410 | 7.07% | -0.93% | 0.9626 |
| Validation Jan-Sep 2026 | 39 | -5.41% | 0.6965 | 10.44% | -8.31% | 0.5673 |
| Continuous validation | 195 | +6.17% | 1.0687 | 10.72% | -9.16% | 0.8994 |

Sample size, normal drawdown and concentration gates pass. The strategy fails development
consistency, both combined PF thresholds, all-block normal stability, stress stability and
positive stressed total return. January-September 2026 is negative even at base costs and the
aggregate edge disappears when costs double. Therefore `passes_historical_gate=false` and
`robust_candidate=false`; do not start forward PAPER and do not optimize weekdays, hour, holding
time or stop on the revealed blocks. No Render resource, deployed branch, paused bot or real
account was changed.

Next concrete step: preregister a non-calendar, single-market session-transfer hypothesis with
parameters fixed before testing; do not mine weekday or holding-window variants of this result.

## SESSION_TRANSFER_V1: distinct session-continuation hypothesis, rejected

The protocol was committed before historical results were read. At 08:00 UTC the model enters
BTC LONG after a completed 00:00–07:59 return of at least +0.75%, or SHORT after a return of at
most -0.75%. It exits at a 2.5% stop, 2.5% target or after eight elapsed hours, uses 20% of current
equity and never overlaps positions. This fixed-clock, single-market continuation premise is not
a modification of the rejected weekend, cross-asset, shock, flow, sweep, pair or monthly models.

The test used 73 public Binance Vision BTCUSDT 1-hour monthly archives from September 2020 through
September 2026. URLs, SHA256 fingerprints, coverage and ten excluded incomplete UTC dates are in
`session_transfer_results_20261023.json`; no bars were fabricated and signals cannot cross gaps.
Normal costs are 0.095% fee and 0.02% adverse slippage per side plus 8% annualized SHORT borrow;
stress doubles all three. Five deterministic tests passed for completed-session causality,
next-open entry, fixed exit, missing-data rejection, worse-open short gaps, stop-first ambiguity,
borrow and cost monotonicity.

| Block | Trades (L/S) | Normal net | Normal PF | Normal max DD | Double-cost net | Double-cost PF |
|---|---:|---:|---:|---:|---:|---:|
| Development 2021 | 224 (112/112) | -6.72% | 0.8422 | 10.05% | -15.81% | 0.6533 |
| Development 2022 | 169 (80/89) | -8.70% | 0.7057 | 8.89% | -16.53% | 0.5067 |
| Validation 2023 | 97 (50/47) | -2.22% | 0.8172 | 4.48% | -6.47% | 0.5556 |
| Validation 2024 | 147 (82/65) | -1.68% | 0.9193 | 4.25% | -8.28% | 0.6515 |
| Validation 2025 | 145 (77/68) | -8.07% | 0.6416 | 9.37% | -14.13% | 0.4473 |
| Validation Jan-Sep 2026 | 101 (44/57) | +1.48% | 1.1312 | 2.59% | -3.13% | 0.7662 |
| Continuous validation | 490 (253/237) | -10.31% | 0.8391 | 12.57% | -28.64% | 0.5822 |

Only total sample, both-direction sample and normal drawdown gates pass. Development consistency,
both PF thresholds, cross-block profitability, stress stability, stressed total return and
profit concentration fail. Therefore `passes_historical_gate=false` and
`robust_candidate=false`; do not start forward PAPER or tune the revealed UTC boundary, 0.75%
threshold, bracket or hold. No deployed branch, Render resource, paused bot or real account was
touched.

Next concrete step: preregister a structurally different spot-only volatility-contraction entry
with no shorting or fixed session boundary; do not reverse this failed continuation rule on the
same blocks.

## VOLATILITY_CONTRACTION_SPOT_V1: distinct spot volatility-regime hypothesis, rejected

The rules and gates were committed before historical results were read. A signal occurs only when
BTC's completed 168-hour realized volatility crosses from above to at most 65% of completed
720-hour volatility. The model buys 35% of equity at the next hourly open, holds at most 168
hours, uses an 8% stop and enforces a 168-hour cooldown. It is long-only and has no fixed session,
weekday, price breakout, flow, rank, pair spread, SHORT or monthly momentum rule.

The test used 73 public Binance Vision BTCUSDT 1-hour monthly archives from September 2020 through
September 2026. URLs, SHA256 fingerprints, coverage and ten removed incomplete UTC days are in
`volatility_contraction_spot_results_20261023.json`; no bars were filled and rolling windows cannot
cross gaps. Base costs are 0.095% fee and 0.02% adverse slippage per side; stress doubles both.
Five deterministic tests passed for causal regime crossing, next-open entry, time/cooldown
non-overlap, missing-data rejection, worse-open gap stops and cost monotonicity.

| Block | Trades | Normal net | Normal PF | Normal max DD | Double-cost net | Double-cost PF |
|---|---:|---:|---:|---:|---:|---:|
| Development 2021 | 6 | +0.69% | 1.0554 | 11.66% | +0.23% | 1.0181 |
| Development 2022 | 8 | +3.10% | 1.7748 | 5.45% | +2.45% | 1.5710 |
| Validation 2023 | 6 | -1.27% | 0.7227 | 5.75% | -1.74% | 0.6375 |
| Validation 2024 | 4 | -3.24% | 0.6330 | 8.69% | -3.53% | 0.6091 |
| Validation 2025 | 6 | +1.41% | 1.2973 | 4.05% | +0.93% | 1.1866 |
| Validation Jan-Sep 2026 | 2 | +0.38% | n/a | 2.37% | +0.22% | n/a |
| Continuous validation | 18 | -2.75% | 0.8456 | 12.39% | -4.12% | 0.7759 |

Development and normal drawdown gates pass, but the validation has only 18 trades versus the
fixed minimum 60. Combined return and both PF gates fail; 2023 and 2024 lose, stress stability
fails, and positive P&L is concentrated. Thus `passes_historical_gate=false` and
`robust_candidate=false`. Do not start forward PAPER or loosen the 0.65 crossing merely to create
more trades. No deployment, Render configuration, paused bot or real account was changed.

Next concrete step: preregister a distinct cross-asset beta-hedged residual-momentum portfolio
whose signal is not a pair z-score or cross-sectional winner rotation; do not retune this sparse
volatility event on the revealed blocks.

## BETA_HEDGED_RESIDUAL_MOMENTUM_V1: distinct hedged residual hypothesis, rejected

The 60-day beta model, ten-day residual threshold and gates were committed before results were
read. At each UTC day boundary it estimates ETH, SOL and XRP beta to BTC, selects the largest
absolute residual beyond 5%, and trades continuation with an opposite beta-weighted BTC leg.
Gross exposure is 35%, holding is at most ten days, cooldown five days and either leg has a 10%
adverse stop. This is neither SOL/ETH z-score reversion nor unhedged winner rotation.

The run used 292 public Binance Vision 1-hour archives from September 2020 through September
2026. URLs, SHA256 fingerprints, coverage and ten excluded incomplete UTC days are stored in
`beta_hedged_residual_results_20261023.json`; no candle was fabricated. Normal costs are 0.095%
fee and 0.02% adverse slippage per leg and side plus 8% annualized short borrow; stress doubles
all three. Four deterministic tests passed for completed-data selection, next-day entry,
beta-weighted two-leg non-overlap, worse-open gaps, borrow and cost monotonicity.

| Block | Pairs (alt L/S) | Normal net | Normal PF | Normal max DD | Double-cost net | Double-cost PF |
|---|---:|---:|---:|---:|---:|---:|
| Development 2021 | 10 (4/6) | +5.65% | 1.9882 | 6.68% | +4.68% | 1.7304 |
| Development 2022 | 33 (16/17) | -16.39% | 0.2084 | 17.06% | -19.10% | 0.1524 |
| Validation 2023 | 26 (15/11) | +1.27% | 1.0773 | 9.28% | -1.42% | 0.9213 |
| Validation 2024 | 32 (14/18) | -0.16% | 0.9929 | 12.05% | -3.40% | 0.8587 |
| Validation 2025 | 30 (15/15) | -16.00% | 0.1164 | 18.03% | -18.58% | 0.0698 |
| Validation Jan-Sep 2026 | 17 (8/9) | -6.30% | 0.2274 | 7.95% | -8.02% | 0.1328 |
| Continuous validation | 103 (51/52) | -22.81% | 0.6444 | 27.75% | -30.67% | 0.5462 |

Only sample-size and direction-balance gates pass. Development consistency, both PF gates,
cross-block stability, stress return, drawdown and concentration fail. Therefore
`passes_historical_gate=false` and `robust_candidate=false`. Do not start forward PAPER or tune
the beta/residual windows and threshold on these revealed blocks. No Render, deployed branch,
paused bot or real account was changed.

Next concrete step: preregister a structurally different volume-neutral range-harvest model with
explicit maker-like cost assumptions stress-tested against taker execution; do not reverse or
retune this failed residual continuation.

## RANGE_HARVEST_LIMIT_V1: distinct resting-limit range hypothesis, rejected

The protocol was committed before results were read. In a 20-day BTC regime with directional
efficiency at most 0.35, the model rests a one-day buy limit 0.5 ATR below prior close, targets
that close, stops one ATR below entry and holds at most 24 hours. Exposure is 25% and positions
cannot overlap. Base execution assumes a 0.02% maker entry and normal taker exit; stress assumes
0.19% fee and 0.04% adverse slippage on both sides.

The test used 73 public Binance Vision BTCUSDT 1-hour archives from September 2020 through
September 2026. Provenance hashes, coverage and ten removed incomplete UTC days are in
`range_harvest_limit_results_20261023.json`; no bars were synthesized. Four engine tests passed
for completed-data setup, delayed limit fill, maximum holding time, worse-open gap stop and cost
stress monotonicity. Same-bar fill/target credit is prohibited and stop wins.

| Block | Trades | Base net | Base PF | Base max DD | Taker-stress net | Stress PF |
|---|---:|---:|---:|---:|---:|---:|
| Development 2021 | 59 | -4.01% | 0.8347 | 8.14% | -8.50% | 0.6678 |
| Development 2022 | 89 | -4.75% | 0.8148 | 10.26% | -11.39% | 0.5937 |
| Validation 2023 | 69 | -0.64% | 0.9515 | 5.62% | -6.06% | 0.6048 |
| Validation 2024 | 77 | -11.62% | 0.5524 | 13.05% | -16.98% | 0.3939 |
| Validation 2025 | 84 | -4.09% | 0.7905 | 5.22% | -10.42% | 0.5272 |
| Validation Jan-Sep 2026 | 56 | -4.66% | 0.6085 | 5.77% | -8.90% | 0.3767 |
| Continuous validation | 286 | -19.71% | 0.7019 | 20.93% | -36.35% | 0.4717 |

Only sample size passes. Development, every validation block, both PF gates, stress stability,
drawdown and concentration fail. Therefore `passes_historical_gate=false` and
`robust_candidate=false`. Do not start forward PAPER or tune the range/ATR settings on these
blocks. No deployment, Render setting, paused bot or real account was changed.

Next concrete step: begin a fresh research family only after preregistering data and evaluation
periods not selected to repair any of today's failed signals; retain all failures as benchmarks.

## BNB_VOLUME_DRYUP_V1: distinct seller-exhaustion hypothesis, rejected

The hypothesis, BNB-only data set, 48-hour decline, six-versus-48-hour quote-volume contraction,
execution rules, chronological blocks and gates were committed before historical results were
read. The model buys 25% of equity at the next hourly open after a return at most -3% and volume
ratio at most 0.70, with a 4% stop, 6% target, 36-hour maximum hold and 24-hour cooldown. It is a
single-asset post-decline supply-exhaustion event, not a variant of rejected flow pressure,
cross-market shock rebound, range-limit or portfolio momentum.

The run used 71 public Binance Vision `BNBUSDT` 1-hour archives from November 2020 through
September 2026. URLs, SHA256 fingerprints and per-month missing-candle counts are stored in
`bnb_volume_dryup_results_20261024.json`. Eight early development archives contain 19 missing
hours in total; no validation archive is incomplete, no candle was fabricated, and signals whose
required history crossed a gap were prohibited. Four deterministic tests passed for completed
history, next-bar entry, non-overlap/cooldown, worse-open gap stops and cost monotonicity.

| Block | Trades | Normal net | Normal PF | Normal max DD | Double-cost net | Double-cost PF |
|---|---:|---:|---:|---:|---:|---:|
| Development 2021 | 73 | +2.78% | 1.0781 | 7.74% | -1.20% | 0.9677 |
| Development 2022 | 62 | -5.66% | 0.7953 | 8.94% | -8.81% | 0.6973 |
| Development 2023 | 38 | -0.99% | 0.8738 | 6.24% | -3.11% | 0.6499 |
| Validation 2024 H1 | 25 | -1.53% | 0.8298 | 4.16% | -2.89% | 0.7007 |
| Validation 2024 H2 | 24 | +1.63% | 1.1828 | 2.65% | +0.30% | 1.0315 |
| Validation 2025 H1 | 21 | +2.01% | 1.3391 | 3.07% | +0.82% | 1.1260 |
| Validation 2025 H2 | 23 | +4.80% | 1.7775 | 2.53% | +3.46% | 1.5308 |
| Validation Jan-Sep 2026 | 29 | -3.10% | 0.7167 | 5.74% | -4.65% | 0.6012 |
| Continuous validation | 122 | +3.68% | 1.0882 | 5.74% | -3.13% | 0.9280 |

Sample size and normal drawdown pass, but development consistency, both combined PF gates,
normal and stress block stability, combined stress return and profit-concentration gates fail.
The superficially positive normal validation therefore does not qualify; double costs reverse it.
Thus `passes_historical_gate=false` and `robust_candidate=false`. Do not start forward PAPER or
retune the thresholds on the revealed BNB blocks. No deployment, Render setting, paused bot or
real account was changed.

Next concrete step: preregister a new data source or market mechanism rather than adjusting this
volume-dry-up event; retain its 2024–2026 blocks as permanently revealed validation evidence.

## ETH_FUNDING_EXTREME_REVERSAL_V1: distinct derivatives-crowding hypothesis, rejected

The funding threshold, contrarian direction, position/risk rules, chronological blocks and gates
were committed before results were read. An archive-format check then revealed that Binance
records some nominal funding settlements a few milliseconds after the hour. Before rerunning the
history, a documented normalization of offsets up to one second was committed; it changes no
signal value or strategy parameter. The model enters opposite an absolute funding rate of at
least 0.020% at the next hourly open, uses 20% equity, a 5% stop, 3% target, 24-hour maximum hold
and eight-hour cooldown. This is a derivatives crowding/carry mechanism, not a spot signal.

The completed run used 140 public Binance Vision ETHUSDT USD-M archives: 70 hourly-price and 70
funding-rate files from December 2020 through September 2026. All 51,120 expected hourly bars
were present; 6,390 funding records, URLs and both archive SHA256 hashes are stored in
`eth_funding_extreme_results_20261024.json`. No candle or funding rate was fabricated. Six tests
passed for settlement normalization, next-hour causality, contrarian direction, non-overlap,
worse-open gaps, actual funding cashflows and adverse stress behavior.

| Block | Trades (L/S) | Normal net | Normal PF | Normal max DD | Stress net | Stress PF |
|---|---:|---:|---:|---:|---:|---:|
| Development 2021 | 186 (4/182) | -6.91% | 0.8846 | 13.76% | -12.30% | 0.7986 |
| Development 2022 | 22 (22/0) | -1.33% | 0.8333 | 3.05% | -1.90% | 0.7684 |
| Development 2023 | 21 (0/21) | +2.91% | 1.7892 | 1.24% | +2.25% | 1.5764 |
| Validation 2024 H1 | 34 (0/34) | -0.70% | 0.9128 | 5.25% | -0.61% | 0.9232 |
| Validation 2024 H2 | 16 (0/16) | +0.01% | 1.0034 | 2.82% | -0.45% | 0.9007 |
| Validation 2025 H1 | 1 (1/0) | +0.58% | n/a | 0.44% | +0.55% | n/a |
| Validation 2025 H2 | 0 (0/0) | 0.00% | n/a | 0.00% | 0.00% | n/a |
| Validation Jan-Sep 2026 | 4 (4/0) | +0.47% | 1.7009 | 1.07% | +0.37% | 1.5015 |
| Continuous validation | 55 (5/50) | +0.36% | 1.0278 | 5.25% | -0.14% | 0.9892 |

Only the drawdown gate passes. Development consistency, sample size, direction balance, both PF
gates, normal/stress block stability, combined stress return and concentration all fail. Funding
regimes also became too sparse after 2024 for the fixed threshold. Therefore
`passes_historical_gate=false` and `robust_candidate=false`. Do not lower the revealed funding
threshold or start forward PAPER. No deployment, Render setting, paused bot or real account was
changed.

Next concrete step: use an independently preregistered mechanism and data rather than lowering
this sparse funding threshold; retain all funding periods as revealed evidence.
