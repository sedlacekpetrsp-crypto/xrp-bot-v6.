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

## BTC_LEAD_LAG_IMPULSE_V1: rejected (2026-10-25)

The rules and gates were frozen in the preceding GitHub commit before performance evaluation. This distinct cross-market hypothesis bought XRP after a large positive BTC hourly move that XRP had not matched. It used next-open entries, 24-hour ATR brackets, six-hour maximum holding, one 20%-notional position, 0.5% stop-risk sizing, gap-stop and adverse intrabar handling, 9.5 bps fees plus 2 bps slippage per side, and doubled-cost stress.

On 114 real Binance Vision monthly archives (BTC/XRP 1h, January 2022–September 2026), the four annual OOS folds produced only 50 trades, -$173.72 net, PF 0.730, versus -$373.47 and PF 0.509 under doubled costs. Only 2023 was base-cost positive; even that fold lost under stress. The 2022 control and 2024–2026 folds lost. The completed result fails sample, profitability, stress, stability, final-period, and concentration gates; it is not eligible for forward PAPER promotion. Exact provenance, SHA256 hashes, full ledgers, audit and limitations are in `research/btc_lead_lag_validation_20261025/` and `research/btc_lead_lag_protocol.md`.

Next concrete step: freeze and test a genuinely different mechanism, preferably one with new information beyond OHLC cross-market momentum; do not tune lead/lag thresholds on the now-observed folds. PAPER-only constraints remain unchanged.

## XRP_RESIDUAL_SNAPBACK_V1: rejected (2026-10-25)

The zero-intercept BTC/ETH factor-residual mean-reversion rules and gates were frozen in commit `88f4039600997677b804db077e9d3a091ef170aa`, before evaluation. On 171 actual Binance Vision archives (XRP/BTC/ETH 1h, Jan 2022–Sep 2026), all 35 code tests and the independent ledger audit passed. Mechanics success is not profitability evidence.

The four annual OOS folds contain 231 non-overlapping trades: -$2,029.15, PF 0.563, expectancy -$8.78; doubled costs: -$3,007.28, PF 0.424, expectancy -$13.02. All four OOS years and the 2022 control lost. Continuous base/stress drawdowns were 20.16%/27.74%. Only sample size passed; the candidate fails all profit, stress, stability, final-fold, drawdown and concentration gates. It is rejected without parameter retuning or forward promotion. Full provenance, hashes, metrics, ledger and audit are in `research/residual_snapback_validation_20261025/`.

Next concrete step: do not continue OHLC-only XRP/BTC/ETH relative-return variants on this reused history. Freeze a distinct hypothesis based on a different observable mechanism before testing. PAPER-only and production-isolation constraints remain unchanged.

## XRP_LARGE_TRADE_FOLLOWTHROUGH_V1: rejected (2026-10-25)

This candidate used Binance quote volume per reported trade as a distinct observable for large-trade participation. Rules were frozen in `466679ca08c11cbc074893a161e4acc5d2580d8a`; a real zero-activity row and adjacent missing hour caused ingestion to stop before results, so the no-imputation gap policy was documented in `e2495aa2f59e69a32f893fe943d11b9b6e54a540` before rerunning.

Across 57 real XRPUSDT hourly archives, 155 annual-fold OOS trades lost -$794.78, PF 0.669, expectancy -$5.13; doubled costs lost -$1,452.17, PF 0.486, expectancy -$9.37. Every OOS year and the control lost. All 41 code tests and independent ledger audit passed, but only the sample gate passed. Full provenance, results, ledger and audit are in `research/large_trade_followthrough_validation_20261025/`. Reject without retuning or forward promotion.

Next concrete step: avoid further variants based on one-hour continuation after volume/trade-size anomalies on this history; investigate a genuinely different mechanism and preregister it. PAPER-only isolation remains unchanged.

## MULTI_STABLE_PEG_REVERSION_V1: rejected (2026-10-25)

