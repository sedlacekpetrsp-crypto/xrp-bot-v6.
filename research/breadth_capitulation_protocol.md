# ALT_BREADTH_CAPITULATION_REVERSAL_V1 — frozen protocol (2026-10-26)

Status: **REGISTERED; NOT EVALUATED.** Distinct mechanism: broad cross-sectional crypto capitulation, not XRP relative strength, pair residuals, lead/lag, derivatives positioning/funding, spot taker flow, trade size, calendar drift, autocorrelation, stablecoin/triangular parity, sweep trend or ordinary single-market breakout. Hypothesis: when most independent liquid crypto markets sell off together and XRP participates, forced broad risk reduction temporarily overshoots and XRP has positive next-day rebound expectancy.

Data: actual Binance Vision monthly spot 1h klines, January 2022–September 2026, for XRPUSDT and a fixed breadth basket of BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT, ADAUSDT, DOGEUSDT, LINKUSDT and LTCUSDT. Record every URL, byte count and locally calculated SHA256. Sort, reject duplicates/invalid bars, preserve/report gaps and never impute. A signal requires exact current and six-hour-prior timestamps for all eight basket members and a contiguous XRP ATR/entry window.

Fixed signal on a closed hourly bar: at least 6/8 basket members have six-hour close return <=-2.0%; median basket return <=-2.0%; XRP six-hour return <=-2.5%. Enter XRP spot long at next hourly open. ATR24; stop 1.5 ATR; target 2R; max hold 24 bars. Stop wins same-bar ambiguity; gap stop fills at worse open. Fee 9.5 bps/side and adverse slippage 2 bps/side; stress doubles both. Risk 0.5% equity, notional <=20%, one non-overlapping position, no leverage.

2022 is control. Locked OOS quarters are 2023 Q1 through 2026 Q3; continuous OOS is non-independent. All gates: >=150 OOS trades; positive base net/expectancy and PF>1.15; positive stress net/expectancy and PF>1.02; >=10/15 positive quarters including 2026 Q3; continuous base/stress drawdown <=10%; no quarter contributes >30% of positive OOS profit. Historical passage remains `TEST NEDOKONCEN` until >=30 future days and >=100 new PAPER trades show positive stressed expectancy. No parameter tuning after results and no LIVE, production, Render, main or deployed-branch changes.

Next: commit this protocol, implementation, deterministic tests and provenance runner before downloading/evaluating outcomes.

## Completed historical validation — rejected

The frozen protocol SHA256 was `3a19639a54419df24b9bd86d2bae378656bae1f250a379af137d74e1d404b732`. The run used 513 real Binance Vision monthly archives (nine markets x 57 months), with every URL, byte count and local SHA256 in `results.json`. No duplicate bars were found. All nine markets share one missing exchange hour between 2023-03-24 12:00 and 14:00 UTC; it was retained without imputation, causal lookbacks crossing it were ineligible, and no position crossed it.

The 15 locked OOS quarters produced 405 base-cost trades, -$1,549.54, PF 0.8500 and expectancy -$3.83. Doubled costs produced 406 path-dependent trades, -$3,112.40, PF 0.7243 and expectancy -$7.67. Only five quarters were base-cost positive; final 2026 Q3 lost $180.37. The continuous, non-independent OOS path lost $1,478.45 with 20.21% maximum drawdown; stress lost $2,738.59 with 28.71% drawdown. The 2022 control also lost. Only the sample-size gate passed; all profitability, stress, stability, final-quarter, drawdown and concentration gates failed.

All 64 repository unit tests passed. `audit_breadth_capitulation.py` independently reconciled timing, frozen thresholds, non-overlap, holding time, sizing, fees, slippage, P/L and equity and wrote a PASS audit. Mechanics success is not evidence of a profitable edge. Reject without threshold retuning and do not promote to forward PAPER.

Next concrete step: do not loosen breadth/drop thresholds on these observed periods. Preregister a different mechanism and preserve genuinely new forward observations before any acceptance; production isolation remains unchanged.
