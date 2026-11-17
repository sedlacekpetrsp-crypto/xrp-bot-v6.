# RSI(2) pullback v uptrendu, BTC/ETH denně — předem registrovaný protokol (2026-11-05)

Výhradně PAPER výzkum. Zapsáno a commitnuto **před** prvním výsledkem. Po prvním spuštění se pravidla,
dělení ani kritéria nemění; každá změna = nová hypotéza s novým protokolem.

Odlišnost od dřívějších hypotéz (`reports/hypothesis-inventory-20261105.md` — žádný krátkodobý
oscilátorový pullback s dlouhým trendovým filtrem), od Donchian (PR #11, breakout = následování trendu)
a Turn-of-month (PR #12, kalendář): krátkodobý návrat k průměru (2denní přeprodanost) jen ve směru
dlouhodobého trendu. Hypotéza: v uptrendu jsou prudké 1–3denní poklesy přehnané a do několika dnů se vracejí.

## Data
- Binance Vision, spot, denní svíčky (`data/spot/monthly/klines/<SYM>/1d/`), veřejná, bez klíčů.
- BTCUSDT, ETHUSDT, 2020-01 … 2026-10. SHA-256 každého archivu do `data_source.json`.
- Indikátory se počítají z celé historie (zahřátí SMA200 před 2020-09), obchoduje se jen uvnitř období.

## Pravidla (long-only, bez páky, JEDINÁ varianta — žádná mřížka, nic se neladí)
- RSI(2) s Wilderovým vyhlazením z close; SMA200 a SMA5 z close.
- Signál vstupu na close dne t: close > SMA200 **a** RSI(2) < 10 a není otevřená pozice ⇒ nákup za **open t+1** × (1 + skluz).
- Signál výstupu na close dne t: close > SMA5 ⇒ prodej za **open t+1** × (1 − skluz). Žádný stop, žádný časový limit.
- Na konci období nucené uzavření za close posledního dne × (1 − skluz). Vstupní den musí ležet v období.
- Koš = 2 nezávislé sleeves (BTC, ETH) po 50 % kapitálu, celá sleeve do pozice, výnos se reinvestuje.
- Poplatek z nominálu na každé straně.

## Náklady
- Poplatek 0,095 % + skluz 0,02 % na stranu; citlivost ×1, ×2, ×3 (obojí násobeno).

## Dělení (chronologicky)
- Ladění (zde jen kontrola, nic se nevybírá): 2020-09-01 … 2022-12-31
- Validace: 2023-01-01 … 2024-12-31
- Závěrečný test: 2025-01-01 … 2026-10-31 — **spustí se jednou**, výsledek se nepoužije k žádné úpravě.

## Měřítko
Buy & hold téhož koše (2 × 50 %, nákup za open prvního dne období, stejné náklady na vstup i výstup).

## Kritéria (předem dané, stejná jako u Donchian a ToM)
Kandidát na forward PAPER jen pokud platí **všechno**:
1. Validace, koš, náklady ×1: Sharpe > Sharpe B&H **a** max. drawdown < max. drawdown B&H.
2. Validace: ≥ 30 obchodů v koši.
3. Validace, náklady ×2: profit factor > 1,2 a čistý zisk > 0.
4. Validace, náklady ×1: čistý zisk > 0 i bez 3 nejlepších obchodů.
5. Závěrečný test, náklady ×2: čistý zisk > 0 **a** Sharpe > Sharpe B&H **a** max. drawdown < max. drawdown B&H.

Jinak verdikt **zamítnuto**. I „kandidát“ znamená jen kandidát na forward PAPER, ne zisková strategie.

## Doplňková informace (NENÍ kritérium, nic se podle ní nevybírá)
- Citlivost prahu RSI ∈ {5, 15} a varianta bez filtru SMA200 — jen validace ×1, označeno `variant`.
- Expozice (% dní v pozici) a průměrná délka obchodu.

## Výstupy
`trades.csv` (každý obchod všech období a nákladů, vč. informačních variant označených `variant`),
`results.json`, `RESULTS.md`, `data_source.json`; řádek v `automation/STRATEGY_REGISTRY.md`.
