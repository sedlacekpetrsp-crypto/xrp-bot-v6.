# ADA_STATE_CLASSIFIER_V1 preregistration — 2026-10-24

## Distinct hypothesis

A strongly regularized linear classifier can combine medium-horizon return, realized volatility,
range, volume shift and mean distance into a causal probability of ADA's next 24-hour direction.
This is a frozen supervised state model on a previously untested asset, not a manual variation of
the rejected trend, shock, flow, range, calendar, pair or derivatives-threshold rules.

## Frozen training and execution

- Public Binance Vision ADAUSDT spot 1-hour archives, December 2020–September 2026, resampled only
  from complete aligned 4-hour groups. Train solely on 2021–2022; development is 2023; untouched
  validation is 2024 H1/H2, 2025 H1/H2 and January–September 2026.
- Six completed-bar features: 24h/72h log return, 72h realized volatility, 24h high-low range,
  six-bar versus prior-18-bar quote-volume shift, and distance from the 30-bar mean. Label is the
  sign of the next six-bar return. StandardScaler plus logistic regression uses fixed `C=0.1`,
  balanced class weights, LBFGS and seed 0. No validation tuning.
- Probability >=0.60 enters long next open; <=0.40 enters short. Position is 20% of equity; 6%
  stop, 8% target, six-bar maximum hold and two-bar cooldown; no overlap. Same-bar ambiguity is a
  stop and adverse stop gaps fill at the open.
- Normal per-side fee 0.095%, adverse slippage 0.020% and short borrow 8% annualized. Stress doubles
  all three. Fitted scaler and coefficients are written to the result for reproducibility.

## Frozen success criteria

Historical eligibility requires positive 2023 development return; at least 80 validation trades;
each direction at least 20%; normal PF >=1.20; stress PF >=1.05; every validation block positive
normally; at least four positive under stress; positive combined stress return; normal drawdown
<=15%; and no block over 50% of summed positive P&L. Robust status additionally requires 50 new
isolated forward PAPER trades without retraining. Historical passage alone is not evidence of
future profitability.
