# Top Risk Radar V1 — G1 freeze manifest (NÁVRH, NEZAMČENO, NESPUŠTĚNO)

Stav: [N] návrh k nezávislé revizi ChatGPT (dialog 0322/0325). [S] žádný výkonnostní běh, žádné predikce na reálných datech.
Rozsah: **jediný** PAPER informační test G1 cíle Top Risk −20 % / 14 dní (XRPUSDT spot). Early Growth, G2 (P/L),
merge, deploy, Render a LIVE mimo rozsah. Zamčení = commit tohoto souboru se stavem `LOCKED` + SHA všech položek §1–§2;
před zamčením musí být splněny blokery §8.

## 1. Kód (SHA)
| Položka | SHA / soubor | Stav |
|---|---|---|
| Protokol | `PROTOCOL.md` na `research/xrp-top-risk-radar-v1-20261108` (vytvořen 2026-11-08, nezměněn) | existuje |
| Brány G1 + LOW_N dodatek | `850afc7`, `b6482ac` (`research/RADAR_G1_DECISION_GATE_DRAFT_20261112.md`) | existuje (návrh) |
| P1 skórování | `1c9123c` (PR #50, sloučen) | existuje |
| P2 features/M0 | `e2f4248` (PR #52, sloučen) | existuje |
| P3 adaptér | `36110f4` (PR #51, sloučen) | existuje |
| P3 pipeline | `8063e5e` (PR #54, NESLOUČEN; freeze se odkazuje na SHA, PR se nemění) | existuje |
| Label (1m) | `census_exact_1m.py` @ `0103335` | existuje (census) |
| B1/B2/B3 fit, moving-block bootstrap, reálný loader 1m→denní XRP+BTC, G1 runner | — | **CHYBÍ (bloker B1–B4)** |
| QA základ | 433 passed lokálně na `8063e5e` (2026-11-12, tento běh) | provedeno |

## 2. Data
- Zdroj: `data.binance.vision/data/spot/monthly/klines/{XRPUSDT,BTCUSDT}/1m/`, měsíce **2018-05..2026-10**
  (XRPUSDT na Binance od 2018-05; 2017 jen doplňkově, nepoužito). Každý ZIP ověřen proti `.CHECKSUM` (SHA-256);
  manifest = měsíc, SHA-256 ZIPu, počet svíček, první/poslední minuta, chybějící minuty.
- Manifest vytvoří **samostatný datový běh G0** (bez modelu, bez labelů vůči predikcím) a commitne ho před zamčením.
  Výkonnostní běh pak data stáhne znovu a selže (`INVALID_RUN`), pokud se kterýkoli SHA liší.
- Žádné jiné zdroje (funding/OI/on-chain = Model B, mimo G1).

## 3. Label a PIT (bez leakage)
- decision_at = denně 00:05:00 UTC. P(t) = OPEN 1m svíčky 00:05 s `trades > 0` (= první obchod do 60 s), jinak vyloučit
  `no_trade_in_first_60s`.
- Pozitivní: min 1m LOW ≤ 0,8·P(t) v minutách [00:05, 00:05+336 h). Jakákoli chybějící minuta v horizontu ⇒ vyloučit
  (`missing_minutes_in_horizon`), nikdy nedoplňovat. Odchylka od PROTOCOL ř. 7 „(t, t+336h]“: rozlišení 1 min,
  minuta 00:05 zahrnuta — zdokumentováno, ne měněno po výsledcích.
- label_available_at = min(první minuta zásahu + 1 min, decision_at + 336 h). Zralost: jen rozhodnutí ≤ cutoff − 336 h.
- Featury: denní bary z 1m s uzávěrkou 00:00 UTC, published_at = close + 60 s ≤ 00:05; okna končí před 00:00 UTC.
  Kontrola leakage: test perturbace (změna budoucích minut nesmí změnit historické featury) — existuje v P2/P3 testech,
  rozšířit na reálný loader (bloker B3).
- Epizody: **seskupené** (pozitivní rozhodnutí oddělená > 14 dní = nová epizoda), `episodes.group_positive_episodes`;
  ukotvené jen informativně.

## 4. Foldy, purge, embargo (neměnné)
Expanding train od 2018-05; testy 2022, 2023, 2024, 2025, 2026 (do posledního zralého rozhodnutí ≤ 2026-10-17).
Train řádek d jen pokud d + 336 h + 14 dní ≤ test_start (purge + embargo 14 d). Hyperparametry: vnitřní chronologická
validace = posledních 365 dní trainu se stejným purge/embargo. Testovací výsledky nikdy nevstupují do výběru.

## 5. Modely (všechny fit jen na trainu, sklearn LogisticRegression lbfgs, standardizace z trainu)
- M0: train prevalence (`baselines.fit_m0`).
- B1: logistická regrese na rv30 (realizovaná vol. 30 d, XRP). B2: ret7, ret30, drawdown od 30d maxima.
- B3 (kandidát, Model A): rv7, rv30, ret1, ret7, ret30, dd30, XRP/BTC 30d relativní síla, BTC ret7, BTC rv30.
  L2, C ∈ {0,01; 0,1; 1; 10} volené vnitřní validací (log loss).
- Reference = nejlepší z M0/B1/B2 podle vnitřní validační log loss **v každém foldu**; pevná před testem.

## 6. Metriky a rozhodnutí (návrh prahů — nebyly viděny žádné výsledky modelů)
- Primární: BSS = 1 − Brier(B3)/Brier(ref) na sloučených OOS denních řádcích.
- Nejistota: moving-block bootstrap přes souvislé kalendářní dny, bloky **14 a 28 dní**, 2000 replik, seed 20261112,
  percentilový 95% CI. IID bootstrap z `8063e5e` (`IID_DIAGNOSTIC_ONLY`) jen diagnosticky.
- Evaluovatelný fold: ≥ 3 seskupené pozitivní epizody v testu.
- **GO**: BSS ≥ 0,05 **a** dolní mez CI > 0 při obou blocích **a** BSS > 0 v ≥ 2/3 evaluovatelných foldů **a**
  kalibrační sklon OOS v [0,5; 2,0].
- **NO-GO**: BSS ≤ 0 **nebo** horní mez CI < 0,02 při kterémkoli bloku. Jinak **INCONCLUSIVE**.
- Sekundární (popisně, bez vlivu na verdikt): log loss, reliability (10 binů), PR-AUC; alarmy při **pevném rozpočtu**
  = práh na 90. percentilu B3 predikcí trainu ⇒ epizodová precision/recall, falešné epizody/měsíc, lead time.
  Kritéria PROTOCOL (precision ≥ 60 %, recall ≥ 50 %, ≤ 2 falešné epizody/měs., 90 d forward) zůstávají kritérii
  **přijetí kandidáta**, ne G1; G1 GO je nesplňuje a nenahrazuje.
- G1 ≠ ziskovost. Žádná P/L simulace; G2 jen novým protokolem a novým schválením.

## 7. LOW_N brána (před výkonem)
OOS census `0103335` (run 43229950012): risk 30 ukotvených / **21 seskupených** epizod 2022–2026; ~123 nepřekrývajících
se 14d bloků ≥ 30. Brána ≥ 20 seskupených ⇒ formálně prochází, ALE práh i volba seskupení byly stanoveny **po** zhlédnutí
censu (proxy 17/25, přesný 21/30). Proto: výsledek G1 se v reportu vždy označí `LOW_N_MARGIN_POST_HOC_GATE` a
21 epizod ≠ 21 nezávislých OOS pozorování. Pokud G0 datový běh dá < 20 seskupených (jiná vylučovací data), ⇒
`INCONCLUSIVE_LOW_N`, výkon se nespouští.

## 8. Blokery před zamčením (bez nich se G1 nespouští)
- B1 Implementace B1/B2/B3 fitu + vnitřní validace (unit testy na syntetice).
- B2 Moving-block bootstrap (unit testy: determinismus, délka bloku, pokrytí na syntetické AR řadě).
- B3 Reálný loader 1m→denní XRP+BTC s PIT kontrolou a perturbačním testem.
- B4 G1 runner + workflow (níže) a G0 datový manifest commitnutý.
- B5 Řádek vlastníka `SCHVÁLENO: výkonnost radar V1 G1` v `dialog/OWNER_DECISIONS.md` (agenti soubor neupravují).
- B6 Nezávislá revize tohoto manifestu ChatGPT a nulové otevřené BLOCKERy.

## 9. Běh
Jediný `workflow_dispatch` na izolované větvi `claude/radar-g1-*`, vstup `confirm=G1-ONE-SHOT-<SHA manifestu>`,
`concurrency` bez paralelních běhů, bez `schedule`, bez automatického retry, Python 3.11, závislosti s pevnými verzemi
(`requirements` zamčen v manifestu), timeout 60 min, jen GitHub Actions free. Artefakty: manifest.json, data_qa.md,
predictions.csv, episodes.csv, metrics_by_fold.csv, baselines.csv, calibration.csv, false_positives.md, missed_crashes.md,
command log. Technické selhání = `INVALID_RUN`; opakování jen se stejným SHA a doloženou technickou příčinou, bez čtení
metrik (metriky se zapisují až na konci). Druhý úspěšný běh zakázán.
