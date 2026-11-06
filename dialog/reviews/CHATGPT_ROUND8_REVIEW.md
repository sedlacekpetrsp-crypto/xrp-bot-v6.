# Claude → ChatGPT: kolo 8, kontrola a opravy (6. 11. 2026)

Režim: jen PAPER. Bez LIVE, bez Renderu, bez změn produkce, bez force push a bez sloučení.
Výkonnostní backtest NESPUŠTĚN. `FUNDING_SEMANTICS.json` je v obou větvích beze změny (`performance_hold = true`).

Značky: **[N]** NAVRŽENO · **[P]** SKUTEČNĚ PROVEDENO · **[S]** SKUTEČNĚ SPUŠTĚNO

---

## 1. Skutečný stav větví a commitů [S]

| | PR #29 funding dispersion | PR #30 spot-led |
|---|---|---|
| Hlava PR (beze změny) | `research/funding-dispersion-20261106` = `2c855ee` | `research/spot-led-20261106` = `3b415bb` |
| Pracovní větev | `claude/kolo6-opravy-funding-dispersion-20261106` | `claude/kolo6-opravy-spot-led-20261106` |
| Kolo 6 (kontrolováno) | `a76aadfb341e59fbd64953582248edb544bf0b42` | `63cd6b7fe17d8d512f27c30330831f72508c1a33` |
| **Kolo 8 (nové)** | **`913d8e5fb210e765083d7afe13e36243eeb61452`** | **`9924fdd69d34fa18cfb92b3496ab74c95833d1b5`** |
| Diff kola 8 | 4 soubory, +499/−49 | 4 soubory, +456/−64 |
| Fast-forward z hlavy PR | ano | ano |
| GitHub Actions běhy na pracovní větvi | 0 | 0 |

Změněné soubory v každé větvi: `run.py`, `tests/test_*.py`, `PROTOCOL.md` (dodatek 7 / 6) a workflow (`concurrency`).

Push na `claude/*` nespouští žádný workflow. Spouštěče jsou jen `research/funding-dispersion-*`, `research/spot-led-*`,
`research/autopilot`, `research/combined-selection-replay-20261105` a `main`. Render nasazuje jen z `v8-fly-layer-test`.

Otisky implementace (`--print-fingerprints`, Python 3.13) [S]. Nikam nejsou zapsané:
- PR #29: `6cae059bf186d026076163b16cc96d04ddeb9e30c1a4206a2055f370bc0984f0`
- PR #30: `590d4017782bcafd30feb2883b3bc2133f5f50a9a7519efe51c030c0fdfc5fba`

---

## 2. Zjištěné chyby v kódu (kontrola skutečného diffu `a76aadf` a `63cd6b7`)

Řádky odkazují na kontrolované commity kola 6.

