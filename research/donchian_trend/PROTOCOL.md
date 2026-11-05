# Donchian trend 20/55 — předem registrovaný protokol (2026-11-05)

Výhradně PAPER výzkum. Zapsáno a commitnuto **před** prvním výsledkem. Po prvním spuštění se pravidla,
mřížka, dělení ani kritéria nemění; každá změna = nová hypotéza s novým protokolem.

Odlišnost od dřívějších 110 hypotéz (`reports/hypothesis-inventory-20261105.md`): žádná netestovala
klasický časově-řadový breakout kanálu (Donchian/Turtle) na denních svíčkách. Nejbližší
`volatility_managed_momentum` je průřezová rotace podle 90denního momenta, ne breakout jednotlivého aktiva.

## Data
- Binance Vision, spot, denní svíčky (`data/spot/monthly/klines/<SYM>/1d/`), veřejná, bez klíčů.
- BTCUSDT, ETHUSDT, XRPUSDT od 2020-01, SOLUSDT od 2020-08 (první měsíc s daty) do 2026-10 včetně.
- SHA-256 každého archivu do `data_source.json`. Časová razítka v µs (od 2025) se převádějí na ms.

## Pravidla (long-only, žádná páka)
- Signál vstupu na zavření dne t: `close_t > max(high_{t-N} … high_{t-1})`.
- Vstup: open dne t+1 × (1 + skluz). Poplatek z nominálu na každé straně.
- Počáteční stop: `vstupní cena − k × ATR20(t)` (Wilder, ATR ke dni signálu), během obchodu se nemění.
- Výstup kanálem: `close_t < min(low_{t-M} … low_{t-1})`, M = N/2 ⇒ prodej na open t+1 × (1 − skluz).
- Stop: když `low ≤ stop`, prodej za `min(open, stop) × (1 − skluz)` (gap pod stop = za open).
- Pokud v jeden den platí stop i signál kanálu, platí stop. Na konci období se pozice zavře za close.
- Max. 1 pozice na aktivum. Koš = 4 nezávislé „sleeves“ po 25 % kapitálu, výnos se reinvestuje v rámci sleeve.

## Náklady
- Poplatek 0,095 % + skluz 0,02 % na stranu (stejně jako dřívější výzkum v repozitáři).
- Citlivost: ×1, ×2, ×3 (obojí násobeno).

## Mřížka (jen na ladicím období)
- N ∈ {20, 55}, k ∈ {2, 3} ⇒ 4 varianty. Vybírá se **jedna** podle Sharpe koše (denní výnosy, ×√365)
  na ladicím období při nákladech ×1. Nic jiného se neladí.

## Dělení (chronologicky)
- Ladění: 2020-09-01 … 2022-12-31
- Validace: 2023-01-01 … 2024-12-31
- Závěrečný test: 2025-01-01 … 2026-10-31 — **spustí se jednou**, výsledek se nepoužije k žádné úpravě.
- Každé období začíná bez pozice; indikátory se počítají z celé historie (bez pohledu dopředu).

## Měřítko
Buy & hold téhož koše (4 × 25 %, nákup za open prvního dne období, stejné náklady na vstup i výstup)
a jednotlivých aktiv.

## Kritéria (předem dané)
Kandidát na forward PAPER jen pokud platí **všechno**:
1. Validace, koš, náklady ×1: Sharpe > Sharpe B&H **a** max. drawdown < max. drawdown B&H.
2. Validace: ≥ 30 obchodů v koši.
3. Validace, náklady ×2: profit factor > 1,2 a čistý zisk > 0.
4. Validace, náklady ×1: čistý zisk > 0 i bez 3 nejlepších obchodů.
5. Závěrečný test, náklady ×2: čistý zisk > 0 **a** Sharpe > Sharpe B&H **a** max. drawdown < max. drawdown B&H.

Jinak verdikt **zamítnuto**. I „kandidát“ znamená jen kandidát na forward PAPER, ne zisková strategie.

## Výstupy
`trades.csv` (každý obchod všech variant, období a nákladů), `results.json`, `RESULTS.md`,
`data_source.json`; řádek v `automation/STRATEGY_REGISTRY.md`.
