# Mean-reversion ETHBTC z20 ±2 (koš BTC/ETH) — výsledky (protokol `PROTOCOL.md`)

**Verdikt: ZAMÍTNUTO** — jediná předem daná varianta (z20, práh ±2, výstup při z přes 0).

| kritérium | splněno |
|---|---|
| 1_validation_sharpe_and_dd_beat_bh_x1 | NE |
| 2_validation_episodes_ge_30 | NE |
| 3_validation_x2_pf_gt_1_2_and_net_gt_0 | ano |
| 4_validation_x1_net_without_top3_gt_0 | ano |
| 5_final_x2_net_gt_0_sharpe_and_dd_beat_bh | NE |

## Strategie vs. buy & hold koše BTC/ETH 50/50 (bez rebalance)

| období | náklady | čistý P/L | výnos % | Sharpe | max DD % | epizody E/B | P/L epizod | PF epizod | bez top 3 | rozdíl vs B&H | B&H výnos % | B&H Sharpe | B&H max DD % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tuning | ×1 | 2717.51 | 27.2 | 0.53 | 81.1 | 24 | 10673.71 | 1.22 | -21674.65 | -8121.20 | 108.4 | 0.80 | 76.9 |
| tuning | ×2 | 2012.48 | 20.1 | 0.50 | 81.6 | 24 | 9273.46 | 1.19 | -22378.44 | -8778.35 | 107.9 | 0.80 | 76.9 |
| tuning | ×3 | 1346.55 | 13.5 | 0.47 | 82.1 | 24 | 7944.67 | 1.17 | -23024.71 | -9396.52 | 107.4 | 0.80 | 76.9 |
| validation | ×1 | 35387.36 | 353.9 | 1.65 | 39.2 | 28 | 25146.35 | 2.39 | 6123.35 | 3247.22 | 321.4 | 1.71 | 34.0 |
| validation | ×2 | 32479.93 | 324.8 | 1.59 | 39.6 | 28 | 22684.68 | 2.27 | 4837.74 | 436.60 | 320.4 | 1.70 | 34.0 |
| validation | ×3 | 29758.78 | 297.6 | 1.53 | 40.0 | 28 | 20387.85 | 2.16 | 3645.57 | -2187.96 | 319.5 | 1.70 | 34.0 |
| final_test | ×1 | -4258.78 | -42.6 | -0.24 | 61.0 | 25 | -2705.04 | 0.68 | -5507.90 | -1765.88 | -24.9 | -0.04 | 60.0 |
| final_test | ×2 | -4590.03 | -45.9 | -0.30 | 62.8 | 25 | -3020.28 | 0.64 | -5695.11 | -2079.88 | -25.1 | -0.04 | 60.0 |
| final_test | ×3 | -4902.15 | -49.0 | -0.36 | 64.5 | 25 | -3317.25 | 0.61 | -5868.65 | -2374.80 | -25.3 | -0.04 | 60.0 |

## Informačně: B&H jednotlivých aktiv (×1)

| období | BTC výnos % | BTC Sharpe | BTC DD % | ETH výnos % | ETH Sharpe | ETH DD % |
|---|---|---|---|---|---|---|
| tuning | 41.7 | 0.57 | 76.6 | 175.1 | 0.93 | 79.3 |
| validation | 464.4 | 2.02 | 26.2 | 178.4 | 1.18 | 45.3 |
| final_test | -17.3 | -0.03 | 53.0 | -32.6 | 0.03 | 67.6 |

## Informační prahy (validace ×1, NEJSOU kritériem, nic se nevybírá)

| práh | čistý P/L | Sharpe | max DD % | epizody | P/L epizod | PF |
|---|---|---|---|---|---|---|
| z1.5 | 35764.26 | 1.65 | 39.7 | 38 | 29198.31 | 2.13 |
| z2.5 | 33236.15 | 1.65 | 41.3 | 17 | 14498.45 | 2.16 |

Pozn.: `trades.csv` obsahuje i úseky N (koš 50/50); součet net_pnl všech řádků bloku = čistý P/L bloku.
Obchody/PF/bez top 3 se počítají jen z epizod E/B; epizoda nese náklady obou svých přechodů.

Výhradně PAPER výzkum. Ani kladný verdikt neznamená ziskovou strategii — jen kandidáta na forward PAPER.
