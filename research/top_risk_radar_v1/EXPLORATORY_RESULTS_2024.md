# Exploratory XRP event census — first verified run

Status: ACTUALLY RUN (descriptive only), NOT A PREDICTIVE BACKTEST.
Run: https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./actions/runs/42426221285
Source: Binance public monthly XRPUSDT 1h spot klines, Jan-Apr 2024; four SHA256-verified ZIP archives.
Reference: 01:00 UTC hourly close (NOT the protocol's 00:05 first eligible trade).
Eligible matured decisions: 91.
+30% within 30d by hourly close: 19.
-20% within 14d by hourly close: 1.
Both: 0.

Interpretation:
- These are overlapping daily labels, NOT independent market events, and NOT forecast accuracy.
- Only one 2024 interval was sampled; no inference about other years or regimes.
- The hourly-close definition misses intrahour extrema and cannot be mixed with the trade-level radar target.
- 2024 Jan-Apr was exploratory; do not select thresholds or model hyperparameters on this sample and then call this same sample OOS.
- This evidence does not support a claim that a model beats a baseline or that trading is profitable.

Next gates:
1. Episode-level accounting and independent cross-checks.
2. Multiple years of source QA with exact trade-level reference.
3. Freeze data, train/test splits and price-only baseline before testing incremental signals.
4. At least 90 days forward PAPER observation for any claimed candidate.
