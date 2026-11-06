# Mean-reversion poměru ETHBTC (long-only, koš BTC/ETH) — předem registrovaný protokol (2026-11-06)

Výhradně PAPER výzkum. Zapsáno a commitnuto **před** prvním kódem i výsledkem.
Po prvním spuštění se pravidla, dělení ani kritéria nemění; každá změna = nová hypotéza s novým protokolem.

Odlišnost: PR #17 (ETHBTC trend SMA50) sázel na pokračování trendu poměru — zde opačná sázka (návrat k průměru)
a výchozí stav je koš 50/50. `research/sol_eth_pairs` (inventář #91) = jiný pár (SOL/ETH) a long/short spread;
zde jen long spot, žádná páka ani short. PR #18 (pásmový rebalance) reagoval na odchylku vah, ne na z-skóre poměru.

## Data
- Binance Vision spot 1d klines BTCUSDT, ETHUSDT, ETHBTC 2020-01 … 2026-10, SHA-256 archivů do `data_source.json`.
- Chybějící den v kterékoli řadě ⇒ běh skončí chybou (žádné doplňování).

## Pravidla (long-only, bez páky, JEDINÁ varianta)
- z(t) = (close ETHBTC(t) − SMA20(t)) / směr. odchylka 20 close (populační, okno včetně t).
- Stavy: N = koš 50/50 BTC/ETH (hodnotově), E = 100 % ETH, B = 100 % BTC.
- Přechody podle z(t) k close dne t, provedení za open(t+1):
  N → E při z < −2; N → B při z > +2; E → N při z > 0; B → N při z < 0. Přímý přechod E ↔ B není (nejdřív N).
- Start období: nákup koše 50/50 za open prvního dne (stav N, i když z je mimo pásmo — signál až od dalšího close).
- Přechod = prodej/nákup jen potřebných částí (open × (1 ∓ skluz), poplatek z obratu). Konec období = prodej všeho za close.
- „Obchod“ = epizoda E nebo B (od vstupu do návratu do N nebo konce období); net_pnl = změna hodnoty portfolia
  během epizody včetně nákladů obou přechodů. Úseky N se zapisují do `trades.csv` jako `segment=N` (ne obchod),
  aby součet všech řádků = celkový P/L.

## Náklady
- Poplatek 0,095 % + skluz 0,02 % na stranu, citlivost ×1, ×2, ×3.

## Dělení (chronologicky)
- Ladění (jen kontrola): 2020-09-01 … 2022-12-31; validace: 2023-01-01 … 2024-12-31;
  závěrečný test: 2025-01-01 … 2026-10-31 — **spustí se jednou**, nic se podle něj neupravuje.

## Měřítko
Buy & hold koše BTC/ETH 50/50 bez rebalance (nákup za open prvního dne, stejné náklady). Informačně B&H BTC a ETH.

## Kritéria (beze změny proti PR #11–#19)
1. Validace ×1: Sharpe > Sharpe B&H 50/50 **a** max DD < max DD B&H 50/50.
2. Validace: ≥ 30 obchodů (epizod E/B).
3. Validace ×2: PF epizod > 1,2 a čistý zisk > 0.
4. Validace ×1: čistý zisk > 0 i bez 3 nejlepších epizod.
5. Závěrečný test ×2: čistý zisk > 0 **a** Sharpe > B&H 50/50 **a** max DD < B&H 50/50.
Jinak **zamítnuto**. „Kandidát“ = jen kandidát na forward PAPER.

## Doplňková informace (není kritérium, nic se nevybírá)
- Prah ±1,5 a ±2,5 místo ±2 — jen validace ×1, `variant` v `trades.csv`.

## Výstupy
`trades.csv`, `results.json`, `RESULTS.md`, `data_source.json`; řádek v `automation/STRATEGY_REGISTRY.md`; draft PR do `research/autopilot`.
