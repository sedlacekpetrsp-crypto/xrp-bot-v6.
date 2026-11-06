# Přepínání XRP ↔ BTC podle trendu XRPBTC — předem registrovaný protokol (2026-11-06)

Výhradně PAPER výzkum. Zapsáno a commitnuto **před** prvním kódem i výsledkem.
Po prvním spuštění se pravidla, dělení ani kritéria nemění; každá změna = nová hypotéza s novým protokolem.

Odlišnost od dřívějších: `research/relative_strength` (inventář #85) = XRP vs BTC+ETH, 7denní poměr, 1h data,
obchod jen XRP s hotovostí. PR #17 = stejná pravidla na páru ETHBTC (zamítnuto). Zde **jiné aktivum (XRP)**,
vždy plně investováno v XRP nebo BTC. Pravidla jsou převzata z PR #17 beze změny (SMA50) — předem daná,
**ne** laděná podle výsledku PR #17. Vyhodnocení stejnými kritérii.

## Data
- Binance Vision spot 1d klines BTCUSDT, XRPUSDT, XRPBTC 2020-01 … 2026-10, SHA-256 archivů do `data_source.json`.
- Chybějící den v kterékoli řadě ⇒ běh skončí chybou (žádné doplňování).

## Pravidla (long-only, bez páky, JEDINÁ varianta)
- Signál k close dne t: XRPBTC close(t) > SMA50(XRPBTC)(t) ⇒ cíl XRP, jinak BTC.
- Při změně cíle: za open(t+1) prodat celé držené aktivum (open × (1 − skluz) − poplatek) a za výnos koupit druhé
  (open × (1 + skluz) + poplatek). První den období nákup cílového aktiva za open (signál z close předchozího dne).
- 100 % kapitálu (10 000 USDT); konec období = prodej za close (skluz + poplatek).
- „Obchod“ = jedno držení aktiva od nákupu do prodeje (net_pnl po nákladech obou stran).

## Náklady
- Poplatek 0,095 % + skluz 0,02 % na stranu, citlivost ×1, ×2, ×3.

## Dělení (chronologicky)
- Ladění (jen kontrola): 2020-09-01 … 2022-12-31; validace: 2023-01-01 … 2024-12-31;
  závěrečný test: 2025-01-01 … 2026-10-31 — **spustí se jednou**, nic se podle něj neupravuje.

## Měřítko
Buy & hold koše XRP/BTC 50/50 (nákup za open prvního dne období, bez rebalance, stejné náklady).
Informačně i B&H samotného XRP a samotného BTC.

## Kritéria (beze změny proti PR #11–#18)
1. Validace ×1: Sharpe > Sharpe B&H 50/50 **a** max DD < max DD B&H 50/50.
2. Validace: ≥ 30 obchodů.
3. Validace ×2: PF > 1,2 a čistý zisk > 0.
4. Validace ×1: čistý zisk > 0 i bez 3 nejlepších obchodů.
5. Závěrečný test ×2: čistý zisk > 0 **a** Sharpe > B&H 50/50 **a** max DD < B&H 50/50.
Jinak **zamítnuto**. „Kandidát“ = jen kandidát na forward PAPER.

## Doplňková informace (není kritérium, nic se nevybírá)
- SMA20 a SMA100 místo SMA50 — jen validace ×1, `variant` v `trades.csv`.

## Výstupy
`trades.csv`, `results.json`, `RESULTS.md`, `data_source.json`; řádek v `automation/STRATEGY_REGISTRY.md`; draft PR do `research/autopilot`.
