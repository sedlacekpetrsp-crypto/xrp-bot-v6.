# XRP_HOLDER_GROWTH_DIVERGENCE_V1 — completed validation

Decision: **NEPROŠEL**. The holder-stock/price-divergence hypothesis, rules and
gates were committed before performance evaluation.

The test used direct CoinMetrics Community daily XRP `AdrBalCnt` plus real
Binance Vision XRPUSDT daily spot archives from January 2020 through September
2026. A metric dated D could first contribute to a signal at D+1 close and the
trade entered at D+2 open. Exact URLs, byte counts and local SHA256 payload
fingerprints are in `results.json`. The 2,466 metric rows and 2,465 price rows
aligned on 2,465 dates with no duplicates or gaps; one metric-only endpoint was
excluded. No value was fabricated, interpolated or carried forward.

The five annual OOS folds produced 31 trades: +$85.59 net, PF 1.107 and +$2.76
expectancy at base costs. Doubled fees/slippage produced +$17.32, PF 1.021 and
+$0.56 expectancy. The descriptive continuous path earned $93.54 base and
$28.07 stressed with 2.43%/2.57% drawdown.

These small positive aggregates fail the frozen requirements. The minimum was
75 OOS trades, base PF had to exceed 1.15, and at least four of five years had
to be positive. Only 2022, 2025 and 2026 were positive; 2023 and 2024 lost at
both cost levels. The stressed edge is especially thin. Do not lower the sample
or PF threshold, select only recent years, or tune either divergence threshold.

All 155 repository tests passed. The independent audit performed 1,370 checks
of the metric lag, both signal conditions, next-open timing, non-overlap,
position cap, fees, slippage and P/L without importing the strategy module.
Tests establish implementation consistency, not future profitability.

```sh
python -m unittest discover -s tests -v
python -m research.run_holder_growth_divergence /tmp/holder-growth-cache research/holder_growth_divergence_validation_20261028
python -m research.audit_holder_growth_divergence research/holder_growth_divergence_validation_20261028
```

Next step: retain the result without tuning and move new research away from
holder-count/price-divergence variants. It is not promoted to forward PAPER.
Production, Render, deployed branches, paused strategies and LIVE remain
untouched.
