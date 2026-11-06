# Pásmový rebalance BTC/ETH 50/50 ±5 p. b. — výsledky (protokol `PROTOCOL.md`)

**Verdikt: ZAMÍTNUTO** — jediná předem daná varianta (pásmo ±5 p. b., rebalance za open dalšího dne).

| kritérium | splněno |
|---|---|
| 1_validation_sharpe_and_dd_beat_bh_x1 | NE |
| 2_validation_trades_ge_30 | NE |
| 3_validation_x2_pf_gt_1_2_and_net_gt_0 | ano |
| 4_validation_x1_net_without_top3_gt_0 | ano |
| 5_final_x2_net_gt_0_sharpe_and_dd_beat_bh | NE |

## Strategie vs. buy & hold koše BTC/ETH 50/50 (bez rebalance)

| období | náklady | čistý P/L | výnos % | Sharpe | max DD % | obchody | rebal. | PF | bez top 3 | rozdíl vs B&H | B&H výnos % | B&H Sharpe | B&H max DD % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tuning | ×1 | 11666.04 | 116.7 | 0.82 | 76.4 | 32 | 15 | 1.11 | -31248.18 | 827.33 | 108.4 | 0.80 | 76.9 |
| tuning | ×2 | 11574.75 | 115.7 | 0.82 | 76.4 | 32 | 15 | 1.11 | -31235.14 | 783.91 | 107.9 | 0.80 | 76.9 |
| tuning | ×3 | 11483.84 | 114.8 | 0.81 | 76.4 | 32 | 15 | 1.11 | -31221.97 | 740.77 | 107.4 | 0.80 | 76.9 |
| validation | ×1 | 30318.03 | 303.2 | 1.64 | 35.5 | 8 | 3 | 8.88 | 6739.33 | -1822.11 | 321.4 | 1.71 | 34.0 |
| validation | ×2 | 30210.85 | 302.1 | 1.64 | 35.5 | 8 | 3 | 8.86 | 6691.78 | -1832.48 | 320.4 | 1.70 | 34.0 |
| validation | ×3 | 30103.96 | 301.0 | 1.64 | 35.5 | 8 | 3 | 8.83 | 6644.37 | -1842.78 | 319.5 | 1.70 | 34.0 |
| final_test | ×1 | -2201.65 | -22.0 | 0.01 | 60.0 | 16 | 7 | 0.78 | -7861.50 | 291.25 | -24.9 | -0.04 | 60.0 |
| final_test | ×2 | -2226.50 | -22.3 | 0.01 | 60.0 | 16 | 7 | 0.77 | -7874.66 | 283.65 | -25.1 | -0.04 | 60.0 |
| final_test | ×3 | -2251.27 | -22.5 | 0.01 | 60.0 | 16 | 7 | 0.77 | -7887.76 | 276.09 | -25.3 | -0.04 | 60.0 |

## Informačně: B&H jednotlivých aktiv (×1)

| období | BTC výnos % | BTC Sharpe | BTC DD % | ETH výnos % | ETH Sharpe | ETH DD % |
|---|---|---|---|---|---|---|
| tuning | 41.7 | 0.57 | 76.6 | 175.1 | 0.93 | 79.3 |
| validation | 464.4 | 2.02 | 26.2 | 178.4 | 1.18 | 45.3 |
| final_test | -17.3 | -0.03 | 53.0 | -32.6 | 0.03 | 67.6 |

## Informační varianty (validace ×1, NEJSOU kritériem, nic se nevybírá)

| varianta | čistý P/L | Sharpe | max DD % | obchody | rebal. | PF |
|---|---|---|---|---|---|---|
| band10 | 30938.24 | 1.66 | 35.0 | 4 | 1 | inf |
| monthly | 30285.27 | 1.64 | 35.6 | 48 | 23 | 2.43 |

Pozn.: „obchod“ = úsek držení jedné sleeve; při kladném trhu jsou úseky většinou ziskové bez ohledu na hranu,
proto rozhoduje hlavně srovnání s B&H (krit. 1 a 5) a sloupec „rozdíl vs B&H“.

Výhradně PAPER výzkum. Ani kladný verdikt neznamená ziskovou strategii — jen kandidáta na forward PAPER.
