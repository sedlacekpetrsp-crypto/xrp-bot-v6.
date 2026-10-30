# BTC_VARIANCE_RISK_PREMIUM_XRP_V1 — completed validation

Decision: **NEPROŠEL**. The fixed hypothesis, threshold, timing, execution and gates were stored in GitHub commit `8014a45b4b8f20ce803c7aacaaf94fc9da6a453f` before complete price download or performance evaluation. The first ingestion exposed two exact pagination-boundary gaps. The inclusive-cursor correction was documented and committed as `caf38944599ea898ce66811b7c645b01b91c1b50` before the corrected run; no strategy parameter changed and the invalid initial output was overwritten.

The mechanism is BTC option-market variance pricing, not another VIX, XRP price-volatility, trend, flow, network or event rule. A signal required official Deribit BTC DVOL close minus annualized population volatility of 20 actual BTC daily returns to be at least 15 percentage points. It entered XRP at D+2, one full day after both day-D observations were conservatively known.

The corrected source contains 2,017 consecutive Deribit DVOL daily observations from 2021-03-24 through 2026-09-30, zero gaps and duplicates. Three retained raw API pages have SHA256 `cda5ab1c...641bd`, `e4cc2e94...a726`, and `9fa127a2...092a`. Direct Binance Vision archives provide 2,465 consecutive BTCUSDT and 2,465 consecutive XRPUSDT daily candles from 2020-01-01 through 2026-09-30, also without gaps or duplicates. `results.json` retains full URLs, byte counts and every SHA256. Nothing was interpolated or carried forward.

All 223 repository tests passed. The independent audit passed 5,033 checks of source hashes, population-volatility arithmetic, premium and two-day lag, chronology, actual opens, adverse fills, fees, slippage, risk, notional cap, non-overlap, equity and report reconciliation without importing strategy code. Tests establish mechanical consistency, not an edge.

| Annual OOS fold | Trades | Base net P&L | Base PF | Double-cost net P&L | Stress PF |
|---|---:|---:|---:|---:|---:|
| 2022 | 35 | -$506.95 | 0.402 | -$536.98 | 0.380 |
| 2023 | 22 | +$277.42 | 1.725 | +$249.95 | 1.635 |
| 2024 | 22 | -$227.42 | 0.563 | -$252.50 | 0.531 |
| 2025 | 12 | +$18.16 | 1.083 | +$7.28 | 1.033 |
| 2026 through September | 7 | +$188.10 | 2.435 | +$176.74 | 2.304 |
| Aggregate reset folds | 98 | -$250.69 | 0.881 | -$355.51 | 0.835 |

Base expectancy is -$2.56 per trade; stressed expectancy is -$3.63. The separate continuous OOS path has 98 repeated trades, -$268.14/PF 0.869 and 6.21% conservative drawdown; stress is -$370.55/PF 0.824 and 6.94% drawdown. The 2021 control also loses after the corrected ingestion. Annual and continuous trades are repeated evidence and are not added.

The candidate fails the frozen 100-trade sample gate by two trades, but rejection does not depend on that margin: net P&L, expectancy, PF, annual stability and concentration also fail at both cost levels. Only 2023, 2025 and 2026 are positive; 2022 and 2024 losses dominate. Drawdown and final-2026 gates pass. No independent forward PAPER evidence exists.

Reproduce from repository root:

```sh
python -m unittest discover -s tests -v
python -m research.run_btc_variance_risk_premium /tmp/vrp-cache research/btc_variance_risk_premium_validation_20261030
python -m research.audit_btc_variance_risk_premium /tmp/vrp-cache research/btc_variance_risk_premium_validation_20261030
```

Full ledgers are in `trades.json.gz`; metrics, sources and gates in `results.json`; audit in `audit.json`. Do not invert the signal, lower the sample gate or tune the premium on these dates. Next work must leave BTC implied-versus-realized volatility variants and preregister a materially different mechanism. Production, main, `v8-fly-layer-test`, Render, paused strategies, infrastructure and LIVE were untouched.
