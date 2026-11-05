# Denní volatilitní průraz (open + k × včerejší rozpětí), BTC/ETH — předem registrovaný protokol (2026-11-05)

Výhradně PAPER výzkum. Zapsáno a commitnuto **před** prvním výsledkem (zatím neexistuje kód ani výsledek).
Po prvním spuštění se pravidla, dělení ani kritéria nemění; každá změna = nová hypotéza s novým protokolem.

Odlišnost od dřívějších hypotéz: Donchian (PR #11) = průraz N-denního extrému, držení týdny;
`volatility_compression` (inventář #99) = podmínka nízké volatility před průrazem; `candle` (#51) =
svíčkové vzory s retestem. Zde **vnitrodenní** momentum: průraz otevírací ceny o část včerejšího
rozpětí, výstup vždy na close téhož dne (žádné držení přes noc) ⇒ mnoho obchodů (kritérium ≥ 30 je
reálně splnitelné, na rozdíl od PR #14), expozice jen několik hodin.

## Data
- Binance Vision, spot, denní svíčky (`data/spot/monthly/klines/<SYM>/1d/`), veřejná, bez klíčů.
- BTCUSDT, ETHUSDT, 2020-01 … 2026-10. SHA-256 každého archivu do `data_source.json`.

## Pravidla (long-only, bez páky, JEDINÁ varianta k = 0,5 — žádná mřížka, nic se neladí)
- R(t−1) = high(t−1) − low(t−1); spouštěcí cena T(t) = open(t) + 0,5 × R(t−1).
- Pokud high(t) ≥ T(t): nákup za max(open(t), T(t)) × (1 + skluz); prodej za close(t) × (1 − skluz).
- Jinak žádný obchod. Max. 1 obchod na aktivum a den. Pořadí uvnitř dne z denních dat neznámé —
  konzervativní předpoklad: plnění vždy na spouštěcí ceně + skluz (žádné zlepšení).
- Koš = 2 nezávislé sleeves (BTC, ETH) po 50 % kapitálu, celá sleeve do obchodu, výnos se reinvestuje.
- Poplatek z nominálu na každé straně.

## Náklady
- Poplatek 0,095 % + skluz 0,02 % na stranu; citlivost ×1, ×2, ×3 (obojí násobeno).

## Dělení (chronologicky)
- Ladění (zde jen kontrola, nic se nevybírá): 2020-09-01 … 2022-12-31
- Validace: 2023-01-01 … 2024-12-31
- Závěrečný test: 2025-01-01 … 2026-10-31 — **spustí se jednou**, výsledek se nepoužije k žádné úpravě.

## Měřítko
Buy & hold téhož koše (2 × 50 %, nákup za open prvního dne období, stejné náklady na vstup i výstup).

## Kritéria (předem dané, beze změny proti PR #11–#14)
Kandidát na forward PAPER jen pokud platí **všechno**:
1. Validace, koš, náklady ×1: Sharpe > Sharpe B&H **a** max. drawdown < max. drawdown B&H.
2. Validace: ≥ 30 obchodů v koši.
3. Validace, náklady ×2: profit factor > 1,2 a čistý zisk > 0.
4. Validace, náklady ×1: čistý zisk > 0 i bez 3 nejlepších obchodů.
5. Závěrečný test, náklady ×2: čistý zisk > 0 **a** Sharpe > Sharpe B&H **a** max. drawdown < max. drawdown B&H.

Jinak verdikt **zamítnuto**. I „kandidát“ znamená jen kandidát na forward PAPER, ne zisková strategie.

## Doplňková informace (NENÍ kritérium, nic se podle ní nevybírá)
- k ∈ {0,3; 0,7} a k = 0,5 jen při close(t−1) > SMA200 — jen validace ×1, v `trades.csv` označeno `variant`.
- Podíl dní s obchodem, průměrný čistý výnos na obchod v bps.

## Výstupy
`trades.csv` (každý obchod), `results.json`, `RESULTS.md`, `data_source.json`; řádek v
`automation/STRATEGY_REGISTRY.md`; draft PR do `research/autopilot`.
