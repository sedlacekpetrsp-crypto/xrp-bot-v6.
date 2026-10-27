# Second-exchange source feasibility — 2026-10-27

Before preregistration, the direct Coinbase Exchange candles endpoint returned
historical XRP-USD hourly OHLCV for an explicitly bounded January 2024 request.
The direct Kraken OHLC endpoint ignored the old `since` value and returned only
recent bars, so Kraken was not selected. Coinbase is therefore the frozen second
venue. The validation must stop rather than invent any candle if bounded Coinbase
history cannot be retrieved or aligned.

Example checked endpoint:
`https://api.exchange.coinbase.com/products/XRP-USD/candles?granularity=3600&start=2024-01-01T00:00:00Z&end=2024-01-02T00:00:00Z`

This check establishes availability only, not profitability or completeness.