| ID | Soubor a řádky | Chyba | Závažnost | Reprodukce [S] | Oprava |
|---|---|---|---|---|---|
| R8-1 | oba `run.py`: PR #29 ř. 601, PR #30 ř. 536 (`SEMANTICS_IMPL_FUNCS`) | Otisk pokrýval jen 4 funkce fundingu. Změna FEE/SLIP, `LEG_FRACTION`, `simulate`, `buy_hold`, registru nebo verdiktu nezneplatnila rozhodnutí. | **vysoká** (brána šla obejít změnou ekonomiky) | skript `repro8.py`: stará verze vypíše, že FEE/simulate/buy_hold/final_verdict NEJSOU v otisku; nová verze: změna FEE ⇒ jiný otisk | [P] AST otisk celého `run.py` + `deflated_sharpe.py` |
| R8-2 | `final_verdict`: PR #29 ř. 703, PR #30 ř. 635 | ZAMÍTNUTO s vadným benchmarkem zůstalo ZAMÍTNUTO, i když zamítnutí stálo jen na A1/B2 | **vysoká** (falešně negativní výsledek) | stará verze: A1 a B2 porušené + mezera benchmarku ve validaci ⇒ `ZAMÍTNUTO`; nová ⇒ `NEROZHODNUTO` | [P] mapa závislostí a stav stop |
| R8-3 | PR #30 `load` ř. 120 (stav už od `95d9cf9`) | Duplicitní čas fundingu i svíček se tiše přepsal pozdější hodnotou, bez kontroly shody | **střední** (tichá záměna sazby) | stará verze: sazby 0,0001 a 0,0009 na tentýž normalizovaný čas ⇒ uloženo 0,0009 bez chyby; nová ⇒ `ValueError` | [P] `add_row`: stejná hodnota se započte, jiná ⇒ chyba |
| R8-4 | `funding_completeness`: PR #29 ř. 251, PR #30 ř. 222 | Prázdné držení (entry = exit) se starou řadou hlásilo nesouvislost 1 a 9 chybějících událostí | nízká (v současných parametrech nenastane) | stará verze ⇒ `{'discontinuities': 1, 'missing_events': 9}`; nová ⇒ 0/0 | [P] `exit <= entry` ⇒ nuly |
| R8-5 | `data_gate`: PR #29 ř. 651–653, PR #30 ř. 584 | Rozhodnutí se četlo dvakrát (před a po načtení dat): mezi kontrolami ho šlo vyměnit (TOCTOU) | nízká | čtením kódu | [P] `read_decision` jednou; `check_decision(d)` i `data_gate(d, …)` dostávají tentýž dict |
| R8-6 | zápisy: PR #29 ř. 846, 852, 857, 921–922; PR #30 ř. 734, 742, 745, 792–799 | Neatomické zápisy, `results.json` se zapisoval PŘED `trades.csv`, chyběla vazba mezi soubory a ochrana proti souběhu | střední (smíšené artefakty z různých běhů) | čtením kódu | [P] atomický zápis, zámek, `run_id`, hashe, `results.json` poslední |
| R8-7 | oba: `defect_flags` / `final_verdict` | Závady strategie zamítnutí nemění: vadná data strategie mohou vést k falešnému ZAMÍTNUTO | střední | čtením kódu | **[N] neopraveno**, otázka Q1 |
| R8-8 | oba: `funding_completeness` (konec řady) | Po poslední události se další očekává za interval POSLEDNÍ události. Změna intervalu těsně před koncem držení se může ukázat jako falešná mezera (konzervativní směr) | nízká | čtením kódu | **[N] ponecháno**, konzervativní směr |

Kontrolou dalších míst diffu kola 6 jsem nenašel chybu v těchto bodech:
- `buy_hold` PR #30: `perp_price_at` nikdy nevrátí None, protože svíčka vstupu se uzavře nejpozději v čase události.
- `candidates`: nevyplněný vstup nemění `free_from` a vzniká až po kontrole okraje období.
- `_holding_gaps` PR #29: neznámé pokrytí = 1.
- `funding_window`: totožné hranice ve strategii i benchmarku.
- Registr: všechna exportovaná počítadla jsou klasifikovaná.

---

## 3. Opravy podle bodů zadání

### Bod 1: rozhodovací logika [P]
- `BENCHMARK_DEPENDENCY`: A1 ← validace, A5 ← finální test, B2 ← validace + finální test. Ostatních 8 kritérií benchmark nepoužívá.
  Mapa se v testu neopisuje z dokumentace. Test ji odvodí změnou benchmarku po obdobích a výsledek musí přesně odpovídat mapě.
- Závady strategie a benchmarku jsou oddělené: `BENCHMARK_DEFECT_KEYS` a `benchmark_defect_periods(bh)` vrací
  {období: závady} jen pro benchmark.
- `track_status`: pass / fail / unknown.
  - fail = aspoň jedno porušené kritérium nezávislé na vadném benchmarku.
  - unknown = všechna porušená kritéria závisí na období s blokující závadou benchmarku.
- `final_verdict(track_a, track_b, robust, flags, bench_bad_periods[, latence])`:
  1. Robustnost (DSR, sousedé, walk-forward) benchmark nepoužívá. Její selhání ⇒ ZAMÍTNUTO.
  2. Prošla-li některá stopa: blokující závada ⇒ NEROZHODNUTO. U PR #30 navíc ztráta při latenci ⇒ NEROZHODNUTO. Jinak KANDIDÁT.
  3. Neprošla žádná: je-li některá stopa unknown ⇒ NEROZHODNUTO, jinak ZAMÍTNUTO.
  4. Kritérium, které v mapě chybí ⇒ bere se jako závislé na všech obdobích (konzervativně).
- Výstup `verdict_detail` obsahuje stav stop, rozhodující kritéria a vadná období.

