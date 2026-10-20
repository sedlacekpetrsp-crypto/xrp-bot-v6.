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
