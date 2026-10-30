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

## XRP_VOLATILITY_COMPRESSION_BREAKOUT_V1: rejected (2026-10-27)

The intended forced-liquidation data family was checked first. Six official Binance Vision daily liquidationSnapshot paths spanning 2022–2026 all returned HTTP 404, so no liquidation strategy was registered and no candle-wick proxy was fabricated. The availability evidence is in `research/liquidation_source_check_20261027.md`.

The separate low-realized-volatility breakout hypothesis and gates were then frozen in commit `024248052292806e075fa72a37144f46cdeceef9` before evaluation. Validation used 57 real Binance Vision XRPUSDT hourly archives from January 2022 through September 2026. All 41,615 bars were unique. One missing hour was retained without imputation and causal histories crossing it were suppressed. URLs, byte counts, row counts, and local SHA256 fingerprints are preserved.

The four annual OOS folds produced 61 trades, -$142.56 net, PF 0.889, and -$2.34 expectancy. Doubled costs lost $394.26, PF 0.729, expectancy -$6.46. The continuous path lost $149.42 base and $395.89 stressed, with 6.34%/7.76% drawdown. Although 2025 and 2026 were positive and drawdown passed, 2023–2024 and the 2022 control lost, the sample missed the frozen 100-trade minimum, and aggregate base and stress profitability failed. Selecting only recent years is prohibited.

All 108 repository tests and 2,056 independent ledger checks passed, demonstrating consistent mechanics rather than an edge. Complete results and ledgers are in `research/volatility_compression_validation_20261027/`. Reject without retuning and without forward promotion. Next assess actual synchronized `bookTicker` coverage for a separately preregistered triangular-dislocation mechanism; do not substitute candle closes if top-of-book data are unavailable. Production, Render and LIVE remain untouched.

## XRP_AGGRESSOR_SELL_BURST_REVERSAL_V1: rejected (2026-10-27)

The planned triangular-dislocation study was not registered because Binance Vision does not provide the required synchronized spot bookTicker legs; substituting candle closes would fabricate executability. That source decision is recorded separately. A distinct raw-tick hypothesis was then frozen in commit `4398ded3f6913c3d6da958abfc9fe52f0acdfec8`: buy after a one-minute fall dominated by a long uninterrupted seller-initiated aggregate-trade run.

Ingestion stopped twice before any performance result. The February 2026 publisher CSV contained two ordering reversals, documented before correction in commit `52c9f993f8888b0f4b2bdba6cfd38c8cb48a90c5`, then 4,000 byte-identical duplicate rows, documented before exact-only deduplication in `27dd04265c6f85f7cd5f5caf78078c77e91aa798`. Strategy parameters never changed. The completed dataset contains 414,445,018 unique events from 57 real monthly archives (6.392 GB compressed) and 2,496,807 derived minute bars. URLs, source SHA256, counts and corrections are retained; no missing price was fabricated.

The annual OOS folds produced 1,553 trades, -$7,499.05, PF 0.316, expectancy -$4.83. Doubled costs lost $12,650.79, PF 0.129, expectancy -$8.15. Every OOS year and calendar month lost. The continuous path lost $5,671.63 base and $7,856.47 stressed, with 56.80%/78.60% drawdown. Only the sample gate passed. All 118 repository tests and 53,233 independent audit checks passed, establishing mechanical consistency rather than an edge.

Reject without inversion or threshold retuning and without forward promotion. Full provenance, results, compressed ledger, audit, limitations and reproduction commands are in `research/aggressor_sell_burst_validation_20261027/`. Next leave Binance aggressor-flow variants and verify a complete second-exchange source before preregistering a cross-exchange premium mechanism. Production, Render and LIVE remain untouched.

## XRP_CROSS_EXCHANGE_RESIDUAL_CONVERGENCE_V1: rejected (2026-10-27)

The second-exchange source was verified first, and the BTC-basis-adjusted Coinbase/Binance residual rules and gates were saved remotely before evaluation. Direct Coinbase Exchange XRP-USD/BTC-USD candles were exactly intersected with Binance Vision XRPUSDT mark-price and BTCUSDT spot candles; actual Binance XRP funding cashflows were included. URLs, byte counts, local SHA256 payload fingerprints, counts, exclusions and gaps are retained. No missing candle was synthesized.