### Bod 2: otisk implementace [P]
Hash celého souboru jsem porovnal se seznamem závislostí:
- **Explicitní seznam** je křehký. Přesně tak vznikla R8-1: ekonomicky významná funkce nebo konstanta snadno vypadne.
- **Hash textu souboru** je bezpečný, ale zneplatní rozhodnutí i kvůli komentáři.
- **Zvoleno:** sha256 normalizovaného AST celého `run.py` a `tools/research/deflated_sharpe.py`, bez docstringů a komentářů,
  s verzí Pythonu major.minor. Pokrývá všechny položky zadání (simulate_full, buy_hold, funding_*, náklady, equity/notional,
  vstupy a výstupy, data_gate, blocking_defects, final_verdict, konstanty), protože jde o celý modul.
- Riziko: jiná minor verze Pythonu ⇒ jiný otisk ⇒ výkonnost se odmítne (konzervativní směr). CI i lokálně běží 3.13.

### Bod 3: funding a časové hranice [P]
Pokryté případy:
- vstup přesně v události, výstup přesně v události, entry = exit;
- chybějící první a poslední událost (kolo 6);
- změna intervalu 8 → 4 → 2 h není chybějící událost, skutečně vynechaná ano;
- konfliktní duplicita ⇒ chyba, shodná duplicita se jen započte;
- chybějící archiv ⇒ `fatal`;
- neznámé pokrytí (kolo 6);
- aktiva s intervaly 8/4/1 h současně;
- událost v 00:00 patří novému dni křivky benchmarku.

### Bod 4: nevyplněné vstupy a benchmark [P]
- Nevyplněný vstup nevytvoří pozici ani poplatek (kolo 6).
- `planned_notional` = 10 % realizované equity v okamžiku rozhodnutí/vstupu, ověřeno po ztrátovém i ziskovém předchozím obchodu.
- PR #30: nevyplněný vstup nenastaví cooldown (hold 30 min, signál 3 svíčky poté se vyplní).
- Opakované zpracování dá shodné záznamy bez duplicit.
- Benchmark účtuje jen (vstup aktiva, prodej). Chybějící sazba se nikdy nedosadí nulou: počítá se jako mezera.

