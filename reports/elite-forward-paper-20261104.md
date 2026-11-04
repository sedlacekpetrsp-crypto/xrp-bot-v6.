# ELITE V18 and V56: experimental forward PAPER deployment

The user explicitly requested deployment of the promising candidates on
2026-11-04 after discussing the lack of a fully validated strategy. This is a
new experimental forward collection, not retrospective acceptance under the
original research gates. The old reports and their rejection decisions remain
unchanged. No LIVE orders or brokerage credentials are used by the module.

## Selection and limitations

Source: `elite-research-v1`, commit `01c30707b8532af4421e87befa9cef22729149bc`.

| Candidate | Historical net return | Double-cost return | Close drawdown | Trades |
|---|---:|---:|---:|---:|
| V18, hourly breakout with BTC trend filter | 47.18% | 35.63% | 11.15% | 97 |
| V56, four-hour adaptive-average reclaim | 8.21% | 6.01% | 2.18% | 77 |

These are total returns for April 2023–September 2026, repeatedly used
development data, NOT annual returns or independent OOS results. V18 exceeded
the drawdown limit. V56 had only 2/4 profitable blocks and 92.5% of its profit
in three trades. Neither met all historical acceptance criteria. See
`elite/REPORT_COST_AUDIT_20261016.md` and `elite/REPORT_V56_20261017.md` on the
source branch. Selection is exploratory and subject to multiple-testing bias.

## Execution

- Two independent virtual 10,000 USDT books; XRPUSDT spot LONG, no leverage.
- Fixed signal rules, risk 0.5% each, maximum allocation 35%, one position each.
- Fee 0.10% plus slippage/half-spread 0.04% on each side, including sizing.
- Signals use closed candles. Entry uses an observed quote within 90 seconds
  after a NEW signal close. Startup does not enter on a historical signal.
  Candles wait 30 seconds after close to outlast the shared 15-second cache.
- Data provider is recorded and pinned per book. A provider change or missing
  history pauses processing instead of silently splicing series.
- V56 warms up from available history (up to 720 four-hour candles) and persists
  that history; future restarts do not reseed the adaptive average. This seed
  differs from the historical backtest start and is not claimed identical.
- Quote polling approximately every 20 seconds. Stops also inspect fully
  post-entry closed 5m bars, conservatively using the minimum of the stop,
  observed quote and gap open. The entry candle's pre-entry low is excluded.
  A transient stop hit within that partial entry candle can therefore be missed
  between polls. This is sampled PAPER execution, not exchange execution.
- Outages pause all processing. Gap recovery uses available closed bars for
  stops and current quotes for exits, never retrospective profitable entries.
- Database transactions commit state and OPEN/CLOSE events together; locks
  serialize overlapping workers. Accounts are never reset on deployment.
- Only the existing paid service `srv-dang770ae00c73em1sm0` starts the module.
  All other strategies and their account histories remain unchanged.
- Status: `/elite-paper/status`; tables `elite_forward_accounts` and
  `elite_forward_events`. New forward results start at zero, separate from
  historical backtests. Current source revision is visible in Git/Render.

## Validation before deployment

Ten focused tests cover fees and risk, stops/gaps, no retrospective entries,
repeat observations/restart state, provider change, history continuity and
initial warmup. On deterministic synthetic OHLC, 1,252 decisions (including
30 entry signals) match the original research functions exactly using the
same input history. This checks the signal port, not profitability.

Full pytest comparison: 206 passed / 19 failed on this change versus 196 passed /
the exact same 19 failed on baseline `8184264` (TV consensus and old Whale tests).
There are no newly failing test names. Local dashboard and status requests both
return HTTP 200; the new dashboard card is present and the mode is PAPER.
