# XRP_LEDGER_ACTIVITY_BREADTH_V1 — completed validation

Decision: **NEPROŠEL**. The on-chain rules, percentile definition and gates were
saved to GitHub before historical performance was evaluated.

The test directly combined CoinMetrics Community daily XRP active-address and
transaction counts with Binance Vision XRPUSDT daily spot archives for January
2022 through September 2026. A metric dated D could only signal at the close of
D+1 and enter at D+2. Exact URLs, payload/archive byte counts, row counts and
local SHA256 fingerprints are in `results.json`; missing dates were not invented.

The four annual OOS folds produced 35 trades: +$221.17 net, PF 1.370 and +$6.32
expectancy at base costs. With doubled fees and slippage they produced +$188.37,
PF 1.306 and +$5.38 expectancy. Three of four years, including 2026, were
positive under both assumptions, while 2025 lost at both. The separate continuous
path had 35 trades, +$331.43/PF 1.537 base and +$296.86/PF 1.469 stressed, with
3.75%/3.86% drawdown. It repeats the same observations and is not extra evidence.

Despite positive aggregate history, the frozen minimum was 80 OOS trades. Only
35 occurred, and the 2022 control lost $236.69 base and $245.85 stressed. The
sample gate therefore fails and no forward PAPER promotion is allowed. Do not
weaken the sample rule or tune the signal to the losing 2025 period.

All 131 repository tests passed. The independent audit checks the two-day metric
lag, next-open timing, non-overlap, 20% cap, fees, slippage and P/L reconciliation.
Tests establish implementation consistency, not future profitability.

Reproduce:

```sh
python -m unittest discover -s tests -v
python -m research.run_ledger_activity_breadth /tmp/ledger-activity-cache research/ledger_activity_breadth_validation_20261027
python -m research.audit_ledger_activity_breadth research/ledger_activity_breadth_validation_20261027
```

Next step: preserve this as a documented near-signal, but test a separate on-chain
mechanism or a materially longer independent source before any new candidate.
Production, Render, deployed branches, paused strategies and LIVE remain untouched.