Only one locked OOS trade occurred, in 2024-Q4. Its next open was already beyond the frozen stop, so gap-stop execution lost $15.60 after base costs (PF 0.0), and $31.20 when every fee and slippage assumption was doubled (PF 0.0). All other OOS quarters and the H2-2023 control had zero trades. The candidate therefore fails the 120-trade sample gate and every profit, stress, stability, final-quarter and concentration gate; only drawdown passes because exposure was almost absent. Zero P/L from no trading is not evidence of an edge.

All 124 repository tests and the independent ledger audit passed, establishing mechanics rather than profitability. Full evidence is in `research/cross_exchange_residual_validation_20261027/`. Reject without loosening the observed residual threshold or forward promotion. Next preregister a genuinely different, naturally denser observable rather than mining this cross-exchange period. Production, Render and LIVE remain untouched.

## XRP_LEDGER_ACTIVITY_BREADTH_V1: rejected (2026-10-27)

This genuinely different candidate used CoinMetrics Community XRP active-address and transaction counts, with a conservative full-day publication lag, combined with Binance Vision daily spot execution. Protocol and exact nearest-rank percentile definition were committed before performance evaluation. Direct source URLs, payload/archive sizes, local SHA256 fingerprints, counts and gaps are retained; no missing observation was fabricated.

The four annual OOS folds produced only 35 trades. They earned $221.17, PF 1.370 and $6.32 expectancy at base costs; doubled costs earned $188.37, PF 1.306 and $5.38 expectancy. Three of four years, including 2026, were positive at both cost levels, but 2025 lost. The descriptive continuous path had 35 trades, +$331.43/PF 1.537 base and +$296.86/PF 1.469 stress, with 3.75%/3.86% drawdown. The 2022 control lost at both costs.

The frozen sample gate required 80 OOS trades, so the positive aggregate history is insufficient and the candidate is rejected without forward promotion. Do not lower the sample threshold or tune against 2025. All 131 repository tests and the independent ledger audit passed. Complete evidence is in `research/ledger_activity_breadth_validation_20261027/`. Next preserve this as a near-signal and seek materially more independent on-chain evidence through a separately preregistered design. Production, Render and LIVE remain untouched.

## XRP_NETWORK_FEE_PRESSURE_V1: rejected (2026-10-27)

This separately preregistered on-chain hypothesis used CoinMetrics Community total XRP fee burn per value-transfer transaction with a full-day publication lag, then executed on direct Binance Vision daily spot data. URLs, payload/archive sizes, local SHA256 fingerprints, counts and gaps are retained; no missing observation was fabricated.

The four annual OOS folds produced 86 trades and lost $303.33, PF 0.825 and -$3.53 expectancy at base costs. Doubled costs lost $426.47, PF 0.764 and -$4.96 expectancy. Only 2023 was profitable; 2024, 2025, 2026 and the 2022 control lost. The continuous path lost $304.25 base and $423.41 stressed, with 5.50%/6.61% drawdown. Every frozen gate except drawdown failed, including the 100-trade minimum.

All 137 repository tests and the independent ledger audit passed. Complete evidence is in `research/network_fee_pressure_validation_20261027/`. Reject without inversion or threshold retuning and without forward promotion. Do not mine the same fee series further; retain the separate activity-breadth near-signal only for genuinely independent future evidence. Production, Render and LIVE remain untouched.

## STABLECOIN_LIQUIDITY_IMPULSE_XRP_V1: rejected (2026-10-28)

This distinct macro-liquidity hypothesis used direct CoinMetrics Community USDT+USDC circulating supply and direct Binance Vision XRP daily spot data from January 2020 through September 2026. Rules and gates were committed before evaluation. Both stablecoin observations were required on an exact date; metrics had a full-day publication lag, and no value was carried forward or interpolated. URLs, byte sizes, local SHA256 fingerprints, counts and gaps are retained.

The five annual OOS folds produced 50 trades and earned $336.53, PF 1.350 and $6.73 expectancy at base costs; doubled costs earned $285.28, PF 1.289 and $5.71 expectancy. Only 2023 and 2024 were positive. Years 2022, 2025 and 2026 lost at both costs, and profit was too concentrated in 2024. The continuous path earned $328.70 base and $276.51 stress, with 3.09%/3.37% drawdown.

Despite positive aggregate history, the 75-trade sample, four-positive-year, final-2026 and concentration gates failed. Reject without selecting 2024 or retuning supply/holding thresholds and without forward promotion. All 143 repository tests and the independent audit passed. Complete evidence is in `research/stablecoin_liquidity_impulse_validation_20261028/`. Next preserve this only as a near-signal pending genuinely independent evidence and move new hypotheses to another mechanism. Production, Render and LIVE remain untouched.

