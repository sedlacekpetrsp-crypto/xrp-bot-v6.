# Kontrariánský žebřík podle propadu od 365denního maxima, 8 aktiv — předem registrovaný protokol (2026-11-06)

Výhradně PAPER výzkum. Zapsáno a commitnuto **před** prvním kódem i výsledkem (fronta R7, rámec v2).
Po prvním spuštění se pravidla, dělení ani kritéria nemění; každá změna = nová hypotéza s novým protokolem.
Backtest se spustí nejdřív 2026-11-07 UTC (denní limit 3 nových hypotéz; 2026-11-06 vyčerpán).

## Proč nové
Valuační/propadový signál (vzdálenost close pod 365denním maximem), ne trend, kalendář ani poměr dvou aktiv.
Žádná ze 110 hypotéz v `reports/hypothesis-inventory-20261105.md` ani z registru nekupovala po prahových propadech
od ročního maxima. Blízká je jen R5 (near-high), která ale řadí aktiva průřezově a je vždy 100 % investovaná;
tady jde o časové dávkování hotovosti v rámci každého aktiva zvlášť.

**Změna oproti náčrtu ve STATE.md bod 13 (jen BTC), rozhodnuto před daty:** BTC samotné má za 2020–2026 jen několik
cyklů s propadem ≥ 20 %, takže by kritéria A2 (≥ 30 obchodů ve validaci) a B5 (≥ 20) nesplnilo z konstrukce.
Hlavní varianta je proto koš 8 nezávislých „rukávů“ (stejný vesmír jako R5); BTC samotné jen informačně.

## Data
- Binance Vision spot 1d klines BTCUSDT, ETHUSDT, BNBUSDT, XRPUSDT, ADAUSDT, DOGEUSDT, LTCUSDT, LINKUSDT,
  2019-08 … 2026-10 (365 dní historie před 2020-09-01), SHA-256 archivů do `data_source.json`.
- Chybějící den u kteréhokoli aktiva v simulovaném období ⇒ běh skončí chybou (žádné doplňování).

## Pravidla (JEDINÁ hlavní varianta, prahy L = 20 / 30 / 40 %)
Kapitál 10 000 USDT se na začátku bloku rozdělí rovným dílem do 8 rukávů (1 250). Každý rukáv = dva podúčty:
- **Základ**: 50 % rukávu koupí aktivum za open prvního dne bloku a drží ho do konce bloku (bez rebalance).
- **Žebřík**: 50 % rukávu v hotovosti (bez úroku). DD(t) = 1 − close(t) / max(close(t−364 … t)).
  - Stav n ∈ {0, 1, 2, 3} = počet koupených tranší v aktuálním cyklu. Při n = 0 se při první tranši zafixuje
    rezerva R = hotovost žebříku; každá tranše = R/3 (třetí tranše = veškerá zbylá hotovost žebříku).
  - Signál k close dne t: koupit všechny dosud nekoupené tranše j (j ≥ n) s DD(t) ≥ L[j]; obchod za **open t+1**.
  - Reset: pokud n > 0 a close(t) ≥ max(close(t−364 … t)) (nové 365denní maximum), prodat **všechny** tranše
    žebříku za open t+1, n = 0 (hotovost včetně zisku/ztráty zůstává v žebříku pro další cyklus).
  - Signál nákupu a resetu ve stejný den nemůže nastat (DD = 0 < 20 %).
- Na začátku každého bloku je stav n = 0 (blok začíná čistý); max365 se počítá i z dat před začátkem bloku,
  takže na prvním dni bloku se může nakoupit hned (podle signálu k close dne před startem).
- Konec bloku: prodej všeho (základ i otevřené tranše) za close posledního dne.
- Bez páky, bez shortů, rukávy se mezi sebou nepřerozdělují.

## Obchody a ledger
- „Obchod“ = tranše (nákup → reset nebo konec bloku). Řádky typu `BASE` = základní pozice rukávu (1 za blok),
  řádky typu `TRANCHE` = tranše. Součet net_pnl všech řádků bloku = čistý P/L bloku (souvislý ledger).
- Počty obchodů (A2, B5), PF (A3, B1) a „bez 3 nejlepších“ se počítají jen z `TRANCHE` řádků; „bez top 3“ =
  celkový čistý P/L bloku minus 3 nejlepší tranše. Výnos, Sharpe (denní, ×√365) a max DD z denní křivky celého koše.

## Náklady
Poplatek 0,095 % + skluz 0,02 % na stranu, citlivost ×1, ×2, ×3.

## Dělení (chronologicky)
Ladění (jen kontrola): 2020-09-01 … 2022-12-31; validace: 2023-01-01 … 2024-12-31; závěrečný test:
2025-01-01 … 2026-10-31 — **spustí se jednou**, nic se podle něj neupravuje (podle rámce v2 už opotřebované = „druhá validace“).

## Měřítko
Buy & hold rovnovážného koše týchž 8 aktiv (1/8 každé za open prvního dne, bez rebalance, stejné náklady) —
podle rámce. Informačně (není kritérium): statický koš 50 % aktiva / 50 % hotovost v každém rukávu (= jen základ,
ukáže přínos samotného žebříku), BTC rukáv samostatně a B&H BTC.

## Kritéria — stopa A (A1–A5) a stopa B (B1–B6) přesně podle `automation/RESEARCH_FRAMEWORK.md`
A1 validace ×1 Sharpe i max DD lepší než B&H koše; A2 validace ≥ 30 tranší; A3 validace ×2 PF tranší > 1,2 a zisk > 0;
A4 validace ×1 zisk bez 3 nejlepších tranší > 0; A5 závěrečný ×2 zisk > 0, Sharpe i DD lepší než B&H.
B1 validace ×2 zisk > 0 a PF tranší > 1,2; B2 max DD ×1 ≤ 0,6 × B&H ve validaci i závěrečném; B3 závěrečný ×2 zisk > 0;
B4 validace ×1 bez top 3 > 0; B5 validace + závěrečný ≥ 20 tranší; B6 ladění ×1 zisk > 0.
Robustnost (nutná pro „kandidáta“): DSR validace ×1 (denní výnosy) ≥ 0,95 s N = 162 (pracovní odhad 159 + 3 varianty),
rozptyl Sharpe pokusů 0,5 ročně; sousedé L = 15/25/35 a 25/35/45 — validace ×2 zisk > 0 u obou; walk-forward 2021, 2022,
2023, 2024 (každý rok samostatně, ×2) — zisk > 0 ve ≥ 3 ze 4 let.
Jinak **zamítnuto**. „Kandidát“ = jen kandidát na forward PAPER, nikdy „zisková strategie“.

## Výstupy
`trades.csv`, `results.json`, `RESULTS.md`, `data_source.json`; řádek v `automation/STRATEGY_REGISTRY.md`;
draft PR do `research/autopilot`. Nezávislý přepočet souhrnů z `trades.csv` (počet a součet net_pnl na blok).
