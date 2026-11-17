# Blízkost 52týdennímu maximu, průřezově 8 aktiv (George–Hwang) — předem registrovaný protokol (2026-11-06)

Výhradně PAPER výzkum. Zapsáno a commitnuto **před** prvním kódem i výsledkem (fronta R5, rámec v2).
Po prvním spuštění se pravidla, dělení ani kritéria nemění; každá změna = nová hypotéza s novým protokolem.
Backtest se spustí nejdřív 2026-11-07 UTC (denní limit 3 nových hypotéz).

Odlišnost: `cross_sectional_rotation` (inventář #56) a `relative_strength` (#85) řadily aktiva podle výnosu/momenta.
Zde se řadí podle **vzdálenosti close od 365denního maxima close** (anchoring: aktiva blízko ročního maxima
investoři podreagovávají). Žádné časování trhu (vždy 100 % investováno), žádný trend poměru, žádný rebalance pásmem.

## Data
- Binance Vision spot 1d klines BTCUSDT, ETHUSDT, BNBUSDT, XRPUSDT, ADAUSDT, DOGEUSDT, LTCUSDT, LINKUSDT,
  2019-08 … 2026-10 (365 dní historie před 2020-09-01), SHA-256 archivů do `data_source.json`.
- Chybějící den u kteréhokoli aktiva v simulovaném období ⇒ běh skončí chybou (žádné doplňování).

## Pravidla (JEDINÁ hlavní varianta, K = 3)
- Skóre(i, t) = close(i, t) / max(close(i, t−364 … t)) ∈ (0, 1].
- Rebalance měsíčně: signál k close posledního dne měsíce t, obchod za **open prvního dne dalšího měsíce**.
- Drží se K = 3 aktiva s nejvyšším skóre (shoda ⇒ pořadí podle seznamu výše), stejné váhy 1/K: na každém rebalance
  se celé portfolio (hodnota za open) přerozdělí na přesně 1/K na aktivum (prodej vystupujících, nákup vstupujících,
  dorovnání ponechaných); náklady z obratu.
- Start období: nákup podle signálu k close dne před startem za open prvního dne; konec = prodej všeho za close posledního dne.
- Bez hotovosti, bez páky, bez shortů.
- „Obchod“ = slot aktiva v jednom měsíci (K obchodů za měsíc). start_value = hodnota pozice po rebalance + 1/K nákladů
  daného rebalance; end_value = hodnota pozice za open příštího rebalance (resp. po likvidaci na konci období, kde
  nese i náklady likvidace). Součet net_pnl bloku = čistý P/L bloku (souvislý ledger).

## Náklady
- Poplatek 0,095 % + skluz 0,02 % na stranu (z obratu), citlivost ×1, ×2, ×3.

## Dělení (chronologicky)
- Ladění (jen kontrola): 2020-09-01 … 2022-12-31; validace: 2023-01-01 … 2024-12-31;
  závěrečný test: 2025-01-01 … 2026-10-31 — **spustí se jednou**, nic se podle něj neupravuje
  (podle rámce v2 je toto období už opotřebované = „druhá validace“).

## Měřítko
Buy & hold rovnovážného koše týchž 8 aktiv (1/8 každé za open prvního dne, bez rebalance, stejné náklady).
Informačně: měsíčně rebalancovaný rovnovážný koš 8 aktiv (oddělí efekt výběru od efektu rebalance) a B&H BTC.

## Kritéria — stopa A (A1–A5) a stopa B (B1–B6) přesně podle `automation/RESEARCH_FRAMEWORK.md`
A1 validace ×1 Sharpe i max DD lepší než B&H koše; A2 validace ≥ 30 obchodů; A3 validace ×2 PF > 1,2 a zisk > 0;
A4 validace ×1 zisk bez 3 nejlepších obchodů > 0; A5 závěrečný ×2 zisk > 0, Sharpe i DD lepší než B&H.
B1 validace ×2 zisk > 0 a PF > 1,2; B2 max DD ×1 ≤ 0,6 × B&H ve validaci i závěrečném; B3 závěrečný ×2 zisk > 0;
B4 validace ×1 bez top 3 > 0; B5 validace + závěrečný ≥ 20 obchodů; B6 ladění ×1 zisk > 0.
Robustnost (nutná pro „kandidáta“): DSR validace ×1 (denní výnosy) ≥ 0,95 s N = 151 (průběžně 148 + 3 varianty K),
rozptyl Sharpe pokusů 0,5 ročně; sousedé K = 2 a K = 4 — validace ×2 zisk > 0 u obou; walk-forward 2021, 2022, 2023,
2024 (každý rok samostatně, ×2) — zisk > 0 ve ≥ 3 ze 4 let.
Jinak **zamítnuto**. „Kandidát“ = jen kandidát na forward PAPER, nikdy „zisková strategie“.

## Doplňková informace (není kritérium, nic se nevybírá)
- Placebo: 3 aktiva s **nejnižším** skóre (validace ×1) — rozpětí top-3 vs bottom-3 ukazuje, zda pořadí nese informaci.

## Výstupy
`trades.csv`, `results.json`, `RESULTS.md`, `data_source.json`; řádek v `automation/STRATEGY_REGISTRY.md`;
draft PR do `research/autopilot`. Nezávislý přepočet souhrnů z `trades.csv` (počet a součet net_pnl na blok).
