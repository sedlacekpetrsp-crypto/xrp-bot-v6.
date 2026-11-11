# K7 — auditní balíček před případným výkonem (dle ChatGPT 0292 §4)

Stav: **výkon NESPUŠTĚN, výnosy ani ceny v tomto balíčku nečteny.** Autopilot běh #54, 2026-11-11 ~19:20 UTC.
Ověření: `python -I research/k7_macro_calendar/audit_package_check.py research/k7_macro_calendar` → `audit_package_check.json` (verdikt OK, 0 problémů).

| Požadavek 0292 §4 | Kde / výsledek |
|---|---|
| Immutable seznam 69 událostí s ex-ante URL + SHA snímku | `events_frozen_69.csv` (SHA-256 `00fe989d0ceed9c483bc624f3f1f4a14e03b16e12438e36c9140ced998c1b45b`), zdroj `step0_events.csv` (SHA-256 `2d5fc1db86a195dd87f38246829eb1a2f64130c8b0eff2264579133bd99faf8f`, výstup `b390f35`, run 42968402155). Každá událost: Wayback snímek `fomccalendars.htm` (`/web/<ts>id_/`), `evidence_hash` = SHA-256 snímku, `actual_hash` = SHA-256 tiskové zprávy Fedu. |
| Časy zveřejnění / as-of | `first_announced_at` = čas archivního snímku (kontrola: shoduje se s ts v URL u 69/69). PIT lead: min 29,6 d, medián 207,5 d; u 69/69 oznámení < vstup t−25 h. Čas t: 69/69 = 14:00 America/New_York (UTC s DST). Per-event řádek „For release at“ (krok 0c) NEOVĚŘEN — pro primární PRE24* nevadí (výstup t−1 h), omezuje jen exploratorní PRE2/POST2. |
| Event vs. publication vs. ingestion time | event = t (14:00 ET); publication ex-ante kalendáře = snímek (≥ 29,6 d před t); ingestion = stažení přes Actions (run 42968402155). Binance Vision ceny se použijí jen jako hotové hodinové svíčky (open v t−25 h a t−1 h), žádná data po t−1 h nevstupují do primárního endpointu. |
| Fixní vstup/výstup | PRE24*: long BTCUSDT perp, open 1h svíčky t−25 h → open t−1 h, taker, 1×; v `events_frozen_69.csv` sloupce `entry_utc_t-25h` / `exit_utc_t-1h` (zmrazeno). Dodatek 1 D1 (`78abe38`). |
| Směr a mediating variable | Směr long (H1 jednostranně: prémie za nesené makro riziko před oznámením). Mediating variable: **není přímo měřitelná z bezplatných PIT dat** (riziková prémie je latentní) — jen nepřímo: realizovaná vol v okně vs. placebo (diagnostika). ⇒ Podle §6 „Měřitelnost mechanismu“ je K7 slabý kandidát; vlastník by měl rozhodovat s tímto vědomím. |
| Cost stress | fee 0,095 % + skluz 0,05 % round trip ×1/×2/×3, základ ×2; funding pozorovaný (56 událostí ≥ 2019-09) / modelový 0,03 %/8 h (13 událostí), vykazováno zvlášť (D4). |
| Power / MDE | σ ≈ 3,5 %/24 h, placebo 20 párů ⇒ SE(D) ≈ 0,43 %, 90% CI ±0,71 %. MEE = 0,44 %. **Pravděpodobnost verdiktu (normální aproximace, před daty):** skutečný efekt 0 ⇒ GO 5 % / NO-GO 50 % / INCONCLUSIVE 45 %; efekt = MEE 0,44 % ⇒ GO 27 % / NO-GO 15 % / INCONCLUSIVE 58 %; efekt 1,05 % ⇒ GO 78 %. Test je **podsílený pro MEE**; nejčastější výsledek je INCONCLUSIVE. |
| Overlap se známými efekty | Placebo: stejný den v týdnu a UTC hodina, předchozích 26 týdnů, mimo ±72 h FOMC a ±24 h CPI, stejný vol kvartil (§6) ⇒ kontroluje sezónnost den/hodina (rodiny `research/weekend`, `weekend_carry`, session). FOMC je vždy středa ⇒ víkendové rodiny se nepřekrývají. Překryv s CPI ±24 h se reportuje (diagnostika). |
| Předchozí varianty | Registr: K7 jediný řádek (krok 0, DATA GO). Původní 4 okna (§4) nahrazena 1 primárním endpointem (D1); PRE2/POST2/POST24/14:30 jen diagnostika. N pro DSR = 222. Žádná dřívější FOMC/makro hypotéza v registru ani inventáři (grep 0). |
| Nulová leakage | Seznam událostí z ex-ante snímků (žádný výběr podle výsledku); 3 vyřazené předem: FOMC-2020-03-18 (nerealizováno jako plán), FOMC-2023-03-22 (pokrytí 1h < 100 %), FOMC-2026-12-09 (budoucí). Dělení 35/16/18 pevné podle pořadí. Placebo jen z minulosti, seed = hash event_id. Výnosy dosud nepočítány (ověřitelné: v repozitáři žádný trades.csv K7). |

## Závěr auditu (Claude)
Datová a metodická stránka je zmrazená a konzistentní (0 problémů). Slabiny: (1) mediating variable není přímo měřitelná,
(2) při MEE 0,44 % je síla ~27 % a nejčastější výsledek INCONCLUSIVE, (3) literatura ukazuje mizení pre-FOMC driftu po 2015.
**Doporučení:** výkon K7 nepovažuji za prioritu; má smysl jen jako levný falzifikační test (≈ 1 běh Actions). Rozhodnutí
zůstává na vlastníkovi (řádek „SCHVÁLENO: výkonnost K7“); bez něj se nic nespouští.
