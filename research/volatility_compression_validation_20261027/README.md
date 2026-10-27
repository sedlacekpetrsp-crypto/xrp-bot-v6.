# XRP_VOLATILITY_COMPRESSION_BREAKOUT_V1 — completed validation

Decision: **NEPROŠEL**. The low-volatility-to-breakout hypothesis fails the frozen sample, aggregate profitability, stress, annual-stability, and concentration gates. It is not eligible for forward PAPER promotion.

The data-source check and strategy rules were frozen in GitHub commit `024248052292806e075fa72a37144f46cdeceef9` before performance evaluation. No threshold, window, bracket, or gate was selected after seeing returns.

## Evidence

- 57 actual Binance Vision XRPUSDT spot 1h monthly archives, January 2022 through September 2026.
- 41,615 unique bars, no duplicates. The common missing hour at 2023-03-24 13:00 UTC was retained; indicator histories crossing it were suppressed and no price was imputed.
- Every source URL, byte count, row count, and locally calculated SHA256 is in `results.json`. Hashes identify downloaded bytes and are not publisher signatures.
- All 108 repository tests passed. The independent ledger audit passed 2,056 chronology, overlap, fee, P/L, risk, notional, equity, manifest, and hash checks.

| Locked period | Trades | Base net P/L | Base PF | Stress net P/L | Stress PF |
|---|---:|---:|---:|---:|---:|
| 2022 control | 23 | -$178.53 | 0.704 | -$273.29 | 0.592 |
| 2023 OOS | 12 | -$231.32 | 0.115 | -$280.29 | 0.085 |
| 2024 OOS | 18 | -$228.61 | 0.500 | -$299.18 | 0.415 |
| 2025 OOS | 19 | +$122.49 | 1.300 | +$41.82 | 1.091 |
| 2026 OOS through September | 12 | +$194.88 | 2.241 | +$143.38 | 1.788 |
| Aggregate annual OOS folds | 61 | -$142.56 | 0.889 | -$394.26 | 0.729 |
| Continuous Jan 2023–Sep 2026 | 61 | -$149.42 | 0.880 | -$395.89 | 0.719 |

Annual-fold totals reset $10,000 equity each year and therefore differ from the continuous path; they repeat the same observations and are not independent evidence. Annual-fold base expectancy was -$2.34 per trade and stress expectancy was -$6.46. Continuous drawdown passed its gate at 6.34% base and 7.76% stress. The historical path had 43 stops, 17 targets, and one time exit. Later-period profitability cannot be selected after the 2023–2024 losses, the losing control, and the 61-trade sample shortfall.

The runner uses next-open entries, 0.50% stop risk, a 20% notional cap, one position at a time, 9.5 bps fees and 2 bps adverse slippage per side, doubled-cost stress, gap-stop fills at the worse open, and stop-first handling for ambiguous OHLC bars. Conservative drawdown uses the whole exit-candle low and is not tick-exact. These limitations do not reverse the failed net and stress evidence.

Reproduce from the repository root:

```sh
python -m unittest discover -s tests -v
python -m research.run_volatility_compression /tmp/crypto-archives research/volatility_compression_validation_20261027
python -m research.audit_volatility_compression research/volatility_compression_validation_20261027
```

No forward PAPER process is opened for a historically rejected strategy. Production, main, `v8-fly-layer-test`, Render, infrastructure, paused strategies, and LIVE trading were untouched.

Next concrete step: do not select only 2025–2026 or retune compression/breakout windows on the observed history. Before another registration, inspect availability, cadence, synchronization, and archive size of actual Binance `bookTicker` top-of-book data for XRPUSDT, XRPBTC, and BTCUSDT to determine whether a genuinely market-neutral triangular-dislocation study is reproducible. If coverage is incomplete, record that failure and choose another data family rather than substitute candle prices.