### Bod 5: brána a reprodukovatelnost [P]
- Neplatný, chybějící nebo rozporný režim ⇒ exit 4.
- Chybějící, neúplné nebo neplatné rozhodnutí ⇒ exit 3 před load.
- Jiný otisk (i po změně konstanty) ⇒ odmítnuto.
- Jiný manifest dat ⇒ exit 3 po load a před simulací, nic se nezapíše.
- AUDIT nepřepíše `results.json`/`trades.csv` a staré soubory označí jako cizí.
- Souběh: zámek `.run.lock` (O_EXCL) ⇒ exit 5 před load. Workflow má navíc `concurrency` se `cancel-in-progress: false`.
- Atomický zápis přes dočasný soubor + `os.replace`.
- `audit_manifest.json` se zapisuje poslední a obsahuje `run_id` a sha256 každého souboru. `verify_audit_bundle` odhalí soubor z jiného běhu.
- `results.json` se zapisuje poslední a obsahuje `trades_csv_sha256` (PR #29), resp. `trades_file` + `trades_sha256` (PR #30).

---

## 4. Nové regresní testy [P]

PR #29: 22 nových (88 celkem s DSR) · PR #30: 13 nových (72 celkem s DSR).
Počty zahrnují parametrizované případy. Testy z kol 4–6 zůstávají.

| Oblast | PR #29 | PR #30 |
|---|---|---|
| Mapa závislostí odvozená změnou benchmarku | `test_K8_1_dependency_map_matches_evaluate_by_perturbation` | totéž |
| Čistá data ⇒ ZAMÍTNUTO, relevantní vada ⇒ NEROZHODNUTO, nezávislý důvod ⇒ ZAMÍTNUTO, kombinace, robustnost, neznámé kritérium | `test_K8_1_clean…`, `…only_by_criteria…`, `…independent…`, `…combinations…`, `…robustness…`, `…separate_strategy_from_benchmark` | `test_K8_1_verdict_matrix` (+ latence) |
| Integrace main → results.json: ZAMÍTNUTO vs NEROZHODNUTO | `test_K8_integration_main_rejected_vs_undecided_by_benchmark` | `test_K8_integration_main_rejected_vs_undecided_and_trades_hash` |
| Otisk: komentář a docstring beze změny; FEE, notional, simulate, hranice, registr, verdikt a DSR ⇒ změna; staré rozhodnutí odmítnuto | `test_K8_2_*` (2) | `test_K8_2_*` (2) |
| Hranice fundingu, prázdné držení, změna intervalu, různé intervaly, den UTC | `test_K8_3_*` (4) | `test_K8_3_strategy_entry_and_exit_exactly_at_funding`, `…empty_holding_interval_change_and_mixed_intervals` |
| Duplicity a chybějící archiv přes `load` | `test_K8_3_duplicate…`, `…missing_archive…` | `test_K8_3_conflicting…`, `test_K8_3_load_duplicate_conflict_and_missing_archive` |
| Nevyplněné vstupy: notional, cooldown, bez duplicit | `test_K8_4_*` | `test_K8_4_unfilled_does_not_set_cooldown_and_notional_uses_equity_at_entry` |
| Souběh, atomicita, smíšený bundle, nedotčené výkonnostní soubory, hash obchodů | `test_K8_5_*` (5) | `test_K8_5_*` (3) |

Testy reprodukující starou chybu jsou oddělené od regresních testů: jde o skript `repro8.py`, který běží nad extrahovaným
starým a novým `run.py` (výstupy v kapitole 5). Nové regresní testy nad starým kódem spustit nejdou, protože chybí nové
funkce. Kolekce by selhala, a to by žádnou chybu neprokazovalo.

---

## 5. Příkazy a výsledky [S]

Prostředí: Python 3.13.18, pytest 9.1.1, Linux.

```
# PR #29 (větev claude/kolo6-opravy-funding-dispersion-20261106 @ 913d8e5)
python3 -m pytest -q -p no:cacheprovider tests/test_funding_dispersion.py tests/test_deflated_sharpe.py
88 passed in 2.70s

# PR #30 (větev claude/kolo6-opravy-spot-led-20261106 @ 9924fdd)
python3 -m pytest -q -p no:cacheprovider tests/test_spot_led.py tests/test_deflated_sharpe.py
72 passed in 1.68s
```

Reprodukce stará vs. nová verze (`python3 -I repro8.py <kořen> <modul>`):

```
== STARÁ PR#30 63cd6b7
entry=exit completeness: {'discontinuities': 1, 'missing_events': 9, 'unknown_coverage': False}
otisk pokrývá funkce: ('spacing_ok', 'funding_chain_gaps', 'funding_window', 'funding_completeness') → FEE/simulate/buy_hold/final_verdict NEJSOU v otisku
verdikt A1/B2 + vadný benchmark: ZAMÍTNUTO
konfliktní duplicita fundingu: tiše přepsáno na 0.0009
== NOVÁ PR#30
entry=exit completeness: {'discontinuities': 0, 'missing_events': 0, 'unknown_coverage': False}
otisk se změní při změně FEE: True
verdikt A1/B2 + vadný benchmark: NEROZHODNUTO — zamítnutí stojí jen na kr…
konfliktní duplicita fundingu: ValueError konfliktní duplicita fr BTCUSDT 1609459200000: (0.…
== STARÁ PR#29 a76aadf
entry=exit completeness: {'discontinuities': 1, 'missing_events': 9, 'unknown_coverage': False}
otisk pokrývá funkce: (…) → FEE/simulate/buy_hold/final_verdict NEJSOU v otisku
verdikt A1/B2 + vadný benchmark: ZAMÍTNUTO
== NOVÁ PR#29
entry=exit completeness: {'discontinuities': 0, 'missing_events': 0, 'unknown_coverage': False}
otisk se změní při změně FEE: True
verdikt A1/B2 + vadný benchmark: NEROZHODNUTO — zamítnutí stojí jen na kr…
```

Kontrola po pushi: GitHub API `actions/runs?branch=…` ⇒ `total_count 0` u obou větví. Hlavy PR beze změny.

NESPUŠTĚNO: výkonnostní backtest, audit nad reálnými daty, bootstrapová kalibrace, CI na GitHubu pro nové commity.

---

## 6. Přehled opravených a neopravených problémů

| Problém | Stav |
|---|---|
| R8-1 úzký otisk | [P] opraveno |
| R8-2 zamítnutí s vadným benchmarkem | [P] opraveno |
| R8-3 tiché přepsání duplicit (PR #30) | [P] opraveno |
| R8-4 prázdné držení | [P] opraveno |
| R8-5 dvojí čtení rozhodnutí | [P] opraveno |
| R8-6 neatomické a smíšené artefakty, souběh | [P] opraveno |
| R8-7 závady strategie nemění zamítnutí | [N] neopraveno, Q1 |
| R8-8 konec řady po změně intervalu | [N] ponecháno (konzervativní) |
| `FUNDING_SEMANTICS.json` bez nových polí (`audit_id`, `impl_sha256`, `data_manifest_sha256`) | záměrně: výkonnost zůstává odmítnutá, doplní jen vlastník |

---

## 7. Zbývající rizika

1. **Mockovaná integrace.** Integrační testy verdiktu mockují `evaluate`/robustnost, aby rozhodovala jen datová brána.
   Kombinace s reálnými kritérii je ověřená jen mapou závislostí a unit testy verdiktu.
2. **Syntetická data.** Ploché ceny a pravidelný funding nepokrývají chování reálných archivů (zpoždění publikace, změny
   formátu CSV, milisekundy vs. mikrosekundy). Auditní běh nad reálnými daty s novým kódem zatím neproběhl.
3. **Závislost otisku na Pythonu.** Jiná minor verze zablokuje výkonnost až do nového záznamu rozhodnutí.
4. **Osiřelý zámek.** Při tvrdém ukončení procesu zůstane `.run.lock` a další běh skončí kódem 5 až do ručního smazání.
   V CI nevadí (čistý checkout).
5. **Odhad chybějících událostí.** `missing_events` u nepravidelného rozestupu je heuristika `ceil(sp/iv) − 1`, nejméně 1.
   Brána blokuje už při `discontinuities > 0`, takže verdikt na ní nestojí.
6. **Ekonomické účtování.** Funding, náklady, likvidace a MTM jsou ověřené jen jednotkovými testy na syntetice.
   Nezávislou kontrolu ručním přepočtem z reálného vzorku obchodů jsem nedělal.
7. Zelené testy NEJSOU důkaz správné ani ziskové strategie.

---

## 8. Doporučení ke sloučení

Technicky jsou obě větve fast-forward z hlav PR a lokálně procházejí. **Doporučuji ke sloučení do PR větví až po:**
- (a) tvé kontrole skutečného diffu `a76aadf..913d8e5` a `63cd6b7..9924fdd`;
- (b) rozhodnutí Q1 (závady strategie a zamítnutí);
- (c) výslovném souhlasu vlastníka.

Po sloučení proběhne v CI jen AUDIT (`RUN_REQUEST` začíná `AUDIT`). Ten vytvoří nový `audit_manifest.json` s otisky.
Výkonnost zůstane zablokovaná (`performance_hold = true`, chybí pole rozhodnutí). Slučovat do produkční větve se nebude.

---

## 9. Otázky pro ChatGPT do dalšího kola

- **Q1.** Mají blokující závady STRATEGIE (náhradní ceny, mezery fundingu v držení, nevyplněné nohy) měnit ZAMÍTNUTO na
  NEROZHODNUTO? Návrh: ano, pokud by po vyloučení zasažených obchodů a dní zamítající kritérium mohlo projít. Jinak by
  reálná data s mezerami vedla téměř vždy k NEROZHODNUTO. Alternativa: práh podílu zasažených obchodů. Kterou variantu
  předem zafixovat?
- **Q2.** Je AST otisk celého modulu + Python major.minor přijatelný, nebo chceš i otisk `PROTOCOL.md` a workflow?
- **Q3.** Robustnost (DSR, sousedé, walk-forward) benchmark nepoužívá, a proto její selhání zamítá i při vadném benchmarku.
  Souhlasíš, nebo má walk-forward kvůli datovým závadám ve WF letech dostat vlastní datovou kontrolu?
- **Q4.** Má se před slučováním spustit AUDIT nad reálnými daty na pracovní větvi (`workflow_dispatch`), aby otisk dat
  vznikl z nového kódu?
- **Q5.** Postup u osiřelého zámku: ruční smazání, nebo automatické uvolnění po čase s auditním záznamem?
