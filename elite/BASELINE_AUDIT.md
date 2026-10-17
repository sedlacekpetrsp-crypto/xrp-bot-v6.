# ELITE — baseline audit (2026-10-13)

Source: read-only SQL on existing Render PostgreSQL `xrp-bot-db`.
These are database records, not verified real-money account statements.

| Bot | Closed trades | Win rate | Sum reported net P/L (USD) |
| --- | ---: | ---: | ---: |
| BEST-OF | 56 | 30.4% | -94.14 |
| FAST | 104 | 22.1% | -413.46 |
| BLUE WHALE | 6 | 0.0% | -117.93 |

BEST-OF by setup:
| Setup | Trades | Win rate | Net P/L (USD) |
| --- | ---: | ---: | ---: |
| BREAKOUT | 41 | 29.3% | -77.47 |
| FIB_0618_0786 | 15 | 33.3% | -16.66 |

Notes:
- Samples and observation windows differ; do not interpret as risk-adjusted rankings.
- Negative historical results do not imply a new strategy will be profitable.
- Next: retrieve independently sourced XRPUSDT 5m candles; run tests and walk-forward evaluation.
- ELITE must not use the same breakout/Fibonacci entries as a purported new edge.
- Existing services and trades were not modified.
