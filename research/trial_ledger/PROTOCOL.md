# R10b — úplný ledger pokusů N (rozšíření R10 o PR #33–#65 a forward PAPER boty)

Stav: ZMRAZENO 2026-11-17 (autopilot běh #73) **před výpočtem**. Metodika, ne strategie (nepočítá se do limitu 3/den).
Účel: K9 dodatek 2 oprava 2 bod 1 — brána DSR e) se počítá při N = 450; pokud úplný ledger doloží N > 450, platí větší N
(před otevřením závěru K9). Výhradně PAPER; jen čtení gitu a jeden read-only SQL snapshot produkční DB (počty řádků, bez cen).

## Zdroje
1. R10 (`origin/research/variant-count-20261107`, `084b42c`): `reports/variant-count-reconstruction-20261107.json`.
2. Všechny `origin/*` větve: soubory `research/<dir>/trades.csv`, `trades.csv.gz`, `results.json` (scan `git ls-tree`).
3. `automation/STRATEGY_REGISTRY.md` (`research/autopilot`) — deklarované mřížky nespuštěných předregistrací.
4. Snapshot produkce `research/trial_ledger/prod_trade_tables_20261117.json` (read-only SQL přes Render MCP
   2026-11-17 ~15:10 UTC: tabulky `*trade*` v public, počet řádků, rozpad podle `setup`/`strategy`, kde sloupec existuje).

## Pravidla počítání (pevná před výpočtem)
- **A (R10):** dolní mez `n_lo = 190`, horní `n_hi = 194 + 15` (každá z 15 NEDOLOŽENÝCH hypotéz R10 = 1 pokus v horní mezi).
- **B (nové backtesty po R10):** každý adresář `research/<dir>` s `trades.csv(.gz)` nebo `results.json` na kterékoli
  `origin/*` větvi, který NENÍ pokryt R10 (adresáře souborů inventáře 110 + 16 R-testů R10) a není forward monitor
  (`research/forward/*`) ani replay bez nových pravidel (`combined_selection_replay*`).
  n = počet různých hodnot sloupce `variant` (bez regexu R10 `placebo|static|eqw|bottom|bench|buy_?hold`), jinak
  `results.json` → `candidates`/`variants`/`config`/`runs` jako R10, jinak 1. Stejný adresář na více větvích = 1× (max n).
  B se započítá do `n_lo` i `n_hi`.
- **C (předregistrované mřížky bez vypočteného výnosu):** n z registru; do `n_lo` jen K9 (fáze A +1, fáze B +2 —
  hodnocený pokus sám), ostatní (R8 #29, R9 #30, A5 #43, K7 #48) jen do `n_hi`.
- **D (produkční / forward PAPER boty):** z produkčního snapshotu. `n_lo` = tabulky s ≥ 1 obchodem, které nejsou
  zjevně pokryty inventářem (mapa předem: `tv_consensus_trades`→research/tv, `bestof_trades`→research/best,
  `candle_v8_trades`+`candle_v8_fixed_trades`→research/candle); `n_hi` = každá dvojice (tabulka, setup/strategy)
  s ≥ 1 obchodem (bez mapování) + tabulky s 0 obchody (1 každá). Forward RSI(2) a MAX-efekt forward = 0 (už v R10 / B).
  `fly_trade_exclusions` není tabulka obchodů (vyřazeno).
- **E (výsledek):** `N_doc_lo = A+B+C_lo+D_lo`, `N_doc_hi = A+B+C_hi+D_hi`. Pro bránu e) K9:
  `N_gate = max(450, N_doc_hi)` (konzervativně horní mez — větší N jen zpřísňuje). V[SR] = 0,5 beze změny (dodatek 2).
- Nic se neladí ani nevynechává podle výsledku; po výpočtu se pravidla nemění. Odchylky = dodatek s důvodem.

## Dodatek 1 (2026-11-17, po 1. výpočtu; jen zvyšuje N)
1. A4 `vortex_chop`: `trades.csv.gz` obsahuje jen zvolené buňky (1 hodnota), registr i `results.json` mají mřížku 8 buněk.
   Pravidlo B se doplňuje: n = max(n, počet `cells` v `results.json` téhož adresáře). Dopad +7 (1 → 8). Jiné adresáře beze změny
   (shoda s registrem: broad_trend, max_effect, new_listing_drift, xs_momentum = 4).
2. Zjištěné, ale **ponechané** dvojí započtení (konzervativní směr, pravidla se po výpočtu nesnižují):
   `spot_listing_drift` (B +1 i C_hi +4), `xrp_bank_credit_expansion_validation_20261105` (B +1, v R10 mezi 15 NEDOLOŽENÝMI ⇒ i v A_hi).
