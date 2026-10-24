# AUTOCORR_REGIME_SWITCH_V1 — preregistration (2026-10-24)

Status: HYPOTHESIS REGISTERED, HISTORICAL TEST NOT YET RUN. This is NOT evidence of profitability.

Distinct hypothesis: the sign of 96-bar lag-one autocorrelation of log returns conditions the direction of the next 4-bar price move. Positive autocorrelation >= +0.12 trades a 4-bar breakout continuation; negative <= -0.12 trades a 4-bar reversal, with no trade in between. Unlike rejected flow pressure, sweep, volatility momentum, and state classifier candidates, this tests a pre-specified conditional reversal-vs-continuation decision on serial dependence, not flow, volume, or volatility alone. Spot LONG only; no shorting.

Fixed parameters before seeing results: XRPUSDT and ETHUSDT spot 15m; 96 closed returns; lag-one Pearson autocorrelation; regime threshold +/-0.12; 4-bar return threshold +/-0.35%; ATR14; stop 1.8 ATR; target 2.2R; max 24 bars; fee 0.095% per side; adverse slippage 0.02% per side; 0.5% account-equity risk per trade; max 20% notional; one position per symbol, 20% total gross portfolio cap. Entry at next bar open; intrabar ambiguous stop wins; gap stop at worse open. Zero leverage.

Historical protocol: actual Binance Vision monthly spot 15m klines Oct 2025–Sep 2026, complete consecutive UTC timestamps and source SHA256. Train Oct 2025–Jun 2026; locked chronological OOS Jul–Sep 2026. Run both markets and 2x fee/slippage stress without tuning. This period was previously inspected in other projects: exploratory OOS, NOT untouched validation. Evaluate monthly subperiods, gross/net P/L, drawdown, PF, and >=100 OOS trades aggregate; require PF>1.2, positive net expectancy and net P/L on both symbols, stress PF>1.05, no single month >50% of total profit, max DD <=10%. After passing, demand >=30 calendar days and >=100 new timestamped forward PAPER trades on independent future observations with positive stressed expectancy before any PROŠEL designation. No LIVE or Render changes.

Next action: run unit tests and independent historical downloader/backtest on real complete archives; write exact data provenance, results, limitations, and decision here. Never label a pending run as failed or successful.

## Completed historical validation, 2026-10-24

Decision: **NEPROŠEL**. Correct repository is `sedlacekpetrsp-crypto/xrp-bot-v6.` (trailing period is part of its name); the earlier 404 resulted from omitting it.

Downloaded 24 actual Binance monthly archives, 35,040 consecutive bars per symbol. Exact archive URLs and SHA256 hashes are in `autocorr_validation_20261024/results.json`; these are locally computed provenance hashes, not independently verified publisher checksums. Full trade records are in `trades.json.gz`. Reproduce from repository root:

```
python -m unittest discover -s tests -v
python -m research.run_autocorr_history /tmp/crypto-archives research/autocorr_validation_20261024
python -m research.weekend_drift_v1 /tmp/crypto-archives research/weekend_validation_20261024
```

All 11 research unit tests passed. Added next-open timing, cost accounting, double-cost deterioration, stop-before-target ambiguity, gap-stop, future-prefix invariance and calendar execution tests. Tests validate mechanics, not profitability. No parameter optimization. Train ends before July 1; OOS uses past-only warmup and begins flat, with positions liquidated at the segment end. Fees 9.5 bps and adverse slippage 2 bps per side; stress doubles both. Each symbol has an isolated $5,000 sleeve, capped at 20% of sleeve equity: combined positions cannot exceed 20% of total capital. No pooled reallocation. Returns below are relative to each sleeve.

| OOS July–September 2026 | Trades | Net return | PF | Double-cost net return | Stress PF |
|---|---:|---:|---:|---:|---:|
| XRP | 169 | -0.524% | 0.972 | -7.824% | 0.651 |
| ETH | 167 | -3.045% | 0.806 | -9.855% | 0.495 |

Both training segments also lose. Trade counts can change under stress because adjusted fills move the brackets. Gross P/L before fees and slippage is reported for the corresponding cost-scenario trade path, not a separately simulated zero-cost strategy. Drawdown marks open positions at candle lows and peaks at prior closes; whole exit-candle lows can overstate drawdown after an earlier exit. This is conservative OHLC approximation, not tick-exact portfolio drawdown. Rejection already follows from negative expectancy on both markets, independently of drawdown.

## Distinct follow-up: WEEKEND_DRIFT_V1

After rejecting autocorrelation, froze and implemented a calendar-only hypothesis before running its backtest: buy spot Saturday 00:00 UTC, sell Monday 00:00 UTC, 2.5% protective stop, no indicator/volume/autocorrelation condition, no leverage. Same fees, stress, split, sizing and conservative screening gates. The calendar signal is known before the entry open. No search over weekdays or holding windows. Strategy code and tests are committed alongside its results.

Decision: **NEPROŠEL**. XRP OOS: 13 trades, -0.632%, PF 0.743; stress -1.212%, PF 0.552. ETH OOS: 13 trades, +0.979%, PF 1.680; stress +0.379%, PF 1.222. Only 26 aggregate OOS trades, loss on XRP, and profit concentration in July; both training markets lose. Do not select ETH alone after seeing this outcome or weaken the 100-trade requirement. Future research needs a longer independently specified test and fresh forward observations, not retuning this period.

These dates have been inspected for multiple hypotheses: results are exploratory chronological OOS, never untouched validation. Neither candidate qualifies for forward promotion or LIVE. No production files, Render services, runtime settings, or main branch were changed.
