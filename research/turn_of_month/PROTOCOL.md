# Turn-of-month (ToM) BTC/ETH — předem registrovaný protokol (2026-11-05)

Výhradně PAPER výzkum. Zapsáno a commitnuto **před** prvním výsledkem. Po prvním spuštění se pravidla,
dělení ani kritéria nemění; každá změna = nová hypotéza s novým protokolem.

Odlišnost od dřívějších hypotéz (`reports/hypothesis-inventory-20261105.md` — žádná kalendářní/sezónní
hypotéza) i od Donchian (PR #11): signál je čistě kalendářní, nezávisí na ceně, momentu ani volatilitě.
Hypotéza: přítoky kapitálu kolem přelomu měsíce (výplaty, rebalance fondů) zvedají ceny v okně
posledních 2 a prvních 3 dnů měsíce.

## Data
- Binance Vision, spot, denní svíčky (`data/spot/monthly/klines/<SYM>/1d/`), veřejná, bez klíčů.
- BTCUSDT, ETHUSDT, 2020-01 … 2026-10. SHA-256 každého archivu do `data_source.json`.

## Pravidla (long-only, bez páky, JEDINÁ varianta — žádná mřížka, nic se neladí)
- Pro každý přelom měsíce s prvním dnem F: vstup za **open dne F − 2** (předposlední den měsíce)
  × (1 + skluz), výstup za **close dne F + 2** (3. den měsíce) × (1 − skluz). Drženo 5 kalendářních dnů.
- Jinak hotovost (0 % výnos). Obchod se bere jen, když vstupní i výstupní den leží v daném období.
- Koš = 2 nezávislé sleeves (BTC, ETH) po 50 % kapitálu, výnos se reinvestuje v rámci sleeve.
- Poplatek z nominálu na každé straně.

## Náklady
- Poplatek 0,095 % + skluz 0,02 % na stranu; citlivost ×1, ×2, ×3 (obojí násobeno).

## Dělení (chronologicky)
- Ladění (zde jen kontrola, nic se nevybírá): 2020-09-01 … 2022-12-31
- Validace: 2023-01-01 … 2024-12-31
- Závěrečný test: 2025-01-01 … 2026-10-31 — **spustí se jednou**, výsledek se nepoužije k žádné úpravě.

## Měřítko
Buy & hold téhož koše (2 × 50 %, nákup za open prvního dne období, stejné náklady na vstup i výstup).

## Kritéria (předem dané, stejná jako u Donchian)
Kandidát na forward PAPER jen pokud platí **všechno**:
1. Validace, koš, náklady ×1: Sharpe > Sharpe B&H **a** max. drawdown < max. drawdown B&H.
2. Validace: ≥ 30 obchodů v koši.
3. Validace, náklady ×2: profit factor > 1,2 a čistý zisk > 0.
4. Validace, náklady ×1: čistý zisk > 0 i bez 3 nejlepších obchodů.
5. Závěrečný test, náklady ×2: čistý zisk > 0 **a** Sharpe > Sharpe B&H **a** max. drawdown < max. drawdown B&H.

Jinak verdikt **zamítnuto**. I „kandidát“ znamená jen kandidát na forward PAPER, ne zisková strategie.

## Doplňková informace (NENÍ kritérium, nic se podle ní nevybírá)
- Placebo: totéž 5denní okno posunuté o s ∈ {−14 … +13} \ {0} dnů vůči přelomu; pro validaci ×1 se
  uvede pořadí ToM mezi 28 okny (podle čistého P/L koše). Ukazuje, zda je přelom měsíce výjimečný.
- Ladicí období ×1: čistý P/L a Sharpe (jen konzistence).

## Výstupy
`trades.csv` (každý obchod všech období a nákladů, vč. placeba označeného `variant`), `results.json`,
`RESULTS.md`, `data_source.json`; řádek v `automation/STRATEGY_REGISTRY.md`.
