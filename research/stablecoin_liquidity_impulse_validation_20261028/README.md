# STABLECOIN_LIQUIDITY_IMPULSE_XRP_V1 — completed validation

Decision: **NEPROŠEL**. The external-liquidity hypothesis, execution rules and
gates were committed before performance evaluation.

The test used direct CoinMetrics Community daily circulating supply for both
USDT and USDC plus real Binance Vision XRPUSDT daily archives from January 2020
through September 2026. Supply dated D could signal only at D+1 close and enter
at D+2 open. Exact URLs, response/archive sizes, counts and local SHA256
fingerprints are in `results.json`. Both supplies were required on each date;
there was no interpolation or carry-forward.

The five annual OOS folds produced 50 trades: +$336.53 net, PF 1.350 and +$6.73
expectancy at base costs. Doubled fees/slippage produced +$285.28, PF 1.289 and
+$5.71 expectancy. However, only 2023 and 2024 were positive; 2022, 2025 and
2026 lost at both costs. The continuous path earned $328.70 base and $276.51
stressed with 3.09%/3.37% drawdown. Profit was too concentrated in 2024.

The frozen minimum was 75 OOS trades and required four of five positive years,
including 2026. Sample, stability, final-year and concentration gates fail.
Aggregate historical profit therefore does not qualify the candidate for forward
PAPER promotion. Do not select 2024 or retune supply thresholds after seeing it.

All 143 repository tests passed. The independent audit verifies the two-day
metric lag, next-open timing, non-overlap, sizing cap, fees, slippage and P/L.
Tests establish implementation consistency, not future profitability.

```sh
python -m unittest discover -s tests -v
python -m research.run_stablecoin_liquidity_impulse /tmp/stable-liq-cache research/stablecoin_liquidity_impulse_validation_20261028
python -m research.audit_stablecoin_liquidity_impulse research/stablecoin_liquidity_impulse_validation_20261028
```

Next step: preserve this as a documented near-signal but do not mine the supply
threshold or holding period. New strategy work should move to a different data
mechanism or genuinely new forward observations. Production, Render, deployed
branches, paused strategies and LIVE remain untouched.
