# Přepínání BTC ↔ ETH podle trendu ETHBTC — výsledky (protokol `PROTOCOL.md`)

**Verdikt: ZAMÍTNUTO** — jediná předem daná varianta (ETHBTC close > SMA50 ⇒ ETH, jinak BTC; vždy investováno).

| kritérium | splněno |
|---|---|
| 1_validation_sharpe_and_dd_beat_bh_x1 | NE |
| 2_validation_trades_ge_30 | ano |
| 3_validation_x2_pf_gt_1_2_and_net_gt_0 | ano |
| 4_validation_x1_net_without_top3_gt_0 | ano |
| 5_final_x2_net_gt_0_sharpe_and_dd_beat_bh | NE |

## Strategie vs. buy & hold koše BTC/ETH 50/50

| období | náklady | čistý P/L | výnos % | Sharpe | max DD % | obchody | PF | win % | bez top 3 | Ø dní | B&H výnos % | B&H Sharpe | B&H max DD % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tuning | ×1 | 11584.82 | 115.8 | 0.82 | 75.6 | 54 | 1.14 | 56 | -27855.28 | 15.8 | 108.4 | 0.80 | 76.9 |
| tuning | ×2 | 9063.78 | 90.6 | 0.76 | 77.6 | 54 | 1.11 | 56 | -28527.86 | 15.8 | 107.9 | 0.80 | 76.9 |
| tuning | ×3 | 6837.18 | 68.4 | 0.70 | 79.6 | 54 | 1.09 | 56 | -29007.74 | 15.8 | 107.4 | 0.80 | 76.9 |
| validation | ×1 | 18404.84 | 184.0 | 1.32 | 30.3 | 71 | 1.63 | 52 | 3358.76 | 10.3 | 321.4 | 1.71 | 34.0 |
| validation | ×2 | 14125.25 | 141.3 | 1.15 | 33.6 | 71 | 1.51 | 51 | 965.48 | 10.3 | 320.4 | 1.70 | 34.0 |
| validation | ×3 | 10490.44 | 104.9 | 0.98 | 36.7 | 71 | 1.40 | 51 | -1034.70 | 10.3 | 319.5 | 1.70 | 34.0 |
| final_test | ×1 | 3863.90 | 38.6 | 0.60 | 59.3 | 23 | 1.27 | 57 | -10344.16 | 29.0 | -24.9 | -0.04 | 60.0 |
| final_test | ×2 | 3149.56 | 31.5 | 0.54 | 60.7 | 23 | 1.22 | 48 | -10551.64 | 29.0 | -25.1 | -0.04 | 60.0 |
| final_test | ×3 | 2472.02 | 24.7 | 0.49 | 62.0 | 23 | 1.18 | 48 | -10765.74 | 29.0 | -25.3 | -0.04 | 60.0 |

## Informačně: B&H jednotlivých aktiv (×1)

| období | BTC výnos % | BTC Sharpe | BTC DD % | ETH výnos % | ETH Sharpe | ETH DD % |
|---|---|---|---|---|---|---|
| tuning | 41.7 | 0.57 | 76.6 | 175.1 | 0.93 | 79.3 |
| validation | 464.4 | 2.02 | 26.2 | 178.4 | 1.18 | 45.3 |
| final_test | -17.3 | -0.03 | 53.0 | -32.6 | 0.03 | 67.6 |

Podíl času v ETH (×1): tuning 52 %, validation 31 %, final_test 44 %

## Informační varianty (validace ×1, NEJSOU kritériem, nic se nevybírá)

| varianta | čistý P/L | Sharpe | max DD % | obchody | PF |
|---|---|---|---|---|---|
| SMA20 | 18553.46 | 1.31 | 30.0 | 82 | 1.56 |
| SMA100 | 23032.00 | 1.47 | 33.8 | 38 | 2.07 |

Výhradně PAPER výzkum. Ani kladný verdikt neznamená ziskovou strategii — jen kandidáta na forward PAPER.
