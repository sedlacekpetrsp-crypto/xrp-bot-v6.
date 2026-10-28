# XRP_REALIZED_VALUE_DISCOUNT_V1 — completed validation

Decision: **NEPROŠEL**. The cost-basis valuation hypothesis, rules and gates
were committed before performance evaluation.

The test used direct CoinMetrics Community daily XRP `CapMVRVCur` plus real
Binance Vision XRPUSDT daily spot archives from January 2020 through September
2026. A metric dated D could signal only at D+1 close and enter at D+2 open.
Exact URLs, byte counts and local SHA256 payload fingerprints are in
`results.json`. The 2,466 metric rows and 2,465 price rows aligned on 2,465
dates with no duplicates or gaps; the metric-only endpoint was excluded. No
value was interpolated or carried forward.

The five annual OOS folds produced 32 base-cost trades: +$641.46 net, PF 2.015
and +$20.05 expectancy. Doubled fees/slippage produced 33 path-dependent trades,
+$480.47 net, PF 1.657 and +$14.56 expectancy. The descriptive continuous path
earned $680.93 base and $516.59 stressed with 1.78%/1.83% drawdown.

These positive aggregates do not pass the frozen gates. The 75-trade minimum
failed; 2022 lost, 2025 generated no trades, and therefore fewer than four of
five OOS years were positive. The 2026 fold was positive but does not cure the
small and episodic sample. Do not lower the sample requirement, treat zero
exposure as a profitable year, or tune the observed MVRV discount.

All 149 repository tests passed. The independent audit performed 1,330 checks
of the two-day metric lag, next-open timing, signal threshold, non-overlap,
position cap, fees, slippage and P/L without importing the strategy module.
Tests establish implementation consistency, not future profitability.

Reproduce from repository root:

```sh
python -m unittest discover -s tests -v
python -m research.run_realized_value_discount /tmp/realized-value-cache research/realized_value_discount_validation_20261028
python -m research.audit_realized_value_discount research/realized_value_discount_validation_20261028
```

Next step: preserve this as a documented near-signal without threshold or exit
tuning. New work should use a different mechanism or genuinely new independent
forward observations. It is not promoted to PAPER monitoring. Production,
Render, deployed branches, paused strategies and LIVE remain untouched.
