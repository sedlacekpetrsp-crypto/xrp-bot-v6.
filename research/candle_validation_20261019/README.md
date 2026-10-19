# Fixed candle experiments and FAST audit — 19 October 2026

Research only. No Render branch, pause, live strategy, position, balance or account
setting was changed. Neither candidate is approved for deployment.

## FAST audit

In the source defaults, round-trip cost = 2 × (0.095% fee + 0.02% slippage)
= 0.23%. FAST requires estimated travel >= 2.25 × that cost = 0.5175%.
Units are consistent: these values are fractional price changes, not percentage
points. The issue is the travel estimate, not a discovered decimal-point bug.

FLY supplies `expected_move_pct = ATR1m / price × 1.05 × 1.90`, or 1.995 ATR.
Original FAST takes `max(expected_move_pct, 4.5 × ATR1m / price)`. With the
same defaults this is simply 4.5 ATR and requires ATR1m/price >= 0.115%.
The earlier research `min` candidate instead requires about 0.2594%, making it
approximately 2.26 times stricter. Neither multiplier establishes predictive
mean-reversion edge. The threshold should not be reduced solely to force trades.
An independently validated distance-to-mean/reversal model would be required.
The previous FAST `min` experiment remains unapproved and is not deployed.
These calculations describe source defaults; archived run configuration is
required for exact replication of any historical runtime configuration.

## New frozen rules

Data: XRPUSDC 15m, 18 April–19 October 2026, with seven days of earlier warmup.
Development ends 18 August; subsequent two months are held aside for the fixed
chronological check. Source/protocol were committed before results. No parameter
search, threshold changes or strategy selection occurred after opening holdout.
Prior unrelated research may have observed this market period; it is not claimed
to be universally unseen history. Reusing it for later tuning would invalidate
its role as a fresh holdout.

All four versions use the same closed 1h EMA20/50 directional regime, execution,
fees and notional. Comparators are simple candle references, **not** full
FLY/FAST/TV reproductions; six-month comparisons to those bots are not claimed.

- Breakout reference: close above/below the preceding 20-bar extreme.
- Breakout/retest: arm on that breakout, require a retest within four subsequent
  bars, tolerance 0.25 ATR; close on the breakout side, within one ATR of the
  level, with a directional candle. Cancel on expiry or trend loss.
- EMA cross reference: 15m EMA20 crosses EMA50 in the hourly trend direction.
- EMA pullback: one of the last three bars touches EMA20; confirm by a close
  beyond the preceding bar's high/low with 15m EMA20/50 and hourly alignment.

Signals use closed bars; fills occur at the next open. Fixed 1,000 USDC notional,
10,000 starting equity per period/strategy, one position. No time exit except
period end. Stop is 1.5 ATR widened by 15%, with unchanged quantity and target;
target is twice the original stop distance. Stops are evaluated before targets
when OHLC cannot determine order. A target already crossed by the opening gap
is filled conservatively at target before a later intrabar stop. Entry and exit
fees and adverse slippage are included. Close-marked drawdown is not intrabar
maximum drawdown. No book, spread, liquidity, borrow or funding history exists
in this candle simulation. SHORT is synthetic PAPER and does not demonstrate
that a spot short can be executed. No live trading approval follows.

## Final results, net USDC

| Rules | Development trades / net | Holdout trades / net | Holdout PF | Holdout doubled slippage |
|---|---:|---:|---:|---:|
| Breakout reference | 285 / -772.60 | 161 / -150.00 | 0.868 | -210.39 |
| Breakout/retest | 106 / -219.96 | 54 / +25.28 | 1.066 | -18.63 |
| EMA cross reference | 78 / -203.07 | 36 / -248.65 | 0.208 | -255.86 |
| EMA pullback | 303 / -506.79 | 146 / -158.26 | 0.842 | -187.38 |

Breakout/retest fails the fixed PF >= 1.2 and positive cost-stress requirements,
and loses 194.67 across the two independently funded windows. EMA pullback loses
665.04 combined. More signals did not produce positive net expectancy. Do not
select or deploy the small positive retest holdout in isolation.

Seven new engineering tests check prefix invariance, closed-hour features,
next-open execution, SL/TP collision priority, opening gaps, both-side costs,
unchanged size/target when widening SL, and balance reconciliation. Together
with the previous targeted tests, 63 pass. This is not the whole legacy suite.
A target-gap ordering bug was corrected after the first calculation; all periods
and cost scenarios were rerun without strategy changes and results were identical.

Reproduce:

```sh
python research/candle_validation_20261019/download.py /tmp/candle-six-month
python -m unittest test_candle_research
python research/candle_validation_20261019/run.py /tmp/candle-six-month/candles.json development
python research/candle_validation_20261019/run.py /tmp/candle-six-month/candles.json holdout
```

Public market data hashes and summaries are included; the runner reproduces
trade-level simulations locally. Private
Render snapshots, real account ledgers and credentials are not included.
