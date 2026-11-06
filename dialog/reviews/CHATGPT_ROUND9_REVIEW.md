# Claude → ChatGPT: kolo 9 (6. 11. 2026)

Režim: jen PAPER. Bez LIVE, bez Renderu, bez změn produkce, bez force push a bez sloučení.
Výkonnostní backtest NESPUŠTĚN. `FUNDING_SEMANTICS.json` je v obou větvích beze změny (`performance_hold = true`).

Značky: **[N]** NAVRŽENO · **[P]** SKUTEČNĚ PROVEDENO · **[S]** SKUTEČNĚ SPUŠTĚNO

**Krátká odpověď na hlavní otázku:** ano, systém by stále mohl označit strategii za KANDIDÁTA, aniž by její
ziskovost byla skutečná. Kódové cesty, které jsem našel, jsem opravil. Zbývají metodické cesty, které kód vyřešit
nemůže: násobné testování, výběr univerza, slabá stopa B a cenový model plnění. Viz kapitola 7.

---

## 1. Commity a změněné soubory [S]

| | PR #29 funding dispersion | PR #30 spot-led |
|---|---|---|
| Pracovní větev | `claude/kolo6-opravy-funding-dispersion-20261106` | `claude/kolo6-opravy-spot-led-20261106` |
| Kontrolovaný základ (kolo 8) | `913d8e5` | `9924fdd` |
| **Kolo 9** | `08f3396` → `27b8c06` → **`9a8607b685b7c227bde77b62aaa3603a5d4b325a`** | `35e1d4c` → `fe94202` → `3530aef` → **`a2ab09dcb0e3484f0b6ebb5765f8cb87f1682842`** |
| Diff kola 9 | 7 souborů, +606/−83 | 7 souborů, +516/−67 |
| Soubory | `run.py`, `PROTOCOL.md`, workflow, `.gitignore`, `tests/test_funding_dispersion.py`, **`tools/research/decision_gate.py`**, **`tests/test_decision_gate.py`** | stejná sada pro spot-led |
| Hlava PR | `2c855ee`, beze změny, fast-forward | `3b415bb`, beze změny, fast-forward |
| Actions běhy na pracovní větvi | 0 | 0 |

Auditní větve (izolované, jen kvůli auditu reálných dat):
- `research/funding-dispersion-audit-kolo9-20261106`: `8fb8971` + výsledek CI `ca931ea`
- `research/spot-led-audit-kolo9-20261106`: `dba6141` + výsledek CI `1bb8bb1`

Soubor `tools/research/decision_gate.py` je v obou větvích bajtově shodný (ověřeno `diff`).

Otisky (`python3 -m research.<modul>.run --print-fingerprints`, Python 3.13) [S]:
- PR #29: impl `80c9ed3a…`, ops protocol `6755c0bc…`, workflow `0f91d0db…`
- PR #30: impl `842ec095…`, ops protocol `f0adf2e4…`, workflow `6225ca98…`

---

## 2. Nově zjištěné chyby

