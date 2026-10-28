# Stablecoin supply source feasibility — 2026-10-28

CoinMetrics Community directly returned daily `SplyCur` for both USDT and USDC
without credentials or a paid service. Both assets must exist on the exact date;
the validator will not carry supply forward or interpolate. Exact response bytes
will be locally SHA256 fingerprinted.

Checked endpoint family:
`https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?assets=usdt,usdc&metrics=SplyCur&frequency=1d`

Availability is not completeness or profitability evidence.
