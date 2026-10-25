# PAPER research candidates — 18 October 2026

**Not approved for deployment.** This branch is based on production source
`218a63f2d01842de3308adeb14d37afab88120c0`. It is not a Render deployment branch.
The existing FLY / FAST / Lead-Lag / TV pauses remain unchanged. No live orders,
position resizing, stop changes or account resets are introduced.

## Candidates

- Shared entry guard: at most one open position per underlying asset across
  FLY, FAST, Lead-Lag, TV and Whale, including opposite directions and USDT/USDC
  quote aliases. Uses the real FLY `paper_position`, not unused uppercase fields.
  Missing exposure symbols fail closed. This is an admission cap, not a new
  aggregate portfolio VaR model. BEST and other engines remain outside its scope.
  Existing exit management is untouched. Calls are synchronous in the existing
  single-process service; this is not a distributed multi-instance lock.
- FLY: reject absolute momentum z greater than 3, including nonfinite values,
  at the shared entry boundary for closed-candle and armed entries. Fixed
  exploratory threshold, not an empirically validated optimum.
- FAST: bound the signal's expected move by the ATR travel estimate using `min`,
  instead of manufacturing a larger expected move using `max`. Existing fee/edge
  threshold remains. ATR and expected move are heuristics, not a proven forecast.
- TV: existing 5m/15m checks plus closed 1h close/EMA20/EMA50 alignment in the
  **offline runner only**. No unfinished hourly filter is wired into production.
- Lead-Lag and Whale: no new signal parameters promoted; existing pause and
  Whale actual-stop risk protections retained. Shared overlap policy is a
  research candidate for both.

## Validation and limits

44 targeted tests pass, covering shared-asset admission, real FLY position
state, pause preservation, exclusion of unrelated bots, unknown exposure,
half-open trade intervals, duplicate IDs, FAST edge filtering, FLY exhaustion,
closed hourly bars, research capture isolation, Whale stop risk and stop policy.
This is not a claim that every historical test in the repository passes.

Private account ledgers are deliberately absent. `audit.py /path/to/ledger.json`
prints an overlap and fixed-fill exclusion analysis. Input rows need bot, id,
symbol, side, opened_at, closed_at, net_pnl and fees. Canonicalize known duplicates
before export. Unknown asset pairs are explicitly counted. Excluding existing
fills is **not** a backtest: new signals, changed equity, capacity and substituted
trades are not reconstructed. Pair-duration sums can overlap and must not be
interpreted as total wall-clock exposure time.

The TV replay uses production signal, entry and exit functions with public
XRPUSDC minute candles. Fee is 0.095% per side, slippage 0.02% per side; stress
case doubles slippage. Stop precedes target on an ambiguous candle, stop gaps
fill at open, and profit protection updates at close. SL multiplier stays 1.15.
Each window has its own 10,000 starting balance. Drawdown is based on realized
balance, not intrabar equity. This is descriptive replay of already observed
history, not pristine out-of-sample validation. Fewer trades alone is not an edge.

`tv_results.json` reproduces the short October 13–17 comparison.
`tv_month/` extends the same two fixed variants to September 17–October 18 05:00
UTC, split at October 10. No parameter search or retrospective threshold change.
Results and hashes accompany each run. Cached signals are keyed by data and
signal/runner source, rather than reused across changed input data.

Reproduce the monthly test:

```sh
python research/paper_overlap_20261018/tv_month/download.py /tmp/tv-month
python research/paper_overlap_20261018/tv_month/run_tv.py /tmp/tv-month/XRPUSDC_1m.json
python -m unittest test_paper_overlap_candidate test_fly_entries test_tv_pause_review test_research_market_evidence test_whale_actual_stop_risk test_whale_reversion_pause test_paper_stop_policy
```

FLY/FAST/Lead-Lag cannot yet be validated against a long continuous historical
order-book/news archive. OHLCV must not silently replace those inputs. Existing
prospective capture continues independently of trading. Whale candidate marks
alone do not establish a new strategy's profitability.
A deployment needs both engineering checks and adequate chronological evidence
after costs; these research changes do not authorize resuming paused strategies.

## Monthly results (USDC, after costs)

| Variant | First window trades / net | Later window trades / net | Later PF | Later double-slippage net |
|---|---:|---:|---:|---:|
| Production baseline | 39 / -108.74 | 14 / -53.65 | 0.210 | -51.00 |
| Closed 1h alignment | 23 / -113.22 | 9 / -28.13 | 0.323 | -24.70 |

Both numeric gates fail. The hourly filter worsens the first window and reduces
trade frequency; the reduction in combined loss is not profitability evidence.
Stress results need not be monotonic because production sizing, targets and
profit protection depend on costs; this is a full rerun, not a fee subtraction.
Trade-level net sums reconcile with simulated balance changes in both windows.
No candidate is deployed or enabled.
