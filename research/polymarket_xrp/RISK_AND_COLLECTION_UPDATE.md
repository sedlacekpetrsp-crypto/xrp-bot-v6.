# Risk and collection update — 2026-10-28

Supersedes the intratrade-risk limitation in SAMPLE_REPORT.md. Strategy rules,
threshold selection and chronological split have not changed.

## Same holdout, improved risk accounting

Five trades; return after modeled costs -1.7003475%. Closed-trade drawdown
1.7003475%. Intratrade liquidation-equity drawdown from minute OHLC: lower and
upper bounds both 1.8909491% for this sample. The equality means unknown
within-minute high/low ordering does not affect this particular maximum.
This remains an OHLC model with assumed fees/slippage, not measured execution
quotes, and does not include unobserved spread/liquidity shocks.

Momentum-only baseline on the same eligible test windows: eight trades,
-2.7370153% net return, intratrade drawdown bounds both 2.9057957%.
The Polymarket filter trades less and loses less here; this is not proof of
incremental predictive information. Both versions lose money. No parameter
was adjusted to improve the observed holdout.

## Longer public-data audit

Downloaded and inspected the complete markets.parquet catalog from
https://huggingface.co/datasets/DineshKumar8399/polymarket-orderbook-dataset/resolve/main/markets.parquet

3,781,074 bytes; SHA256
9469b844297763fc9259a902b53df6100e0d1dd9ac95e9cdeef7dcc7e6f487c2.
314,123 rows; zero slugs containing `xrp` case-insensitively. Therefore no
identified XRP five-minute coverage to extend this test. Did not download
the much larger quote archive. This does not imply no other suitable archive exists.

## Prepared capture utility

`collect_snapshot.py` performs one manual, read-only capture for an explicit
XRP five-minute slug. It maps Up to its token by outcome name, requests the
Polymarket book and Binance public depth concurrently, and records request
and receipt times plus failures. Raw responses remain unusable until validated.
This is capture scaffolding, not an automated rolling collector or validated
backtest importer. No scheduler or background service has been installed.

Usage: `python collect_snapshot.py xrp-updown-5m-UNIX_START OUTPUT.jsonl`
The known CLOB 403 may still block real capture in this environment. Tests use
mocked transport; do not mistake passing tests for live data availability.

13 unit tests pass, including intratrade loss hidden by flat closing prices,
missing candles, cost accounting, outcome mapping and empty-market rejection.

Verdict remains TEST NEDOKONČEN: only a few-hour pilot, no independent multi-day
validation. Production, Render, LIVE and paid services unchanged.