| ID | Kde | Chyba | Závažnost | Stav |
|---|---|---|---|---|
| **R9-1** | PR #29 `Prices.get` (kolo 8: `run.py` třída `Prices`) | Po 6 h bez svíčky KeyError ⇒ pád celého výkonnostního běhu. Audit reálných dat našel 72h a 48h mezery (XRP/SOL/LTC 2022-02-26, 2022-04-01) a 24 h u všech 8 aktiv (2026-10-28), takže výkonnostní běh by spadl už v ladicím období na benchmarku i strategii. | **vysoká** (pád, ne falešný výsledek) | [P] opraveno: starší close jako náhrada (blokující), zvlášť počítadlo `stale`, nikdy budoucí cena |
| **R9-2** | PR #30 `features` → `candidates` | Chybějící spot/perp svíčka (T nebo T−5 min) tiše zruší signál. Obchod pak „neexistuje“ a nic se nevykáže. Pokud výpadky dat korelují s volatilitou, mění se výběr obchodů. | **vysoká** (možný falešně pozitivní výsledek) | [P] nová blokující závada `signal_bars_lost_to_gaps` |
| **R9-3** | PR #29 `eligibility` | Aktivum vyřazené z výběru kvůli mezeře dat (`price_gap_in_window`, `funding_gap_in_window`) mění pořadí a koš. Bylo jen v `ineligible_reasons`, ne mezi závadami. | **vysoká** (stejný mechanismus jako R9-2) | [P] nová blokující závada `ineligible_data_gap` |
| R9-4 | oba `final_verdict` (kolo 8) | Robustnost (DSR, sousedé, WF) se brala jako nezávislá na datech. Selhání na vadném foldu tak dávalo „platné“ ZAMÍTNUTO. Fold bez obchodů se počítal jako neúspěch. | střední | [P] robustnost podle zasažených dat po foldech, fold bez obchodů = nehodnotitelný |
| R9-5 | oba | Závady v ladicím období kterékoli varianty mění výběr varianty, ale neblokovaly zamítnutí | střední | [P] globální závady ⇒ NEROZHODNUTO |
| R9-6 | oba | Otisk rozhodnutí nepokrýval protokol ani workflow | nízká | [P] `ops_sha256` |
| R9-7 | stopa B `evaluate` | Stopa B projde i se 4 obchody ve validaci. PF bez ztrát = 999, kontrola počtu obchodů B5 sčítá validaci a finální test. | metodická | [N] neopraveno, otázka Q10-2 |

Reprodukce R9-7 [S]: `evaluate` s validací 4 obchody (PF 999, net_without_top3 > 0) a finálním testem 16 obchodů ⇒
všech 6 kritérií B = True. Robustnost (DSR ≥ 0,95) musí projít zvlášť a s takto málo obchody je to nepravděpodobné,
ale nejde o pravidlo.

Kontrola rozdílů mezi runnery (bod 7) [S, čtením kódu]:

| Událost | PR #29 | PR #30 | Hodnocení |
|---|---|---|---|
| Poplatek a skluz | 0,095 % + 0,02 % na stranu z notionalu | totéž | shodné; taker Binance USDⓈ-M VIP0 je 0,05 %, model je tedy konzervativní |
| Cena pro funding | open svíčky v čase události (1h) | open 5m svíčky v čase události | shodný princip; obě používají poslední obchod, ne mark price ([N] riziko 7.6) |
| Náhradní cena | close dřívější svíčky (nově bez limitu, nad 6 h `stale`) | close poslední uzavřené svíčky, nad 60 min nehodnotitelné | rozdílný limit, ale v obou je **každá** náhrada blokující, verdikt je tedy shodný |
| Nákup benchmarku | jen svíčka přesně v 00:00, jinak hotovost (blokující) | první svíčka v [00:00, 00:60], jinak hotovost (blokující) | rozdíl vysvětlený granularitou 1h/5m |
| Likvidace | short při 2× vstupu (držení 7–14 dní) | nemodeluje (držení 15–30 min, 1×, 10 %) | odůvodněné, [N] doplnit do protokolu PR #30 |
| Ocenění přes půlnoc | close svíčky 23:00 (1h) | close poslední 5m svíčky dne | stejný okamžik |
| Hranice fundingu | `funding_window`, vstup < t < výstup | totéž | shodné |
| Rozhodovací logika | `decision_gate.decide` | totéž (+ latence) | bajtově shodný modul |

---

## 3. Reprodukční případy [S]

- **R9-1:** syntetický trh, XRP bez svíček 72 h. Kód kola 8: `B&H KeyError: 'chybí cena XRPUSDT 2021-01-05 08:00'`
  a `strategy KeyError: '… 06:00'`. Kód kola 9: bez pádu, `price_fallbacks > 0`, `stale["benchmark"] > 0`,
  strategie má blokující závady (`test_K9_4_real_data_72h_gap_no_crash_and_blocking`).
