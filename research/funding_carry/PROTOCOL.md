# Delta-neutrální funding carry BTC/ETH — předem registrovaný protokol (2026-11-06)

Výhradně PAPER výzkum (fronta v2, R3; rámec `automation/RESEARCH_FRAMEWORK.md`). Zapsáno a commitnuto
**před** prvním kódem i výsledkem. Po prvním spuštění se pravidla, dělení ani kritéria nemění.

Odlišnost od 110 hypotéz inventáře i PR #11–#21: žádný směrový signál ceny. Výnos = funding placený
shortům USDT-M perpetuálu, cenové riziko zajištěno spot longem (delta ≈ 0). Signál = jen úroveň fundingu.

## Data (veřejná, bez klíčů; stahuje GitHub Actions)
- Binance Vision: spot 1d klines BTCUSDT, ETHUSDT (`data/spot/monthly/klines/<S>/1d`),
  USDT-M perp 1d klines (`data/futures/um/monthly/klines/<S>/1d`),
  funding (`data/futures/um/monthly/fundingRate/<S>/<S>-fundingRate-YYYY-MM.zip`), 2020-01 … 2026-10.
- SHA-256 všech archivů do `data_source.json`. Chybějící den v klines v testovaném období ⇒ chyba.
  Chybějící měsíc fundingu ⇒ chyba (žádné doplňování).

## Pravidla (na každé aktivum zvlášť, koš 2 × 50 % kapitálu, bez míchání rukávů)
- f7(t) = průměr sazeb všech funding událostí s časem ≤ konec dne t za posledních 7 dní (t−6 … t),
  anualizace: průměr × (24 / funding_interval_hours) × 365.
- Vstup: f7(t) > H ⇒ za open(t+1): spot nákup za spot open, perp short stejného množství za perp open.
  Rukáv C: polovina na spot, polovina = marže perpu (izolovaná, 1× notional vůči marži ≈ 2× páka perpu).
- Výstup: f7(t) < 0 ⇒ za open(t+1) prodej spotu a uzavření shortu. Konec období = uzavření za close.
- Funding: short dostane rate × qty × perp close dne události (záporný rate = platí).
- Údržba marže: k close dne, je-li podíl marže M/(S+M) mimo [0,30; 0,70], vyrovnat na 50/50 za open(t+1)
  (obchod spotu i perpu o potřebné množství, s náklady). Likvidace: je-li perp high dne ≥ cena, při níž ztráta
  shortu = marže ⇒ marže = 0, epizoda končí, zapsat `liquidated=1` (konzervativní, bez náhrady).
- Mimo pozici hotovost bez úroku.

## Náklady
- Obě nohy: poplatek 0,095 % + skluz 0,02 % na stranu (konzervativně stejné pro spot i perp), ×1 / ×2 / ×3.

## Mřížka a výběr (jediný výběr, předem daný)
- H ∈ {10 %, 20 %} p.a. Výběr na ladění ×1 podle čistého zisku koše; zvolený H se použije beze změny
  ve validaci a závěrečném testu. Informačně (ne výběr): H = 5 % a 30 % (robustnost sousedů).

## Dělení
- Ladění 2020-09-01 … 2022-12-31; validace 2023-01-01 … 2024-12-31; závěrečný test 2025-01-01 … 2026-10-31
  (podle rámce v2 už jen „druhá validace“), spuštěn jednou, nic se podle něj neladí.
- Walk-forward robustnost: kalendářní roky 2021, 2022, 2023, 2024 se zvoleným H.

## Měřítko
B&H koše BTC/ETH 50/50 bez rebalance (stejné náklady). Informačně: hotovost 0 %.

## Kritéria
- Stopa A (v1): validace ×1 Sharpe > B&H a max DD < B&H; ≥ 30 obchodů; validace ×2 PF > 1,2 a zisk > 0;
  validace ×1 zisk bez 3 nejlepších > 0; závěrečný ×2 zisk > 0, Sharpe > B&H a DD < B&H.
- Stopa B (v2): B1 validace ×2 zisk > 0 a PF > 1,2; B2 max DD ≤ 0,6 × B&H ve validaci i závěrečném testu;
  B3 závěrečný ×2 zisk > 0; B4 validace ×1 bez 3 nejlepších > 0; B5 validace + závěrečný ≥ 20 obchodů;
  B6 ladění ×1 zisk > 0.
- Při „prošlo“ (A nebo B) navíc: DSR ≥ 0,95 na denních výnosech validace ×1 (`tools/research/deflated_sharpe.py`),
  N = 140 (konzervativní horní odhad všech dosud otestovaných variant), V[SR] = 0,5 p.a. (= 0,5/365 na den);
  sousedé H (5 % pro 10 %, 30 % pro 20 %) zisk ×2 ve validaci > 0; walk-forward zisk ×2 ve ≥ 3 ze 4 let.
- „Obchod“ = epizoda vstup–výstup na jednom aktivu; net_pnl včetně fundingu, údržby marže a všech nákladů.
- Prošlo ⇒ jen kandidát na forward PAPER (rámec bod 3), nikdy „zisková strategie“.

## Výstupy
`trades.csv` (každá epizoda; sloupce variant, period, cost_mult, asset, entry/exit, funding, costs, net_pnl,
liquidated), `results.json`, `RESULTS.md`, `data_source.json`; řádek v `automation/STRATEGY_REGISTRY.md`;
draft PR do `research/autopilot`.

## Dodatek 1 (2026-11-06 11:20 UTC, jen načítání dat — PŘED zobrazením jakéhokoli výsledku)
První běh (run 42208143113) skončil chybou „chybí klines BTCUSDT 2026-10-28“ (měsíční archiv neobsahuje den);
žádné metriky nebyly vypsány ani uloženy. Den chybějící v měsíčním archivu se doplní z oficiálního **denního**
archivu Binance Vision (`data/<spot|futures/um>/daily/klines/<S>/1d/<S>-1d-YYYY-MM-DD.zip`), SHA-256 do manifestu
(`filled_missing_day`). Chybí-li i denní archiv ⇒ chyba. Pravidla, dělení ani kritéria se nemění.
