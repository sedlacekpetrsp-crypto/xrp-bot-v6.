# Blue Whale / Nathan public-strategy research

Status: **NO DEPLOY**

This branch tests only the publicly inferable logic associated with the account/channel. It does **not** reconstruct paid/VIP entries.

## V1 — liquidity sweep + reversal confirmation
- BTCUSDT 1H
- ~18 months
- 70/30 train/test
- Test: 33 trades
- Win rate: 48.48%
- Profit factor: 0.781
- Net return: -1.058%
- Max drawdown: 1.714%
- Result: FAIL

## V2 — 4H levels + 1H reversal + 4H/1D context
- ~24 months
- 60/20/20 train/validation/test
- Test: 18 trades
- Win rate: 38.89%
- Profit factor: 0.854
- Net return: -0.474%
- Max drawdown: 1.662%
- Result: FAIL

## V3 — hold-or-break model
Setups:
- RECLAIM
- REJECT
- BREAKOUT + retest
- BREAKDOWN + retest

Final test:
- 116 trades
- Win rate: 28.45%
- Profit factor: 0.539
- Net return: -9.451%
- Max drawdown: 10.165%
- Result: FAIL

## V4 — fixed-parameter robustness audit
Eight sequential time windows were used to avoid choosing one favorable period.

Pass criteria fixed before the run:
- profitable in at least 5/8 windows
- pooled profit factor >= 1.10
- pooled net PnL > 0
- at least 40 trades

### Best observed candidate
Selective RECLAIM:
- 323 trades
- profitable windows: 3/8
- pooled PF: 0.913
- pooled net PnL: -446.51 USD on 10,000 USD model equity
- Result: FAIL

### Other notable candidates
Balanced REJECT:
- 297 trades
- profitable windows: 2/8
- pooled PF: 0.882
- pooled net PnL: -536.70 USD
- Result: FAIL

Balanced RECLAIM:
- 320 trades
- profitable windows: 3/8
- pooled PF: 0.833
- pooled net PnL: -842.18 USD
- Result: FAIL

Selective BREAKOUT:
- 72 trades
- profitable windows: 0/8
- pooled PF: 0.358
- pooled net PnL: -1,112.53 USD
- Result: FAIL

## Conclusion
No tested public-style setup showed a stable positive edge after simulated fees and slippage.

Therefore:
- do not deploy a PAPER or live bot from this public strategy;
- do not merge this research into V8.1 or V9;
- keep the branch isolated for audit/reproducibility;
- only reopen the idea if complete timestamped signals with entry, stop and exit/TP become available.

This conclusion applies only to the publicly inferable strategy, not to any undisclosed VIP method.
