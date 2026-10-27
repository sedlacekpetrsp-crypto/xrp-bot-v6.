# XRP_AGGRESSOR_SELL_BURST_REVERSAL_V1 — completed validation

Decision: **NEPROŠEL**. The tick-sequence sell-exhaustion reversal loses in every locked control/OOS year and fails every profitability, stability, drawdown, and concentration gate. Only sample size passes; no forward PAPER process is opened.

Rules and gates were frozen in GitHub commit `4398ded3f6913c3d6da958abfc9fe52f0acdfec8` before evaluation. The initial ingestion stopped before performance on a locally disordered publisher archive; the exact ordering correction was committed as `52c9f993f8888b0f4b2bdba6cfd38c8cb48a90c5`. The corrected stream then stopped on 4,000 identical duplicate rows; exact-only deduplication was committed as `27dd04265c6f85f7cd5f5caf78078c77e91aa798`. No return existed at either amendment, and no trading parameter changed.

## Data and verification

- 57 actual Binance Vision monthly XRPUSDT spot `aggTrades` archives, January 2022 through September 2026; 6,391,888,325 compressed bytes.
- 414,445,018 unique ordered aggregate-trade events produced 2,496,807 UTC minute bars.
- Every URL, SHA256, byte/record count, first/last ID and timestamp, ordering flag, and exact-duplicate count is in `results.json`. Local hashes identify downloaded bytes; they are not publisher signatures.
- The February 2026 SHA recorded in the amendments had two raw ordering reversals and 4,000 byte-identical duplicate rows. After complete numeric ID ordering and exact deduplication there were zero ID discontinuities, zero invalid minutes, and no timestamp reversal. No price, side, quantity, ID, or time was invented.
- Two calendar gaps remain: one missing minute in December 2022 and 152 missing minutes on 2023-03-24. They were not filled; affected entries/positions follow the frozen no-imputation rule.
- All 118 repository tests passed. The independent audit passed 53,233 chronology, overlap, fee, P/L, risk, notional, equity, run-count, manifest, and SHA checks.

| Locked period | Base trades | Base net P/L | Base PF | Stress net P/L | Stress PF |
|---|---:|---:|---:|---:|---:|
| 2022 control | 696 | -$2,535.00 | 0.441 | -$4,611.72 | 0.184 |
| 2023 OOS | 280 | -$1,300.39 | 0.325 | -$2,343.99 | 0.130 |
| 2024 OOS | 483 | -$2,312.92 | 0.356 | -$3,808.87 | 0.157 |
| 2025 OOS | 474 | -$2,382.88 | 0.263 | -$3,843.76 | 0.100 |
| 2026 OOS through September | 316 | -$1,502.87 | 0.317 | -$2,654.18 | 0.126 |
| Aggregate annual OOS folds | 1,553 | -$7,499.05 | 0.316 | -$12,650.79 | 0.129 |
| Continuous Jan 2023–Sep 2026 | 1,553 | -$5,671.63 | 0.320 | -$7,856.47 | 0.134 |

Annual folds reset $10,000 each year, so their P/L differs from the continuous path; both views repeat the same observations and are not independent samples. Annual-fold base expectancy was -$4.83 per trade and stress expectancy -$8.15. Continuous base/stress drawdown was 56.80%/78.60%. Every OOS calendar month lost on the continuous base path. The base ledger had 888 time exits, 559 stops, 104 targets, and two gap stops.

The simulation uses actual aggregate-event order and trade-price extrema, but not historical executable bid/ask queue position. Frozen 9.5 bps fees and 2 bps adverse slippage per side (both doubled under stress) partially address that limitation. Aggregate-trade events can contain multiple fills and are not individual order messages. These limitations cannot rescue evidence this consistently negative.

Reproduce from repository root (requires about 6.4 GB of source ZIPs plus temporary space for the documented 2026-02 ordering correction):

```sh
python -m unittest discover -s tests -v
python -m research.run_aggressor_sell_burst /tmp/aggtrade-archives research/aggressor_sell_burst_validation_20261027
python -m research.audit_aggressor_sell_burst research/aggressor_sell_burst_validation_20261027
```

Do not invert this losing long signal into a short strategy or retune event-run/drop thresholds on the observed data. Next concrete step: move away from Binance aggressor-flow variants and first verify a complete, timestamp-compatible, free second-exchange price source for a separately preregistered cross-exchange XRP premium-dislocation study. If synchronized source coverage is inadequate, record that before choosing another mechanism. Production, main, `v8-fly-layer-test`, Render, infrastructure, paused strategies, and LIVE trading were untouched.