## XRP_REALIZED_VALUE_DISCOUNT_V1: rejected (2026-10-28)

This separately preregistered valuation hypothesis bought XRP when the direct CoinMetrics Community market-value-to-realized-value ratio was at or below 0.90, with a full-day publication lag, and executed on direct Binance Vision daily spot archives. The 2,466 metric observations and 2,465 price observations aligned on 2,465 dates without gaps or duplicates; one metric-only endpoint was excluded. Exact URLs, byte sizes, local SHA256 fingerprints and ledgers are retained, and no missing value was fabricated.

The five annual OOS folds produced only 32 base-cost trades. They earned $641.46, PF 2.015 and $20.05 expectancy; doubled costs produced 33 path-dependent trades, +$480.47, PF 1.657 and $14.56 expectancy. The continuous path earned $680.93 base and $516.59 stressed, with 1.78%/1.83% drawdown. However, 2022 lost and 2025 generated no trades, so the fixed 75-trade and four-positive-year gates failed. Zero exposure is not a profitable year.

Reject without lowering the sample threshold or tuning the observed MVRV discount and exits. All 149 repository tests and 1,330 independent audit checks passed. Complete evidence is in `research/realized_value_discount_validation_20261028/`. Preserve this as a near-signal only; it is not promoted to forward PAPER. Next work must use a different preregistered mechanism or genuinely independent future observations. Production, Render and LIVE remain untouched.

## XRP_HOLDER_GROWTH_DIVERGENCE_V1: rejected (2026-10-28)

This separately preregistered fundamental-divergence hypothesis required at least 1% thirty-day growth in the count of nonzero-balance XRP addresses while XRP price fell at least 10%. Direct CoinMetrics Community `AdrBalCnt` and Binance Vision daily spot data were joined only on exact dates with a full-day metric lag. The 2,466 metric rows and 2,465 price rows aligned on 2,465 dates without gaps or duplicates; one metric-only endpoint was excluded. Exact URLs, byte counts, local SHA256 fingerprints and ledgers are retained.

The five annual OOS folds produced 31 trades, +$85.59, PF 1.107 and $2.76 expectancy. Doubled costs produced +$17.32, PF 1.021 and $0.56 expectancy. The continuous path earned $93.54 base and $28.07 stressed, with 2.43%/2.57% drawdown. However, the 75-trade minimum and PF >1.15 gate failed. Years 2023 and 2024 lost at both costs, so only three of five annual folds were positive.

Reject without lowering the sample/PF requirements, selecting recent years or tuning the two observed thresholds. All 155 repository tests and 1,370 independent audit checks passed. Complete evidence is in `research/holder_growth_divergence_validation_20261028/`. It is not promoted to forward PAPER. Next research must move away from holder-count/price-divergence variants or wait for genuinely independent future observations. Production, Render and LIVE remain untouched.

## XRP_BROAD_DOLLAR_DOWNTREND_V1: rejected (2026-10-28)

This separately preregistered external-macro hypothesis bought XRP after at least a 1.5% twenty-observation decline in the FRED broad trade-weighted U.S. dollar index. Each value was delayed until the second subsequent valid FRED observation, weekends and holidays were not filled, and entry occurred at the next XRP daily open. Direct FRED CSV and 81 Binance Vision archives supplied 1,688 valid macro observations and 2,465 consecutive spot days. Seventy-three explicit FRED missing-value rows were excluded without interpolation. Exact URLs, byte counts, local SHA256 fingerprints and ledgers are retained.

The five annual OOS folds produced 35 trades and lost $284.45, PF 0.654 and -$8.13 expectancy. Doubled costs lost $321.63, PF 0.620 and -$9.19 expectancy. The continuous path lost $268.23 base and $304.45 stressed, with 3.92%/4.16% drawdown. Only 2023 and 2025 were positive; 2022, 2024 and final 2026 lost at both costs. Every frozen gate except drawdown failed.

Reject without inverting the observed signal, selecting profitable years or tuning the macro lookback/threshold. All 161 repository tests and 1,394 independent audit checks passed. Complete evidence is in `research/broad_dollar_downtrend_validation_20261028/`. It is not promoted to forward PAPER. Next research must use a distinct mechanism or genuinely independent future observations. Production, Render and LIVE remain untouched.

## XRP_VIX_SHOCK_RECOVERY_V1: rejected (2026-10-28)

