# XRP_EXTREME_FEAR_CONTRARIAN_V1 source feasibility (2026-10-29)

Performance was not evaluated before this note was committed.

Selected direct source:
- URL: https://api.alternative.me/fng/?limit=0&format=json
- Retrieved payload SHA256: `4c347c0e5c7f35addd8be0ca7ddc01b94ecb386609e35c6a52f770db471250d6`.
- 3,189 observations returned, newest first, from 2018-02-01 through 2026-10-29 UTC.
- API metadata reported no error.
- Values are integer strings on 0–100. The runner will reverse to chronological order, reject duplicate/non-daily timestamps and retain exact dates only. A full-day lag is mandatory.

Two rejected source ideas were not registered as strategies: CoinMetrics XRP `SplyCur` represents nearly fixed total supply rather than escrow circulation, and `SplyAct1yr` returned HTTP 403 as unavailable with community credentials. No paid service or fabricated substitute is used.

Market execution will use direct Binance Vision XRPUSDT daily monthly archives, with each URL, byte count, row count and freshly computed SHA256 retained. This is an availability check only and does not amend the frozen rules or establish profitability.
