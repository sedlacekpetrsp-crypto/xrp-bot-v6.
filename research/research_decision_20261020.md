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
