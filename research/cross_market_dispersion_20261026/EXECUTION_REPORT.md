# Execution result — 2026-10-26

**NEPROŠEL / REJECTED under the frozen acceptance gates.** The GitHub Actions job succeeded technically; that does not mean the trading strategy passed.

Final code commit: `9c7cf363072a170d68400e692fce640cb8f67467`.
Verified GitHub run: https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./actions/runs/40368025792

## Validation

12 deterministic unit tests passed locally and on GitHub. Downloaded 228 public Binance Vision monthly spot archives (four assets, Jan 2022–Sep 2026), verified their published SHA256 checksums, validated OHLC and aligned timestamps. Independent ledger reconciliation checked both legs' notionals, entry/exit costs, synthetic borrow, non-overlap and compounded equity for all 137 trades in each cost scenario. `audit.json`, `unit_tests.log`, `results.json` and both compressed trade ledgers preserve evidence. The rerunnable reconciliation is `research/audit_dispersion_20261026.py`.

## Data qualification

The strict no-gap historical input gate FAILED: the aligned series has 41,615 hours instead of 41,616, with the missing UTC hour 2023-03-24 13:00. No synthetic candle was inserted. A clearly labelled **diagnostic** backtest uses two contiguous blocks with a new 180-observation warmup after the gap. Thus the complete frozen full-coverage experiment is not claimed. This gap is before the OOS period; all 2025–Sep 2026 observations fall in the second continuous block. The final day cannot open a trade without a next-day exit price, so it is excluded.

## Results after costs

| Period | Trades | Base return | Base PF | 2x-cost return | 2x-cost PF |
|---|---:|---:|---:|---:|---:|
| All diagnostic history | 137 | -24.52% | 0.240 | -29.57% | 0.177 |
| 2025–Sep 2026 OOS | 48 | -8.41% | 0.142 | -11.00% | 0.066 |
| 2025 | 24 | -5.24% | 0.099 | -6.80% | 0.036 |
| Jan–Sep 2026 | 24 | -3.35% | 0.205 | -4.51% | 0.110 |

Returns are relative to equity at the first trade of each period, carried forward from a 10,000 initial account. Conservative full-history hourly drawdown bound: **25.01% base / 29.96% stress**, exceeding the 10% ceiling. Period drawdown fields retain the full-history high-water mark; they are not period-reset drawdowns. Only 48 OOS spreads versus the required 100; both profit-factor thresholds and both positive-calendar-year gates fail. Profit concentration is undefined for negative net profit and cannot satisfy the acceptance gate. No strategy parameters were optimized or retuned.

## Corrections and limitations

- Removed retroactive paired exits at the hour's open for intrabar stops. Gap triggers exit both legs at the open; intrabar stops use the other leg's adverse hourly extreme as a conservative bound. These are not claimed as exact executable fills.
- Charge an intrabar stop hour conservatively in borrow duration. Include both legs' entry and exit fees, adverse slippage and doubled borrow in stress.
- Record hourly adverse equity bounds and preserve the high-water mark across data gaps. Simultaneous candle extremes may not occur together; the drawdown estimate is deliberately conservative.
- Validate nonempty hourly timestamps and add economic ledger fields, calendar/OOS metrics, gates, archive checksum provenance and explicit gap diagnostics.
- Shorts remain synthetic spot shorts; actual borrowing availability and financing were not verified. Previously studied history is not a pristine holdout. No forward PAPER evidence exists.

Do not promote this candidate to production or LIVE. Production bots, Render configuration, main branch and paid services were not changed. Only the requested research branch was updated. The isolated workflow now triggers on relevant code pushes to this branch as well as manual dispatch; results-only commits do not trigger it.