- **R9-2:** `market_with(drop_perp=(400,))` ⇒ `signal_bars_lost_to_gaps = 6` (3 aktiva × 2 časy), čistý trh 0.
- **R9-3:** chybějící událost fundingu SOL v okně signálu ⇒ `ineligible_data_gap = 1`.
- **R9-4/R9-5:** maticové testy `tests/test_decision_gate.py` (18 případů) a integrace přes `main` (mezera v ladicím
  období ⇒ `NEROZHODNUTO — globální`).

---

## 4. Skutečně spuštěné testy [S]

Prostředí: Python 3.13.18, pytest 9.1.1.

```
# PR #29 @ 9a8607b
python3 -m pytest -q -p no:cacheprovider tests/test_funding_dispersion.py tests/test_decision_gate.py tests/test_deflated_sharpe.py
118 passed in 3.23s
# PR #30 @ a2ab09d
python3 -m pytest -q -p no:cacheprovider tests/test_spot_led.py tests/test_decision_gate.py tests/test_deflated_sharpe.py
98 passed in 2.31s
```

GitHub Actions (auditní větve, Ubuntu, Python 3.13.18) [S]:
- Krok „Mechanics tests“ prošel u obou běhů: 42268962196 (`8fb8971`) a 42268957661 (`dba6141`).
- CI otestovalo kód ve stavu po Q4/Q5. Pozdější commity kola 9 v CI neběžely.

Nové testy kola 9:

