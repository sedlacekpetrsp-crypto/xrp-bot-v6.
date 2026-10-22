# DOWNSIDE_IMBALANCE_SHORT_V1 preregistration — 2026-10-22

## Distinct hypothesis

After a completed 24-hour window in which squared negative hourly returns dominate squared
positive returns, price is down at least 2%, and the close remains in the bottom quarter of the
window, selling pressure will persist over the next eight hours. This is a directional short
continuation hypothesis, not a variation of rejected sweep, flow-pressure, cross-sectional,
pairs, broad-shock rebound, or monthly momentum models.

## Fixed rules before historical results

- Universe: BTCUSDT, ETHUSDT, SOLUSDT, XRPUSDT, Binance spot public 1h archives.
- Signal on completed bars only: 24 hourly log returns, downside/upside squared-return energy
  ratio at least 2.5, at least eight negative hours, 24h close return at most -2%, and close
  location in the 24h high-low range at most 0.25.
- Enter short at the next bar open; rank simultaneous signals by energy ratio.
- Exit: 3.5% stop, 4% target, or eight-hour maximum hold. Stop wins if both levels occur in one
  hourly candle. A stop gap fills at the worse open; a favorable target gap receives only the
  target price.
- Portfolio: at most two positions, no duplicate symbol, 17.5% of current equity per position
  (35% maximum gross exposure), and a 12-hour per-symbol cooldown after exit.
- Base costs: 0.095% fee and 0.02% slippage per side plus 8% annualized short borrow, accrued
  hourly. Stress test doubles all three costs.
- Incomplete days are removed across all symbols; no missing candle is synthesized. Inputs and
  downloaded ZIP SHA-256 hashes are recorded. Equity is marked hourly.

## Chronological protocol and pass criteria

- Development: calendar 2021 and 2022. Both must be net positive at base costs.
- Untouched validation: 2023, 2024, 2025, and 2026-01-01 through 2026-09-30.
- Validation must have at least 150 closed trades, combined PF >= 1.20 at base costs and >= 1.05
  at doubled costs, every block positive at base costs, at least three of four blocks positive
  under stress, combined stressed return positive, maximum drawdown <= 15%, and no one positive
  block may supply more than 60% of summed positive block P&L.
- A robust candidate additionally requires at least 50 entirely new forward PAPER trades under
  the frozen rules. Historical passage alone is not evidence of future profitability.

Parameters will not be changed after reading development or validation results. A failed gate
retires V1 rather than triggering optimization on these same validation blocks.
