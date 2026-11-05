# Hlasování časového momenta 1/3/6/12 m BTC/ETH — výsledky (protokol `PROTOCOL.md`)

**Verdikt: ZAMÍTNUTO** — jediná předem daná varianta (váha = podíl kladných horizontů 30/91/182/365 dní, měsíční rebalance).

| kritérium | splněno |
|---|---|
| 1_validation_sharpe_and_dd_beat_bh_x1 | NE |
| 2_validation_trades_ge_30 | ano |
| 3_validation_x2_pf_gt_1_2_and_net_gt_0 | ano |
| 4_validation_x1_net_without_top3_gt_0 | ano |
| 5_final_x2_net_gt_0_sharpe_and_dd_beat_bh | NE |

## Strategie vs. buy & hold (koš 2 × 50 %)

| období | náklady | čistý P/L | výnos % | Sharpe | max DD % | obchody | PF | win % | bez top 3 | Ø dní | B&H výnos % | B&H Sharpe | B&H max DD % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tuning | ×1 | 28450.24 | 284.5 | 1.26 | 45.7 | 26 | 1.74 | 42 | -20555.03 | 55.0 | 108.4 | 0.80 | 76.9 |
| tuning | ×2 | 28242.40 | 282.4 | 1.26 | 45.9 | 26 | 1.73 | 42 | -20675.91 | 55.0 | 107.9 | 0.80 | 76.9 |
| tuning | ×3 | 28035.85 | 280.4 | 1.25 | 46.0 | 27 | 1.73 | 41 | -20795.75 | 54.0 | 107.4 | 0.80 | 76.9 |
| validation | ×1 | 10827.45 | 108.3 | 1.14 | 32.4 | 34 | 2.49 | 59 | 3007.04 | 42.0 | 321.4 | 1.71 | 34.0 |
| validation | ×2 | 10671.84 | 106.7 | 1.13 | 32.5 | 34 | 2.46 | 59 | 2908.95 | 42.0 | 320.4 | 1.70 | 34.0 |
| validation | ×3 | 10517.53 | 105.2 | 1.12 | 32.6 | 34 | 2.44 | 59 | 2811.66 | 42.0 | 319.5 | 1.70 | 34.0 |
| final_test | ×1 | -2141.46 | -21.4 | -0.37 | 33.0 | 24 | 0.57 | 38 | -3483.15 | 43.0 | -24.9 | -0.04 | 60.0 |
| final_test | ×2 | -2197.35 | -22.0 | -0.38 | 33.2 | 24 | 0.56 | 38 | -3530.25 | 43.0 | -25.1 | -0.04 | 60.0 |
| final_test | ×3 | -2252.79 | -22.5 | -0.40 | 33.5 | 24 | 0.56 | 38 | -3576.95 | 43.0 | -25.3 | -0.04 | 60.0 |

Průměrná cílová váha (měsíce, oba symboly): tuning 59 %, validation 71 %, final_test 47 %

## Informační varianty (validace ×1, NEJSOU kritériem, nic se nevybírá)

| varianta | čistý P/L | Sharpe | max DD % | obchody | PF |
|---|---|---|---|---|---|
| h3_monthly | 9655.73 | 1.07 | 32.4 | 30 | 2.45 |
| h4_weekly | 16162.78 | 1.44 | 27.2 | 72 | 2.29 |

Pozn.: data navíc 2019-09…2019-12 jen jako zahřátí 365denního horizontu pro ladicí období.
Výhradně PAPER výzkum. Ani kladný verdikt neznamená ziskovou strategii — jen kandidáta na forward PAPER.