The distinct stablecoin redemption-anchor hypothesis was frozen in commit `31769d0b11fe8db9fea692f1fe55bc3ca695b55c`. Ninety-nine real Binance Vision archives for USDCUSDT, FDUSDUSDT and TUSDUSDT had complete Jan 2024–Sep 2026 15m coverage. All 46 code tests and the independent equal-sleeve audit passed.

The locked quarterly OOS screen found only 8 base trades, -$14.58, PF 0.292, expectancy -$1.82; double-cost stress found 13 path-dependent trades, -$42.09, PF 0.084, expectancy -$3.24. USDC did not reach the preregistered dislocation, and the FDUSD/TUSD trades lost. Only drawdown passed. Reject for inadequate sample and negative base/stress evidence; do not loosen thresholds on these observed quarters. Complete provenance, results and ledgers are in `research/stable_peg_validation_20261025/`.

Next concrete step: retain the no-retuning rule; use a distinct mechanism with a naturally larger event sample and freeze it before evaluation. PAPER-only isolation remains unchanged.

## XRP_OI_CROWDING_UNWIND_V1: rejected (2026-10-25)

The derivatives-positioning hypothesis and gates were frozen before performance evaluation, with two ingestion-only no-imputation amendments recorded before rerunning. The completed screen used 1,004 real Binance Futures metrics archives and 33 real Binance spot 5m archives from January 2024 through September 2026. Source URLs, byte counts and local SHA256 fingerprints are preserved with the output. Seventy-one invalid required-metric rows were excluded; gaps were retained and causal lookbacks crossing them were suppressed.

Across the seven locked OOS quarters, 111 base-cost trades lost $579.90, PF 0.5843, expectancy -$5.22. Doubled costs produced 112 path-dependent trades and lost $1,074.52, PF 0.3745, expectancy -$9.59. Only one quarter was positive and final 2026 Q3 lost. Continuous OOS drawdown was 6.46% base and 11.00% stressed. Every frozen gate failed, including the 150-trade minimum. All 52 repository tests and an independent ledger audit passed, which establishes mechanics rather than profitability. Full results, provenance, compressed ledger and audit are in `research/oi_crowding_validation_20261025/`.

Reject without threshold retuning or forward promotion. Next concrete step: preregister a genuinely different observable mechanism, reserve new forward data, and avoid further OI/long-short/taker-crowding variants on these observed quarters. PAPER-only and production-isolation constraints remain unchanged.

## XRP_FUNDING_DISLOCATION_REVERSAL_V1: rejected (2026-10-25)

Rules and gates were frozen before evaluation. Initial ingestion then stopped before performance because publisher funding timestamps had 1–31 ms offsets from nominal hours; a normalization-only amendment was committed before rerunning. The completed validation used 57 real Binance funding archives and 57 real spot 1h archives from January 2022 through September 2026, with URLs, byte counts and local SHA256 fingerprints in the result. There were no duplicates or unexpected funding gaps. One missing spot hour was retained without imputation and no position crossed it.

Across 15 locked OOS quarters, 321 base-cost trades lost $1,403.59, PF 0.7585, expectancy -$4.37. Doubled costs lost $2,754.20, PF 0.5855, expectancy -$8.58. Only four quarters were positive and final 2026 Q3 lost. Continuous OOS drawdown was 15.26% base and 25.26% stressed. Only the sample gate passed. All 58 repository tests and the independent ledger audit passed, establishing implementation consistency rather than an edge. Complete provenance, results, ledger and audit are in `research/funding_reversal_validation_20261025/`.

Reject without retuning or forward promotion. Next concrete step: move away from derivatives-crowding variants and preregister a strategy based on a genuinely new observable data family, with fresh forward evidence reserved before any acceptance. PAPER-only isolation remains unchanged.

## ALT_BREADTH_CAPITULATION_REVERSAL_V1: rejected (2026-10-26)

