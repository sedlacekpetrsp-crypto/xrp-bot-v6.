# XRP_CROSS_EXCHANGE_RESIDUAL_CONVERGENCE_V1 — completed validation

Decision: **NEPROŠEL**. Rules and gates were frozen on GitHub before historical
evaluation. This was a genuinely cross-exchange, BTC-basis-adjusted relative
price test, not a retuned version of a rejected OHLC or flow strategy.

The direct sources yielded exactly aligned hourly data from Coinbase Exchange
XRP-USD/BTC-USD and Binance Vision XRPUSDT mark/BTCUSDT spot plus actual XRP
funding observations. Full request URLs, payload byte counts, SHA256 fingerprints,
series counts, exclusions and gaps are in `results.json`. No candle was filled or
invented. Coinbase's bounded API payload hashes are local provenance fingerprints,
not publisher signatures.

Only one locked OOS signal occurred (2024-Q4). Its next open was already beyond
the preregistered stop, so it used gap-stop execution and lost $15.60 after base costs (PF 0.0), or
$31.20 with all fees and slippage doubled (PF 0.0). All other OOS quarters and
the H2-2023 control had no trades. The minimum was 120 OOS trades, so the
candidate fails sample, profitability, stress, stability, final-quarter and
concentration gates. Zero activity in other quarters is not positive evidence.

All 124 repository tests passed. The independent audit validates next-open
timing, signal threshold, non-overlap, 10%-per-leg cap, fees, slippage and P/L
reconciliation. Tests establish implementation consistency, not profitability.

Limitations: hourly OHLC does not reproduce synchronized bid/ask or intrabar
paths; independent adverse extremes deliberately make stops conservative. The
0.60% Coinbase fee is a conservative frozen taker assumption and may differ by
account tier. No forward PAPER evidence exists.

Reproduce from repository root:

```sh
python -m unittest discover -s tests -v
python -m research.run_cross_exchange_residual /tmp/cross-exchange-cache research/cross_exchange_residual_validation_20261027
python -m research.audit_cross_exchange_residual research/cross_exchange_residual_validation_20261027
```

Do not loosen the residual threshold after observing this sparse sample. A next
candidate should use a denser but distinct observable and must be preregistered.
No production, Render, main, deployed branch, paused strategy or LIVE setting
was changed.