This separately preregistered external-risk hypothesis bought XRP after VIX had been at least 25 and then retreated at least 20% over five valid observations. Each value was delayed until the second subsequent valid FRED observation; weekends, holidays and 32 explicit missing values were not filled. Direct FRED CSV and 81 Binance Vision archives supplied 1,729 valid VIX observations and 2,465 consecutive XRP spot days. Exact URLs, byte counts, local SHA256 fingerprints and ledgers are retained.

The five annual OOS folds produced only 11 trades, +$183.67, PF 2.582 and $16.70 expectancy. Doubled costs earned $174.04, PF 2.451 and $15.82 expectancy. The continuous path earned $209.64 base and $199.82 stressed, with 0.84%/0.86% drawdown. However, 2023 had no trade, 2025 lost at both cost levels, and February 2022 supplied too much of positive-month profit. The frozen 75-trade, four-positive-year and concentration gates failed.

Reject despite positive aggregate history. Do not lower the sample threshold, count zero exposure as a profitable year or tune the observed VIX thresholds. All 167 repository tests and 596 independent audit checks passed. Complete evidence is in `research/vix_shock_recovery_validation_20261028/`. It is not promoted to forward PAPER; reconsideration requires genuinely new independent VIX shocks under unchanged rules. Production, Render and LIVE remain untouched.

## XRP_REAL_YIELD_EASING_V1: rejected (2026-10-29)

This separately preregistered external-rates hypothesis bought XRP after the FRED ten-year real Treasury yield declined at least 0.25 percentage point over 20 valid observations. Each observation was delayed until the second subsequent valid FRED observation; missing observations were not filled. Direct FRED data and 81 Binance Vision archives supplied 1,689 valid macro observations and 2,465 consecutive XRP daily candles. Exact URLs, bytes, local SHA256 fingerprints, missing timestamps and ledgers are retained.

The five annual OOS folds produced only 24 trades and lost $280.64, PF 0.476 and -$11.69 expectancy. Doubled costs lost $303.94, PF 0.446 and -$12.66 expectancy. Only 2023 was profitable; 2022, 2024 and 2025 lost, while 2026 generated no trades. The descriptive continuous path lost $272.91 base and $294.34 stressed, with 3.04%/3.24% drawdown. Every frozen gate except drawdown failed.

All 174 repository tests and 1,066 independent audit checks passed, demonstrating mechanics rather than an edge. Complete evidence is in `research/real_yield_easing_validation_20261029/`. Reject without inversion, threshold tuning or selecting the positive control/2023 subset. Do not promote to forward PAPER. Next research must use a genuinely different mechanism rather than another real-rate or external-risk recovery variant. Production, Render and LIVE remain untouched.

## XRP_FINANCIAL_CONDITIONS_EASING_V1: rejected (2026-10-29)

This preregistered external credit/risk/leverage hypothesis required the weekly Chicago Fed NFCI to be <= -0.25 and to have eased at least 0.10 index point over eight valid observations. Each observation was delayed until the second subsequent valid weekly observation, then execution used the next XRP daily open. The initially considered high-yield-spread export was rejected before registration because its free history began only in late 2023; no values were invented. Direct FRED NFCI and 81 Binance Vision archives supplied 352 weekly macro observations and 2,465 consecutive XRP daily candles with exact URLs and local SHA256 fingerprints.

The annual OOS folds produced only 5 base-cost trades and lost $65.70, PF 0.351 and -$13.14 expectancy. The doubled-cost path produced 6 path-dependent trades and lost $39.56, PF 0.578 and -$6.59 expectancy. Only 2025 had one profitable trade; 2022, 2024 and 2026 had no exposure, while 2023 lost. The separate continuous path also lost at both cost levels. Every frozen gate except drawdown failed.

All 180 repository tests and 404 independent audit checks passed, establishing mechanics rather than profitability. Complete evidence is in `research/financial_conditions_easing_validation_20261029/`. Reject without threshold relaxation, inversion or selection of the positive control/2025 trade. Do not promote to forward PAPER. Next research must leave external easing variants and use a genuinely different mechanism. Production, Render and LIVE remain untouched.

## POLYMARKET_XRP_SIGNAL_V1: historical test not completed (2026-10-29)

This genuinely different prediction-market hypothesis was preregistered before performance evaluation. The official Gamma series `xrp-up-or-down-5m` was created only on 2025-11-21 and the first ascending closed-event page begins 2025-12-18. At the fixed audit date this is only 341 days of series age and 314 days from the earliest returned event, below the frozen two-calendar-year source gate required for a multi-year test.