The fixed eight-market breadth rules and acceptance gates were committed before evaluation. Validation used 513 actual Binance Vision monthly spot archives for XRP plus BTC, ETH, BNB, SOL, ADA, DOGE, LINK and LTC from January 2022 through September 2026. URLs, byte counts and local SHA256 fingerprints are preserved. No duplicates were found. A single exchange-wide missing hour was retained without imputation; no signal lookback or position crossed it.

Across 15 locked OOS quarters, 405 base-cost trades lost $1,549.54, PF 0.8500, expectancy -$3.83. Doubled costs produced 406 path-dependent trades and lost $3,112.40, PF 0.7243, expectancy -$7.67. Five quarters were positive and final 2026 Q3 lost. Continuous drawdown was 20.21% base and 28.71% stressed. Only sample size passed. All 64 repository tests and an independent ledger audit passed, establishing implementation consistency rather than profitability. Complete provenance, results, ledgers and audit are in `research/breadth_capitulation_validation_20261026/`.

Reject without retuning or forward promotion. Next concrete step: avoid threshold variants of this market-breadth capitulation idea on the now-observed periods; freeze a different mechanism before testing and reserve new forward evidence. PAPER-only and production isolation remain unchanged.

## XRP_CONTINUOUS_PREMIUM_RECOVERY_V1: rejected (2026-10-26)

The continuous mark/index-premium recovery rule and gates were committed before evaluation. Validation used 114 real Binance Vision monthly archives from January 2022 through September 2026 with complete URLs, byte counts and local SHA256 fingerprints. Exact timestamp alignment excluded one premium-only and 48 spot-only hours. One one-hour and two 24-hour gaps were retained without imputation; full causal windows suppressed affected signals and no position crossed a gap.

Across 15 locked OOS quarters, 81 base-cost trades earned $146.06, PF 1.0921, expectancy $1.80. This still fails the minimum sample and PF gates. Under doubled costs the same 81 trades lost $199.02, PF 0.8882, expectancy -$2.46. Nine quarters were positive and final 2026 Q3 was positive, but the required ten-quarter stability and concentration gates failed. Continuous drawdown passed at 3.90% base and 5.05% stress; the 2022 control lost. All 70 repository tests and the independent audit passed. Full provenance, results and ledgers are in `research/premium_recovery_validation_20261026/`.

Reject without retuning or forward promotion: nominal profitability alone is insufficient, especially when it disappears under realistic cost stress. Next concrete step: retain this as a documented near-signal but test a genuinely different preregistered mechanism on new evidence. PAPER-only and production isolation remain unchanged.

## XRP_ILLIQUIDITY_SHOCK_REVERSAL_V1: rejected (2026-10-26)

This distinct Amihud-style hypothesis bought XRP after an extreme negative hourly return per reported USDT of spot quote volume. Rules and gates were frozen before evaluation. A zero-volume archive row stopped the first attempt before performance; the no-imputation rule retaining that row, preserving the adjacent missing hour and suppressing affected causal windows was separately committed before rerunning.

Across 57 real Binance Vision XRPUSDT hourly archives and 15 quarterly OOS folds, 213 base-cost trades lost $1,065.48, PF 0.7475, expectancy -$5.00. Doubled costs lost $2,020.26, PF 0.5800, expectancy -$9.48. Only 6/15 quarters were positive; continuous base/stress drawdown was 12.76%/19.03%. The 2022 control lost at both cost levels. All 77 code tests and 8,448 independent audit checks passed, establishing mechanics rather than profitability. Complete provenance, local SHA256 fingerprints, metrics, compressed ledgers and audit are in `research/illiquidity_reversal_validation_20261026/`.

Reject without retuning the now-observed return/impact thresholds or forward promotion. Next concrete step: freeze a genuinely different mechanism not based on single-market hourly price impact, while reserving future data for independent PAPER evidence. Production, Render and LIVE remain untouched.

## XRP_ORDERBOOK_DEPTH_IMBALANCE_V1: rejected (2026-10-26)

