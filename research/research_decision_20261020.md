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
