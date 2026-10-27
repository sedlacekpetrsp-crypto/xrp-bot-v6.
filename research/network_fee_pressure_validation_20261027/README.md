# XRP_NETWORK_FEE_PRESSURE_V1 — completed validation

Decision: **NEPROŠEL**. The fee-pressure rules and gates were committed before
performance evaluation. This is a different on-chain mechanism from the earlier
active-address breadth candidate.

The test used direct CoinMetrics Community daily XRP total-fee-burn and transfer
counts plus real Binance Vision XRPUSDT daily archives, January 2022 through
September 2026. Metrics had a full-day availability lag: day D could signal only
at D+1 close and enter at D+2 open. `results.json` retains exact URLs, sizes,
row counts and local SHA256 fingerprints. No observation was fabricated.

The four annual OOS folds produced 86 trades and lost $303.33, PF 0.825 and
-$3.53 expectancy after base costs. With doubled costs they lost $426.47, PF
0.764 and -$4.96 expectancy. Only 2023 was profitable; 2024, 2025 and 2026 lost.
The continuous path lost $304.25 base and $423.41 stressed, with 5.50%/6.61%
drawdown. The 2022 control also lost at both costs.

The candidate fails sample, profitability, stress, stability, final-year and
concentration gates. Do not invert it or tune percentile/holding rules on these
observed years. No forward PAPER promotion is allowed.

All 137 repository tests passed. The independent audit checks metric/entry lag,
non-overlap, sizing cap, fees, slippage and P/L reconciliation. Tests establish
mechanical consistency, not future profitability.

```sh
python -m unittest discover -s tests -v
python -m research.run_network_fee_pressure /tmp/network-fee-cache research/network_fee_pressure_validation_20261027
python -m research.audit_network_fee_pressure research/network_fee_pressure_validation_20261027
```

Next step: do not mine further thresholds from the same fee series. Preserve the
earlier activity-breadth near-signal for genuinely new independent observations,
and move new hypothesis work to another data mechanism. Production, Render,
deployed branches, paused strategies and LIVE remain untouched.
