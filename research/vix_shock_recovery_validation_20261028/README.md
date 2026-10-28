# XRP_VIX_SHOCK_RECOVERY_V1 — completed validation

Decision: **NEPROŠEL**. The external equity-volatility recovery hypothesis,
rules and gates were committed before performance evaluation.

The test used direct FRED `VIXCLS` and real Binance Vision XRPUSDT daily spot
archives from January 2020 through September 2026. Each VIX value became
eligible only on the date of the second subsequent valid observation; entry was
at the next XRP daily open. Weekends, holidays and 32 explicit FRED missing-
value rows were not filled. The data retained 1,729 valid VIX observations and
2,465 consecutive XRP days. Exact URLs, byte counts and local SHA256
fingerprints for all 82 payloads are in `results.json`.

The five annual OOS folds produced only 11 trades: +$183.67 net, PF 2.582 and
+$16.70 expectancy at base costs. Doubled fees/slippage earned $174.04, PF
2.451 and +$15.82 expectancy. The descriptive continuous path earned $209.64
base and $199.82 stressed with 0.84%/0.86% drawdown.

The positive aggregate is insufficient. The frozen minimum was 75 trades;
2023 generated no trade, 2025 lost at both cost levels, and February 2022 alone
supplied more than 25% of positive-month profit. Thus sample, four-positive-year
and concentration gates fail. Do not lower the sample threshold, count zero
exposure as a profitable year, select isolated events or tune VIX thresholds.

All 167 repository tests passed. The independent audit performed 596 checks of
release lag, VIX shock/recovery thresholds, next-open timing, non-overlap,
sizing, fees, slippage and P/L without importing the strategy module. Tests
establish implementation consistency, not future profitability.

```sh
python -m unittest discover -s tests -v
python -m research.run_vix_shock_recovery /tmp/vix-cache research/vix_shock_recovery_validation_20261028
python -m research.audit_vix_shock_recovery research/vix_shock_recovery_validation_20261028
```

Next step: preserve this rare-event near-signal without retuning and do not
promote it to forward PAPER. Any future reconsideration requires genuinely new
independent VIX shock observations under unchanged rules. Production, Render,
deployed branches, paused strategies and LIVE remain untouched.