Official APIs are partly usable: a resolved probe market with reported volume $8,912.92 returned 277 public trades. However, both legacy CLOB and current Data API v2 price-history probes returned zero points for the same market. Six exact direct URLs, payload byte counts and SHA256 fingerprints are saved in `research/polymarket_xrp_source_audit_20261029/`; no Binance proxy or missing odds were fabricated.

No performance was evaluated, so this is not a completed failure. All 186 repository tests and 15 structural audit checks pass. Status remains **TEST NEDOKONČEN** until unchanged two-year, 95% completeness and 1,000-eligible-market gates can be met using official evidence. Next step is immutable forward capture or a complete official archive, then the already frozen chronological test. Production, Render and LIVE remain untouched.

## XRP_EXTREME_FEAR_CONTRARIAN_V1: rejected (2026-10-29)

This separately preregistered external-sentiment hypothesis bought XRP when the prior calendar day's Alternative.me Fear & Greed value was <=20, with entry at the following daily open. The direct sentiment API supplied 3,189 unique observations from 2018 onward; 81 Binance Vision archives supplied 2,465 consecutive XRP days. Exact-date alignment retained one explicit missing sentiment day as a gap without interpolation. URLs, byte counts and local SHA256 fingerprints are saved.

The five annual OOS folds produced 41 trades, +$176.30, PF 1.288 and +$4.30 expectancy. Doubled costs earned +$138.97, PF 1.221 and +$3.39 expectancy. However, only 2022 and 2026 were profitable, 2023 had no exposure, 2024–2025 lost, September 2022 supplied excessive positive profit, and the sample missed the frozen 75-trade minimum. The 2020–2021 control lost at both costs. Positive aggregate history is not enough.

All 192 repository tests and 1,714 independent audit checks passed. Complete evidence is in `research/extreme_fear_contrarian_validation_20261029/`. Reject without lowering the sample/stability/concentration gates or selecting profitable years. It is not promoted to forward PAPER; retain only as a frozen near-signal awaiting genuinely independent episodes. Production, Render and LIVE remain untouched.

## DEFI_YIELD_ROTATION_XRP_V1: rejected (2026-10-29)

This separately preregistered DeFi capital-allocation hypothesis bought XRP when the realized supply APY of the largest ordinary Aave v3 Ethereum USDC pool was below its 30-observation median and had fallen at least 0.50 percentage point over seven observations. Every source observation was mapped to the first strictly later XRP daily open. The fixed source contains 1,362 unique DefiLlama observations; 45 direct Binance Vision archives contain 1,369 consecutive XRP candles. Exact URLs, bytes, local SHA256 fingerprints and ledgers are retained. No APY or price was filled or fabricated.

The three annual OOS folds produced 47 trades, +$329.72, PF 1.425 and +$7.02 expectancy. Doubled fees and slippage earned +$286.41, PF 1.358 and +$6.09 expectancy. The separate continuous path earned $329.86 base and $285.93 stressed, with 2.53%/2.61% conservative drawdown. However, the frozen minimum was 75 OOS trades and 2026 lost at both cost levels. Only 2024 and 2025 were positive, so the all-year stability gates failed. There is no independent forward-PAPER evidence.

Reject despite positive aggregate history. Do not lower the sample gate, exclude 2026 or tune the now-observed yield thresholds. All 199 repository tests and 2,682 independent audit checks passed, establishing mechanics rather than future profitability. Complete evidence is in `research/defi_yield_rotation_validation_20261029/`. Next research must use a genuinely different preregistered mechanism; retain this only as a frozen near-signal for genuinely new observations. Production, Render and LIVE remain untouched.

## XRP_CORE_DEVELOPMENT_ACTIVITY_V1: rejected (2026-10-29)

This separately preregistered fundamental-development hypothesis used public `merged_at` events from the canonical `XRPLF/rippled` GitHub repository. A pre-performance ingestion clarification retained different PRs sharing a merge second while exact-deduplicating by PR number. Exhaustive official API pagination supplied 2,262 unique merged PRs; 81 Binance Vision archives supplied 2,465 consecutive XRP daily candles. Exact URLs, reported page totals, byte counts, local SHA256 fingerprints and ledgers are retained. No event or price was filled or invented.

The five annual OOS folds produced 105 trades and lost $114.81, PF 0.951 and -$1.09 expectancy. Doubled costs lost $229.27, PF 0.905 and -$2.18 expectancy. Only 2023 and 2024 were positive; 2022 had no exposure, while 2025 and final 2026 lost at both cost levels. The descriptive continuous path lost $123.61 base and $237.11 stressed, with 7.86%/8.66% drawdown. Only sample size and drawdown passed.

