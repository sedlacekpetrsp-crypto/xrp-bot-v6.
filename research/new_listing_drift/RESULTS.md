# A1 NEW-LISTING DRIFT — výsledky (PAPER výzkum, ne doporučení)

Protokol `ea4a16d`. Zvolená varianta (ladění ×1): **K60_T90**. Verdikt: **zamitnuto**.

| blok | náklady | obchody | čistý P/L | PF | Sharpe | max DD | placebo BTC short | B&H BTC % (Sharpe, DD) |
|---|---|---|---|---|---|---|---|---|
| tuning | ×1 | 141 | -930.09 (-9.30 %) | 0.6991 | -0.4063 | 20.7% | -1519.18 | 240.4092 (0.9714, 0.7667) |
| tuning | ×2 | 141 | -964.87 (-9.65 %) | 0.6895 | -0.4226 | 20.8% | -1561.07 | 240.4092 (0.9714, 0.7667) |
| tuning | ×3 | 141 | -999.67 (-10.00 %) | 0.6801 | -0.4389 | 20.9% | -1603.01 | 240.4092 (0.9714, 0.7667) |
| validation | ×1 | 226 | +719.49 (+7.19 %) | 1.2405 | 0.3994 | 16.1% | -1263.09 | 200.7344 (1.3625, 0.2626) |
| validation | ×2 | 226 | +661.39 (+6.61 %) | 1.2193 | 0.3707 | 16.5% | -1331.36 | 200.7344 (1.3625, 0.2626) |
| validation | ×3 | 226 | +603.16 (+6.03 %) | 1.1985 | 0.342 | 16.8% | -1399.70 | 200.7344 (1.3625, 0.2626) |
| final_test | ×1 | 302 | -1226.78 (-12.27 %) | 0.7826 | -0.6645 | 21.9% | +345.84 | -32.1776 (-0.4213, 0.5298) |
| final_test | ×2 | 302 | -1301.23 (-13.01 %) | 0.7707 | -0.7086 | 22.5% | +258.84 | -32.1776 (-0.4213, 0.5298) |
| final_test | ×3 | 302 | -1375.72 (-13.76 %) | 0.759 | -0.7527 | 23.1% | +171.75 | -32.1776 (-0.4213, 0.5298) |

Ladění ×1 podle varianty: K30_T90 -1025.14, K30_T180 -4356.23, K60_T90 -930.09, K60_T180 -4293.11

Kritéria: C1_val_x2_net_gt0_pf_gt1_2 ✔, C2_val_x2_gt_placebo ✔, C3_val_x1_ex_top3_gt0 ✔, C4_val_x1_sharpe_dd_vs_bh ✘, C5_final_x2_gt0_and_placebo ✘, C6_val_trades_ge30 ✔, C7_tuning_gross_edge_ge_3x_cost ✘

Robustnost: dsr_ge_0_95 ✘, neighbours_val_x2_gt0 ✔, walk_forward_ge_3_of_4 ✔
; DSR 0.012 (N = 202); WF ×2 2021 +811.08, 2022 +183.76, 2023 -567.29, 2024 +1228.69

Data: 9580 archivů, checksumy {'ok': 9580}; univerzum 671 listingů, vyřazeno pro data 0.
## Vyhodnocení (Claude, 2026-11-08) — **ZAMÍTNUTO**
- Ladění 2020–22 záporné ve všech 4 variantách (×1 −930 až −4 356 USDT); hrubá hrana zvolené K60_T90 v ladění **−7,7 %**
  na obchod (C7 vyžaduje ≥ +0,87 %) ⇒ hypotéza neprošla už na vstupní bráně.
- Validace 2023–24 kladná (×2 +661, PF 1,22, nad placebem −1 331), ale Sharpe 0,37 < B&H BTC 1,36 a DD 16,5 % vs 26,3 % ⇒ C4 ✘;
  DSR 0,012 (N = 202).
- **Závěrečný test 2025–26: ×2 −1 301 (−13,0 %)**, zatímco prosté BTC-short placebo se stejným rozvrhem +259 ⇒ listing
  nepřidává hranu nad short trhu; C5 ✘.
- Mechanismus selhání: 55–64 % obchodů vyhrává, ale **likvidace** (squeeze ≥ 2× vstupu) — 21 / 16 / 39 v blocích — berou
  celý notional; P/L validace z 47 % z 5 nejlepších obchodů. Funding kladný v ladění/validaci, záporný v závěrečném testu (−209).
- Nezávislý přepočet z trades.csv: 104 skupin, 0 neshod. Data 9 580 archivů, SHA-256 vše ok, 671 listingů, 0 vyřazeno.
- Varianta se stop-lossem / zajištěním BTC by byla nová hypotéza navržená po pohledu na data ⇒ jen přes dialog a s N + varianty.