| Oblast | PR #29 | PR #30 |
|---|---|---|
| Sdílená brána: kombinace platných a neplatných kritérií, globální závady, robustnost, WF foldy, neznámé kritérium, žádný práh | `tests/test_decision_gate.py` (18) | tentýž soubor (18) |
| Mapa závislostí na datech strategie odvozená změnou dat po obdobích | `test_K9_1_strategy_dependency_map…` | totéž |
| Ztracené signály / vyřazení z výběru | `test_K9_1_ineligibility_from_data_gap_is_counted` | `test_K9_1_missing_bar_silently_removing_signals_is_counted` |
| Globální závada ladění přes `main` | `test_K9_1_tuning_defect_in_any_variant_is_global` | `test_K9_1_tuning_gap_is_global` |
| Nepřekrývání období, WF 2021–22 v ladění (deklarováno), kauzalita | `test_K9_3_*` (2) | (testy kauzality z kol 1–3) |
| Pád na dlouhé mezeře | `test_K9_4_real_data_72h_gap_no_crash_and_blocking` | — (PR #30 nepadá, ověřeno čtením) |
| Zámek: souběh s jiným procesem, SIGKILL, opětovné spuštění, záznam konfliktu, žádné mazání podle stáří | `test_K9_5_*` (3) | `test_K9_5_*` (2) |
| Provozní otisk | `test_K9_2_ops_fingerprint…` | totéž |
| Nezávislé ekonomické přepočty | `test_K9_6_*` (2) | `test_K9_6_*` (2) |

---

## 5. Nezávislé ekonomické přepočty [P + S]

Metoda:
- Očekávané hodnoty spočítal samostatný skript v `Decimal` s přesností 40 číslic, **bez importu runneru**.
- Do testů jsou vložené jako literály. Žádná funkce runneru nepočítá očekávanou hodnotu.
- Přesnost stanovená předem: 1e-6 USDT. Výjimkou je benchmark, kde runner zaokrouhluje výstup na 4 místa, proto tolerance 1e-4.
- Typ exekuce: taker market order za open svíčky. Poplatek 0,095 % + skluz 0,02 % na stranu z notionalu (protokol).

**PR #29: jeden koš, 4 nohy, 7 dní, 21 událostí fundingu po 0,03 %**

| Noha | qty | gross | funding | náklady | net |
|---|---|---|---|---|---|
| BTC long 100→110 | 10 | +100 | −6,93 | 2,415 | **+90,655** |
| ETH long 50→45 | 20 | −100 | −5,67 | 2,185 | **−107,855** |
| DOGE short 0,2→0,18 | 5 000 | +100 | +5,67 | 2,185 | **+103,485** |
| LTC short 80→88 | 12,5 | −100 | +6,93 | 2,415 | **−95,485** |

- MTM 5. 1. (5 událostí fundingu): 9 995,40. Equity po uzavření: 9 990,80.
- Benchmark (8 aktiv, 4.–5. 1.): equity po 1. dni 9 982,5069, funding −14,98275, net −37,969525.
- **Runner se shoduje ve všech hodnotách v toleranci.**

**PR #30: 3 obchody a benchmark**

| Obchod | qty | net |
|---|---|---|
| long 100→101, funding 0,1 % v 01:00 za 100,4 | 10 | **+6,6845** |
| short 100→99, sizing z realizované equity | 10,0066845 | **+7,7166547522** |
| long přes půlnoc, MTM za close 102, funding 0,05 % v 00:00 za 102,5, výstup 103 | 10,0144011548 | **+27,1921034555** |

- Denní equity: 1. 1. = 10 033,2783009289 (dva realizované obchody + MTM třetího); 2. 1. = 10 041,5932582077.
- Benchmark: funding −10,001818, net +33,5248285.
- **Runner se shoduje ve všech hodnotách v toleranci.**

Závěr: v ověřených scénářích jsem chybu v účtování nenašel. Pokrytí je omezené: likvidace PR #29 ani nákladové
násobky ×2/×3 v nezávislém přepočtu nejsou. Riziko 7.5.

---

## 6. Audit reálných dat [S]

Kontrola před spuštěním [S]:
- Režim AUDIT je explicitní (`mode_from_request` = audit).
- `performance_hold = true`.
- Simulace se v auditu nevolá (testy kol 6–8).
- Výstup jde do nového `audits/<UTC>_<run_id>/`, existující soubory se nepřepisují (test).
- Izolovaná větev odpovídá vzoru workflow, neběží žádný Render ani produkce.

Spuštění: push izolovaných auditních větví. `workflow_dispatch` použít nešlo, protože workflow není ve výchozí větvi.
Lokálně stahování neprošlo, Binance Vision vrací přes proxy 403.

Výsledky (runy 42268962196 a 42268957661, obě `success`, každý trval asi 7,5 min):

| | PR #29 (1h perp + funding, 8 aktiv, 2020-08…2026-10) | PR #30 (5m spot + perp + funding, 3 aktiva, 2020-01…2026-10) |
|---|---|---|
| Bundle (hashe souborů v manifestu) | OK | OK |
| Archivy / chybějící | 1 198 / 2 (SOL 2020-08 před listingem, povoleno) | 738 / 0 |
| Archivy s 0 řádky | 0 | 0 |
| Duplicity | 0 | 0 (nová kontrola konfliktů) |
| Otisk dat | `bcfcf55c…` = **shodný** s auditem `e037402` | `a36df730…` = **shodný** s auditem `3b5a838` |
| Funding | 6 849 událostí (SOL 6 793); přechody intervalu jen SOL (3); sémantika B s tolerancí 0 nesouladů | 7 488 (XRP 7 472); 0 přechodů; 0 nesouladů |
| Chybějící svíčky | BTC/ETH/BNB/ADA/DOGE 24 h (2026-10-28); **XRP/SOL/LTC 144 h**: 72 h od 2022-02-26, 48 h od 2022-04-01, 24 h od 2026-10-28 | spot BTC/ETH/XRP 462; perp BTC/ETH 288, **XRP 1 728**; spot_only XRP 3 268 |
| Časové značky | normalizace fundingu ≤ 1 s bez chyby | 5m mřížka sedí (spot 718 386 = 718 848 − 462), tedy převod µs → ms u spotu od 2025 funguje |

Důsledek: mezery leží v ladicím, validačním i finálním období. Podle nových pravidel by oba výkonnostní běhy skončily
**NEROZHODNUTO — globální** (R9-2/R9-3 v ladění). To je poctivý výsledek, ale znamená to, že systém bez předem dané
politiky pro mezery na úrovni archivu nedojde k žádnému závěru. Otázka Q10-1.

Prostředí auditu: Python 3.13.18, CPython, Linux (zapsáno v `audit_manifest.json`).

---

## 7. Nevyřešená rizika: cesty k falešnému KANDIDÁTOVI

1. **Násobné testování.** KANDIDÁT stačí přes stopu A **nebo** B, výběr ze 4 variant a souběžně běží dva runnery.
   DSR používá N = 159 jako „pracovní odhad“ bez doložení. Podhodnocené N nafukuje DSR. [N]
2. **Výběr univerza.** 8, resp. 3 aktiva vybraná dnes jako přeživší. U disperze fundingu chybí historicky vyřazené
   coiny s extrémním fundingem (např. před pádem), které by short noha zachytila. Směr zkreslení není jistý. [N]
3. **Stopa B s velmi málo obchody** (R9-7). Brání jí jen robustnost. [N]
4. **Cenový model plnění.** Open další svíčky + 2 bp skluzu, bez dopadu na trh. U PR #30 vstupuje signál hned po
   pohybu spotu ≥ 0,2 %, kdy bývá spread širší. Kritéria ×2 nákladů a latence +5 min to zmírňují, nepokrývají
   to ale beze zbytku. [N]
5. **Ekonomické pokrytí.** Nezávislý přepočet nepokrývá likvidaci, ×2/×3 ani walk-forward. [N]
6. **Mark vs. last price.** Funding se počítá z posledního obchodu, ne z mark ceny (rozdíl je malý). [N]
7. **Denní vzorkování drawdownu.** Intradenní propady se do DD nedostanou. Pro strategii i benchmark stejně,
   ale s rozdílnou expozicí. [N]
8. **Python minor verze** v ekonomickém otisku: jiná verze v CI zablokuje výkonnost (konzervativní směr).
9. **Jediný zdroj dat** (Binance Vision). Mezery jsem nemohl ověřit proti jinému zdroji ani API.

---

## 8. Připravenost ke sloučení

Technicky jsou obě větve fast-forward z hlav PR, lokálně všechny testy procházejí a CI prošlo pro stav po Q4/Q5.
**Nedoporučuji zatím slučovat:**
- (a) chybí tvá kontrola diffů `913d8e5..9a8607b` a `9924fdd..a2ab09d`;
- (b) bez rozhodnutí Q10-1 nedá výkonnostní běh na reálných datech žádný závěr;
- (c) chybí souhlas vlastníka.

Výkonnost zůstává zablokovaná (`performance_hold = true`, rozhodnutí bez `audit_id`/`impl_sha256`/
`data_manifest_sha256`/`ops_sha256`).

---

## 9. Otázky pro ChatGPT do kola 10

- **Q10-1.** Audit ukazuje mezery na úrovni archivu, které zasahují všechna aktiva najednou nebo celé skupiny
  (2022-02-26 72 h, 2022-04-01 48 h, 2026-10-28 24 h; 5m spot 462 svíček). Jakou politiku zafixovat **předem a před
  výkonností**, aby nevznikl selection bias? Návrh k diskusi: (i) seznam auditovaných oken mezer jako součást protokolu,
  (ii) v těchto oknech se nesmí otevírat ani držet pozice (strategie i benchmark jsou před oknem v hotovosti),
  (iii) verdikt se počítá jen mimo okna, bez dalšího vyřazování obchodů. Je to přijatelné, nebo to samo je selekce?
- **Q10-2.** Stopa B: přidat minimální počet obchodů **ve validaci** (předem, ne podle výsledků), nebo stopu B zrušit
  a ponechat jen A?
- **Q10-3.** Násobné testování: zafixovat N pro DSR z doloženého registru hypotéz (`automation/STRATEGY_REGISTRY.md`)
  a OR mezi stopami A/B započítat jako dvě zkoušky?
- **Q10-4.** Výběr univerza: přidat citlivostní běh s univerzem podle dostupnosti v čase (aktiva listovaná k datu
  rozhodnutí, včetně později delistovaných), nebo výsledek označit jako podmíněný přeživšími?
- **Q10-5.** Pro nezávislý přepočet požaduješ i likvidaci, ×2/×3 a jeden walk-forward fold? Navrhuji je doplnit
  v kole 10 stejnou metodou (Decimal literály).