Reject without reversing the observed signal, selecting 2023–2024 or changing merge thresholds. All 206 repository tests and 7,557 independent audit checks passed, establishing mechanics rather than future profitability. Complete evidence is in `research/core_development_activity_validation_20261029/`. It is not promoted to forward PAPER. Next research must use a genuinely different preregistered mechanism rather than another core-merge-count window. Production, Render and LIVE remain untouched.

## XRP_LEDGER_CADENCE_HEALTH_V1: rejected (2026-10-29)

This preregistered infrastructure-quality hypothesis used direct CoinMetrics Community XRP daily ledger count with a conservative full-calendar-day publication lag, then direct Binance Vision daily execution. The metric and price windows each contain 2,465 consecutive exact dates from January 2020 through September 2026 without gaps or duplicates. Exact URLs, bytes, local SHA256 fingerprints and ledgers are retained; no observation was filled or invented.

The annual OOS folds produced 215 trades, +$202.74, PF 1.044 and +$0.94 expectancy at base costs. Doubled costs lost $24.37, PF 0.995 and -$0.11 expectancy. Only 2023–2024 were clearly positive; 2022 and 2025 lost, while 2026's $2.50 base profit became a $41.58 stressed loss. The continuous path earned $135.15 base but lost $92.63 stressed, with 6.25%/7.29% drawdown.

Reject despite adequate sample and nominal base profit: PF, stressed profitability, yearly stability, final stressed year and concentration gates failed. All 211 tests and 11,506 independent audit checks passed. Complete evidence is in `research/ledger_cadence_health_validation_20261029/`. Do not tune `BlkCnt` thresholds or promote to forward PAPER. Production, Render and LIVE remain untouched.

## XRP_PROTOCOL_ACTIVATION_EVENT_V1: rejected (2026-10-29)

This distinct event study used official XRPL mainnet amendment activation timestamps, grouped same-date activations and entered only at the first strictly later XRP daily open. Its protocol, source feasibility and fixed 75-trade gate were stored in GitHub commit `164ddea10785c33b81da1404f5dc7d4878a0d865` before price download or performance evaluation. The official snapshot has 105 records, 94 fully dated records and local SHA256 `1fe133244756ef3fcfb4db639a27f2edcce21956682898a8d5cbbaf12036b1eb`. Eighty-one Binance Vision archives provide 2,465 consecutive daily candles with no gaps or duplicates.

The annual OOS folds contain only 23 non-overlapping trades and lose $277.49, PF 0.592; double-cost stress loses $301.42, PF 0.566. Only 2024 is positive and 2026 loses at both costs. Continuous OOS also loses. The candidate fails sample, net, expectancy, PF, stability, final-year and concentration gates and has no forward PAPER evidence.

Reject without reducing the sample gate or retuning this sparse event family. All 217 tests and 1,320 independent audit checks passed. Complete evidence is in `research/protocol_activation_event_validation_20261029/`. Production, Render and LIVE remain untouched.

## BTC_VARIANCE_RISK_PREMIUM_XRP_V1: rejected (2026-10-30)

This distinct crypto-options hypothesis bought XRP when official Deribit BTC DVOL exceeded annualized 20-day realized BTC volatility by at least 15 points, using an extra full-day causal delay. Rules and gates were frozen in GitHub commit `8014a45b4b8f20ce803c7aacaaf94fc9da6a453f`. The first ingestion exposed two omitted Deribit pagination boundaries; the inclusive-cursor correction was documented in `caf38944599ea898ce66811b7c645b01b91c1b50` before the corrected run, with no strategy change.

The corrected data contain 2,017 consecutive DVOL days and 2,465 consecutive BTC and XRP daily candles, without gaps, duplicates or imputation. The five annual OOS folds produce 98 trades, -$250.69, PF 0.881 and -$2.56 expectancy. Double-cost stress loses $355.51, PF 0.835 and -$3.63 expectancy. Only 2023, 2025 and 2026 are positive; large 2022 and 2024 losses dominate. Continuous OOS also loses.

Reject independently of missing the 100-trade gate by two: profitability, expectancy, PF, stability and concentration fail at both costs. All 223 tests and 5,033 independent audit checks pass. Complete evidence is in `research/btc_variance_risk_premium_validation_20261030/`. Do not invert or tune this options-volatility family. Production, Render and LIVE remain untouched.
