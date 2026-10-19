# Retest cost review — 2026-10-19

Decision: REJECT FOR DEPLOYMENT. This is offline research, not a change to any running bot.

The original development sample had net -219.96 USDC, fees 201.44 and gross after slippage -18.52. Descriptive high-volatility/stronger-trend cohorts did not justify tightening entry filters. These are exploratory cohorts, not counterfactual backtests.

One fixed change was frozen on GitHub before evaluating the older period: solve the target price so that reaching it delivers the original reward after modeled fees and slippage. Signals, stop and notional are unchanged. This does not assure a positive expectation: targets are harder to reach.

## Older disjoint period

2025-10-18 inclusive through 2026-04-18 exclusive, XRPUSDC 15m. Data begins seven days earlier for warmup. This is a backward historical check, not forward out-of-sample evidence. Prior unrelated exposure is unknown. Starting balance 10,000 USDC, notional 1,000 USDC, fees 0.095% per side, base slippage 0.02% per side.

| Metric | Original retest | Net-target candidate |
|---|---:|---:|
| Trades | 185 | 181 |
| Net PnL USDC | -214.22 | -109.74 |
| Fees USDC | 351.36 | 343.71 |
| Profit factor | 0.832 | 0.914 |
| Close-marked drawdown | 3.34% | 2.56% |
| Net PnL, double slippage | -251.17 | -132.78 |

The candidate improves net by 104.48 USDC but fails positive net, PF >=1.2 and positive stress net. No parameter search or further variants were selected after this result. Both retest versions remain rejected. Earlier tests on FLY/FAST/TV are separate; these candle references are not full replicas of those bots. SHORT is synthetic PAPER; borrow/funding absent. Drawdown is not intrabar worst case. Stress recomputes the cost-adjusted target using stressed slippage, rather than holding the base target fixed.

## Reproduction

From repository root:

```
python -m unittest test_candle_research research.retest_cost_review_20261019.test_variant test_paper_overlap_candidate test_archive_filter_replay test_archive_continuity test_tv_pause_review test_research_market_evidence -q
python research/retest_cost_review_20261019/download.py /tmp/retest-older
python research/retest_cost_review_20261019/run.py /tmp/retest-older/candles.json
```

42 targeted tests passed. Raw input digest is in data_manifest.json; results include each gate. No private account or ledger exports are included. No deployment, paused-strategy restart or live-trading change was performed. Further claims require genuinely new prospective evidence, not repeated tuning on these now-seen periods.
