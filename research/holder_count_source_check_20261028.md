# CoinMetrics XRP holder-count source check — 2026-10-28

Checked before performance evaluation of `XRP_HOLDER_GROWTH_DIVERGENCE_V1`.

The direct CoinMetrics Community catalog endpoint
`https://community-api.coinmetrics.io/v4/catalog-all/assets?assets=xrp`
lists daily `AdrBalCnt` with community availability. The frozen query is:

`https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?assets=xrp&metrics=AdrBalCnt&frequency=1d&start_time=2020-01-01&end_time=2026-10-01&page_size=10000`

The feasibility response returned HTTP 200, 2,466 rows, no pagination token,
first date 2020-01-01 and last date 2026-10-01. This check established only
availability, schema and coverage; it did not join prices, evaluate signals or
calculate returns. The validation runner will independently download and hash
its raw response and will retain exact URLs, byte counts, SHA256, gaps and
exclusions.

`AdrBalCnt` is a third-party derived count and its historical methodology may
change. Each dated metric is treated as unavailable until the following daily
close. No missing value will be interpolated or carried forward.