This distinct passive-liquidity hypothesis used published XRP perpetual-futures depth at +/-1% and spot execution. Rules were committed before evaluation; after the initial download stopped on HTTP 404, the no-imputation missing-archive rule was separately committed before rerunning.

The completed ingestion covered 1,004 requested daily depth archives and 33 monthly spot archives, with 1,036 actual SHA256 fingerprints and one explicit missing depth day. The frozen exact 59:30 snapshot existed in only 4,021 of 24,096 spot hours, creating 2,557 gaps and no consecutive 720-hour causal history. Consequently V1 generated 0 control and 0 OOS trades and decisively failed the 150-trade sample and all profit/stability gates. Zero P/L/drawdown is not positive evidence. All 83 repository tests passed; the independent audit correctly found an empty ledger and verified manifest counts. Full provenance and quality output are in `research/orderbook_depth_validation_20261026/`.

Reject V1 without post-result timestamp relaxation. Any later order-book study must be a separately named, preregistered design using a causal cadence rule calibrated outside its evaluation interval. No forward promotion; production, Render and LIVE remain untouched.

## XRP_ATTENTION_SHARE_SURGE_V1: rejected (2026-10-26)

This distinct hypothesis used XRP's share of reported USDT quote volume in a frozen BTC/ETH/BNB/SOL/XRP basket as a measure of market attention. Rules and gates were committed before performance evaluation. The test used 285 real Binance Vision monthly spot archives from January 2022 through September 2026, with 41,615 aligned hours per market, no duplicates or omissions, and one preserved exchange-wide missing hour. Source URLs and local SHA256 fingerprints are retained.

Across four annual OOS folds, 172 base-cost trades lost $964.12, PF 0.7981, expectancy -$5.61. Doubled costs lost $1,570.53, PF 0.6926, expectancy -$9.13. Every OOS year and the 2022 control lost; continuous drawdown was 12.74% base and 17.18% stressed. Only sample size passed. All 89 repository tests and 5,082 independent audit checks passed, establishing mechanics rather than profitability. Full evidence is in `research/attention_share_validation_20261026/`.

Reject without retuning the percentile or basket and without forward promotion. Next work must use a genuinely different information mechanism and retain independent future PAPER evidence. Production, Render and LIVE remain untouched.

## XRP_SPOT_PERP_CARRY_V1: rejected (2026-10-27)

The equal-notional long-spot/short-perpetual carry rules and gates were frozen in commit `995eca12a921d31bd20f2cb9b08939013ccc3524` before performance evaluation. Unlike the earlier directional funding-reversal study, this candidate attempted to collect actual subsequent funding cashflows while hedging XRP direction.

Validation used 171 real Binance Vision monthly spot, mark-price, and funding archives from January 2022 through September 2026. Exact URLs, byte counts, row counts, and local SHA256 fingerprints are preserved. Exact timestamp intersection produced 41,543 aligned hours. Seventy-two spot-only and one mark-only hours were excluded; four resulting gaps were retained without imputation and no position crossed a gap.

The annual OOS folds produced 139 base-cost trades and lost $3,685.19, PF 0.000, expectancy -$26.51. Doubled costs lost $4,065.49, PF 0.000, expectancy -$29.25. The separately reported continuous OOS path lost $3,471.87 base and $3,799.54 stressed, with 34.72%/38.00% conservative drawdowns. There were no profitable trades under the frozen pair-stop methodology; 2026 produced no signals. All 99 repository tests and 3,918 independent ledger checks passed, proving arithmetic consistency rather than an edge.

Reject without retuning carry thresholds, holding time, or the preregistered conservative spread stop. Complete results, limitations, provenance, compressed ledger, audit, and reproduction commands are in `research/spot_perp_carry_validation_20261027/`. No forward promotion. Next investigate a separately preregistered forced-liquidation-event mechanism only if a complete, free, traceable source is available. Production, Render and LIVE remain untouched.
