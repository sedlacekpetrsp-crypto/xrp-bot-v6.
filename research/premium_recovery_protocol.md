# XRP_CONTINUOUS_PREMIUM_RECOVERY_V1 — frozen protocol (2026-10-26)

Status: **REGISTERED; NOT EVALUATED.** Distinct mechanism: continuous perpetual mark/index premium recovery, not periodic funding, open interest/account crowding, spot flow/trade size, market breadth, pair relative strength/residuals, calendar/autocorrelation, stablecoin or triangular parity, sweep trend or ordinary breakout. Hypothesis: after an unusually deep negative perpetual premium, a material hourly premium recovery while it remains non-positive identifies deleveraging exhaustion and predicts a short XRP spot rebound.

Data: real Binance Vision monthly XRPUSDT USD-M `premiumIndexKlines` and XRPUSDT spot 1h klines, January 2022–September 2026. Record URL, byte count and local SHA256 for all archives. Sort, reject duplicates/invalid bars, intersect only exact timestamps, report all omissions/gaps and invent nothing. Signal and ATR windows must be contiguous.

Fixed causal rule on a closed hour: the prior premium close must be <=-0.10% and at/below the 2.5th empirical percentile of the preceding 720 premium closes (the extreme and confirmation hours excluded); current premium close must rise by >=0.05 percentage point yet remain <=0. Enter XRP spot long at next hourly open. ATR24; stop 1.5 ATR; target 2R; maximum 12 bars. Stop wins same-bar ambiguity; gap stop fills at worse open. Fee 9.5 bps/side plus adverse slippage 2 bps/side; stress doubles both. Risk 0.5% equity, notional <=20%, one non-overlapping position, no leverage. No funding cashflow is claimed.

2022 is control. Locked OOS quarters are 2023 Q1 through 2026 Q3; continuous OOS is non-independent. All gates: >=150 OOS trades; positive base net/expectancy and PF>1.15; positive stress net/expectancy and PF>1.02; >=10/15 positive quarters including 2026 Q3; continuous base/stress drawdown <=10%; no quarter contributes >30% of positive OOS profit. Historical passage remains `TEST NEDOKONCEN` until >=30 future days and >=100 new PAPER trades show positive stressed expectancy. No post-result tuning and no LIVE, production, Render, main or deployed-branch changes.

Next: commit the protocol, implementation, tests and provenance runner before downloading/evaluating outcomes.

## Completed historical validation — rejected

The frozen protocol SHA256 was `a730f198e0bbdc6db58c31fd10cde6407eaafa43ad9ee048f238ce895cb39d68`. The run used 57 Binance premium-index and 57 spot archives, with every URL, byte count and local SHA256 in `results.json`. There were no duplicates. Exact alignment excluded one premium-only and 48 spot-only hours, leaving one exchange-wide one-hour gap and two 24-hour premium gaps. Nothing was imputed; complete 720-hour windows suppressed signals after gaps, and no position crossed a gap.

The 15 locked OOS quarters produced 81 base-cost trades, +$146.06, PF 1.0921 and expectancy +$1.80. This is below the 150-trade and PF>1.15 gates. Doubled costs lost $199.02, PF 0.8882 and expectancy -$2.46. Nine of 15 base quarters were positive and final 2026 Q3 was positive, but the stability minimum was ten and profit concentration failed. Continuous base/stress drawdowns were 3.90%/5.05%; the 2022 control lost. Historical passage therefore fails sample, base PF, all stressed-profit gates, stability and concentration despite positive nominal base P/L.

All 70 repository unit tests passed. `audit_premium_recovery.py` independently reconciled causal premium thresholds, next-hour timing, non-overlap, holding time, sizing, fees, slippage, P/L and equity and wrote a PASS audit. Correct mechanics and a small nominal backtest gain do not establish robustness. Reject without retuning and do not promote to forward PAPER.

Next concrete step: preserve this result as an interesting but non-robust negative; do not loosen premium thresholds or costs on these periods. Preregister a different mechanism and reserve genuinely new forward evidence before any acceptance. Production isolation remains unchanged.
