# Výzkumný rámec v2 (platí od 2026-11-06 09:40 SEČ)

Vlastník (2026-11-06): „Úprav to podle sebe.“ Důvody změny: v2 opravuje tři slabiny v1, které se
ukázaly po 11 zamítnutých hypotézách. (1) Jediné měřítko „porazit buy & hold“ ve validaci 2023–24
(B&H +321 %) zamítá i strategie, které propad zhruba půlí. (2) Validační i závěrečné období sdílí všech
11 hypotéz, takže holdout už je opotřebovaný. (3) Hypotézy byly skoro samá učebnicová denní TA na BTC/ETH.

Výhradně PAPER. Nic z tohoto rámce nemění produkci; výsledky jsou jen podklad pro rozhodnutí vlastníka.

## 1. Dvě stopy hodnocení (obě se počítají a zapisují u každé hypotézy)

**Stopa A — porazit trh** (původní kritéria v1, beze změny): validace Sharpe i max DD lepší než B&H
při ×1, ≥ 30 obchodů, PF > 1,2 a zisk > 0 při ×2, zisk bez 3 nejlepších obchodů > 0, závěrečný test ×2
zisk > 0 a Sharpe i DD lepší než B&H.

**Stopa B — řízené riziko** (nová): strategie po nákladech vydělává s výrazně menším propadem než trh.
Všechno musí platit:
1. Validace, náklady ×2: čistý zisk > 0 a PF > 1,2.
2. Validace i závěrečný test: max DD ≤ 0,6 × max DD B&H téhož období.
3. Závěrečný test, náklady ×2: čistý zisk > 0.
4. Validace, ×1: zisk bez 3 nejlepších obchodů > 0.
5. Validace + závěrečný test dohromady ≥ 20 obchodů.
6. Ladicí období, ×1: čistý zisk > 0 (strategie nesmí fungovat jen v jednom režimu trhu).

## 2. Ochrana proti náhodným úspěchům (vícenásobné testování)
- `automation/STRATEGY_REGISTRY.md` vede u každé hypotézy počet otestovaných variant (velikost mřížky);
  průběžný součet = N.
- U každého „prošlo“ (A nebo B) spočítat **Deflated Sharpe Ratio** (Bailey & López de Prado 2014)
  pro validaci s N; požadavek DSR ≥ 0,95. Implementace jednou v `tools/research/deflated_sharpe.py` + test.
- Robustnost: sousední parametry (±1 krok mřížky) musí dát stejné znaménko zisku ve validaci ×2;
  walk-forward na 4 po sobě jdoucích ročních oknech 2021–2024 — kladný zisk ×2 ve ≥ 3 z 4.

## 3. Opotřebovaný holdout ⇒ forward PAPER je jediná cesta k „kandidátovi“
- Období 2025-01 … 2026-10 už viděla řada hypotéz; od teď je to jen „druhá validace“.
- Co projde A nebo B + bod 2 → **forward PAPER ve výzkumu**: každý běh doplní nové denní svíčky
  (Binance Vision daily klines, přes GitHub Actions) a zaúčtuje obchody do
  `research/forward/<název>/trades.csv` + `equity.csv`. Žádný zásah do produkčních botů.
- Až po ≥ 60 dnech forward PAPER a zisku po nákladech ×2 se strategie smí předložit vlastníkovi jako
  „kandidát na produkční PAPER bota“. Ani pak ne „zisková strategie“.
- Přehodnocení starých výsledků novou stopou B je post-hoc ⇒ případný úspěch se značí **(post-hoc)**
  a může jít jen do forward PAPER, nikdy rovnou dál.

## 4. Tempo: hloubka před počtem
- Max. **3 nové hypotézy denně**. Ostatní běhy: robustnost (bod 2) kandidátů, forward PAPER, audit
  produkčních botů, údržba nástrojů.
- Jedna hypotéza smí trvat i několik běhů; mezistav vždy commitnout se zápisem „kde pokračovat“.

## 5. Kde hledat (pořadí fronty ve STATE.md)
Přednost mají zdroje výhody, které v1 netestovala: delta-neutrální carry (funding/basis), průřezové
strategie na širším koši aktiv, řízení velikosti pozice (volatilitní cílení), a vyhodnocení skutečných
produkčních PAPER botů. Další denní TA na samotném BTC/ETH jen s jasným zdůvodněním odlišnosti.
