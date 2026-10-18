# Frozen ELITE V12–V14 batch — 2026-10-14

Research only. No existing bots or Render configuration changes; no real orders.
Prior V8–V11 showed concentrated profits and insufficient evidence. This batch
keeps all discovery and challenge gates from PROTOCOL_V8_V11.md unchanged.
No parameter grid. No lowering thresholds after observing results.

## Three fixed hypotheses
- V12: exactly V8's shock/recovery entry logic on completed 1h bars instead of
  4h; negative return < -2.5 SD of previous 30 returns (excluding shock and
  rebound), followed by a positive close above shock midpoint. Stop 2 ATR,
  target 4 ATR. Maximum holding time 12 hourly bars (=144 five-minute bars),
  preserving V8's 12-signal-bar horizon. This tests timeframe transfer, not an
  independent family. Do not assume higher frequency improves profitability.
- V13: 4h simple 14-change RSI recovery through 30 from <=30, confirmed positive
  close. Stop 3 ATR, target 6 ATR, max holding 7 days. Flat RSI =50, zero-loss
  positive changes RSI=100. This tests sustained recovery after oversold moves,
  distinct from the earlier two-period trend-pullback RSI entry.
- V14: hourly narrow-range breakout. Previous bar's high-low range <= minimum
  of the previous 24 ranges; current close > previous high, positive close,
  and in upper 20% of its own range. Stop 2 ATR, target 6 ATR, maximum 48h.
  This is a volatility-expansion family, related to V2; it is not called a new
  independent statistical discovery merely because it has another version.
ATR is the simple mean of the last 14 true ranges through the closed signal bar.
No shorts, leverage, martingale or averaging down.

## Evaluation (unchanged)
April 2023–September 2026 is DEVELOPMENT ONLY, with blocks Apr–Dec 2023,
H1 2024, H2 2024 and Jan 2025–Sep 2026. All candidates must have positive net
P/L in >=3/4 blocks, continuous PF>=1.2, >=60 trades, close MTM DD<=10%,
intrabar bound<=12%, positive stress P/L and positive 95% lower daily-P/L bound
from the existing 7-day block bootstrap, 2000 draws, seed713.
10,000 USDT start, risk 0.5%, max allocation35%; baseline per-side fees/slippage/
half-spread .001/.0003/.0001, stress doubles all. Next5m open fills; existing
engine's conservative stops and cost-inclusive risk sizing remain unchanged.
Report every candidate, continuous and reset-block results, buy/hold baselines,
full base/stress ledgers and daily equity. Analyse contribution of the largest
one/three winners as a sensitivity diagnostic, not a newly invented pass gate.

Only frozen discovery survivors can access reserved 2022 historical challenge
(H1/H2 separately, both net/stress positive, both PF>=1.2, combined>=30 trades,
close DD<=10%, intrabar bound<=12%, continuous bootstrap lower bound>0).
2021 remains reserved. Historical challenge is backward testing, not forward
walk-forward OOS. A pass does not establish live profitability. A further
prospective PAPER observation is required before live consideration.
Archive all failures rather than hiding them. If no candidate passes, do not
unlock the challenge or prepare an approved PAPER deployment.
