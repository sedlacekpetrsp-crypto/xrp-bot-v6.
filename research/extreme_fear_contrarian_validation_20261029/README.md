# XRP_EXTREME_FEAR_CONTRARIAN_V1 — completed historical validation

Decision: **NEPROŠEL**. The frozen sentiment candidate is not promoted to forward PAPER despite positive aggregate history.

The protocol and source SHA256 were committed before evaluation. The rule bought XRP only when the prior calendar day's Alternative.me Fear & Greed value was <=20, entered at the next daily open, and never used classification text or an XRP price/volume confirmation. No threshold or exit was tuned after results.

## Data and mechanics

- Alternative.me direct API: 3,189 unique daily observations from 2018-02-01 through 2026-10-29; API metadata reported no error.
- Binance Vision: 81 direct XRPUSDT daily monthly archives, January 2020 through September 2026; 2,465 unique consecutive price days.
- Exact-date intersection produced 2,464 days. One missing sentiment date, 2024-10-26 UTC, was retained as a gap; no value was carried forward or fabricated. One price-only day and 725 sentiment-only dates were excluded.
- All direct URLs, bytes, row counts and locally computed SHA256 fingerprints are in `results.json`; hashes identify downloaded bytes and are not publisher signatures.
- Execution: full-day metric lag, next-open entry, one long spot position, 0.5% equity stop risk, 20% notional cap, 2 ATR stop, 3R target, maximum ten days. Base fee/slippage were 9.5/2 bps per side; stress doubled both. Gap exits used adverse prices and stop won same-candle ambiguity.
- All 192 repository tests passed. The independent ledger audit passed 1,714 checks covering causal timing, threshold, non-overlap, risk/notional, costs, slippage, P/L, counts and decision gates. Passing mechanics are not profitability evidence.

## Locked chronological results

| Annual OOS fold | Trades | Base net P/L | Base PF | Stress net P/L | Stress PF |
|---|---:|---:|---:|---:|---:|
| 2022 | 20 | +$249.95 | 2.029 | +$233.79 | 1.936 |
| 2023 | 0 | $0.00 | n/a | $0.00 | n/a |
| 2024 | 1 | -$17.87 | 0.000 | -$18.55 | 0.000 |
| 2025 | 6 | -$81.27 | 0.320 | -$86.01 | 0.295 |
| 2026 Jan–Sep | 14 | +$25.49 | 1.110 | +$9.74 | 1.041 |
| **Annual folds combined** | **41** | **+$176.30** | **1.288** | **+$138.97** | **1.221** |

Combined expectancy was +$4.30 base and +$3.39 stressed. The separate continuous January 2022–September 2026 path produced 41 trades, +$174.34, PF 1.282 and 2.25% drawdown; stress produced +$136.81, PF 1.216 and 2.31% drawdown. The continuous path reuses the annual observations and is not additional evidence.

The base/stress profit, expectancy, PF, final-2026 and drawdown gates passed. The candidate still fails decisively because 41 trades are below the frozen 75 minimum, only 2022 and 2026 are profitable, 2023 has no exposure, 2024–2025 lose, and September 2022 supplies too much positive profit. The 2020–2021 control also loses at both costs. Do not lower the sample gate, call zero exposure profitable, or select 2022/2026 after observation.

Reproduce from repository root:

```sh
python -m unittest discover -s tests -v
python -m research.run_extreme_fear_contrarian /tmp/fear-data research/extreme_fear_contrarian_validation_20261029
python -m research.audit_extreme_fear_contrarian research/extreme_fear_contrarian_validation_20261029
```

Preserve the frozen rule only as a documented near-signal. It is not forward-promoted; reconsideration would require genuinely independent future extreme-fear episodes under unchanged rules. No production, Render, infrastructure, paused strategy or LIVE setting was changed.
