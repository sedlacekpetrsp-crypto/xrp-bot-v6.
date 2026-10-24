# TRIANGULAR_PARITY_V1 preregistration — 2026-10-24

## Distinct hypothesis

Temporary violations of BTC–ETH–USDT triangular parity can remain profitable after three-leg
execution costs. On a completed synchronized 5-minute bar, calculate both USDT→BTC→ETH→USDT and
USDT→ETH→BTC→USDT gross cycles. If the better dislocation is at least 0.50%, execute that full
cycle only at the next synchronized open. This is atomic cross-rate parity, not a directional,
trend, reversion, flow, pair-spread, classifier or derivatives-carry strategy.

## Frozen data and execution

- Public Binance Vision BTCUSDT, ETHUSDT and ETHBTC spot 5-minute archives, December 2022 through
  September 2026. Development is 2023; untouched validation is 2024 H1/H2, 2025 H1/H2 and
  January–September 2026. Only timestamps present in all three pairs are eligible.
- Allocate 20% of current equity per cycle and wait 12 bars after execution. All three legs use
  the next bar's opens; any signal-to-execution gap is therefore realized directly. The cycle has
  no held position or stop after its third leg, and cycles cannot overlap.
- Normal fee is 0.095% per leg plus 0.020% adverse slippage per leg. Stress doubles both. No
  parameter search or threshold change follows this preregistration.

## Frozen success criteria

Historical eligibility requires positive 2023 return; at least 100 validation cycles; each route
at least 20%; normal PF >=1.20; stress PF >=1.05; every validation block positive normally; at
least four positive under stress; positive combined stress return; drawdown <=5%; and no block
above 50% of summed positive P&L. Robust status additionally requires 100 new sequential forward
PAPER cycles using executable quotes. OHLC backtest passage alone is not proof of profitability.
