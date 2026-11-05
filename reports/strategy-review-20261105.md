# Kontrola strategií a kódu — 2026-11-05

Pracovní větev `claude/xrp-bot-strategy-backtest-7hu2l1`, založena z `v8-fly-layer-test`
@ `bd55352`. Změny sloučeny přes PR #5 do `v8-fly-layer-test` → merge commit
`da2f6659f0bb42e54be7c97a4b7d64bc9998bd14`. `main` nezměněn (`cfcde7a`).

## Jak číst tento report — úrovně důkazu

| Úroveň | Co zahrnuje | Stav |
|---|---|---|
| **A. Kód a lokální testy** | unit testy, lokální start aplikace, testovací PostgreSQL, **syntetická data** | provedeno, výsledky níže |
| **B. Historické výzkumné důkazy** | výsledky a ledgery commitnuté v repozitáři (jiné větve) | čteno; část nezávisle přepočtena (✔), zbytek převzat (↗) |
| **C. Produkce (Render, produkční PostgreSQL, burza)** | nasazení, běžící workery, skutečné účty a zápisy | **NEOVĚŘENO — žádný přístup** |

Nic z úrovně A ani B neověřuje produkci. Syntetické testy nejsou důkazem ziskovosti.
Tvrzení o tom, co v produkci „běží“, pocházejí z kódu a dokumentace repozitáře, ne z pozorování.

---

## A. Kód a lokální testy

### A1. Prostředí session

- Síťová politika odmítá CONNECT (HTTP 403) na `data-api.binance.vision`, `data.binance.vision`,
  `api.binance.com`, `fapi.binance.com`, OKX, Kraken, Coinbase. Návrh prostředí s přístupem
  k datům uživatel zamítl. **Nové tržní backtesty NEBYLY provedeny.**
- Bez Render API klíče/CLI; `api.render.com` a `xrp-bot-v8.onrender.com` nedostupné
  (jiné domény `*.onrender.com` netestovány); bez připojení k produkční PostgreSQL.
- GitHub API: `default_branch = main`. Že Render nasazuje `v8-fly-layer-test`, je údaj ze
  zadání uživatele, neověřeno.

### A2. Unit testy (`python -m pytest -q -p no:cacheprovider`, Python 3.13)

| Commit | Výsledek |
|---|---|
| `bd55352` bez `pytest-asyncio` | 199 prošlo / 30 selhalo |
| `bd55352` s `pytest-asyncio` | 210 prošlo / 19 selhalo (19 shodně s reportem z 2026-11-04) |
| `da2f665` (po PR #5) | **231 prošlo / 6 selhalo** |

- 11× `test_market_data`: chyběl plugin `pytest-asyncio`. Přidán `requirements-dev.txt`;
  `requirements.txt` beze změny.
- 13× `test_tv_consensus`: zastaralá fixture vůči zpřísněnému vstupnímu filtru; napevno staré
  prahy (BE 0,8R / trailing 1,1R / stale 45 min / 2 potvrzení obratu vs. v kódu 0,9R / 1,4R /
  75 min + 2 různé svíčky / 3 potvrzení); závislost na pořadí (globální USER_PAUSED injektáž
  z `app_v8_fly`). Upraveny pouze testy, produkční TV logika beze změny.
- Zbývá 6 selhání (3× `test_whale_fib_vwap`, 3× `test_whale_signals`): testují odstraněné
  chování; selhávají shodně na `bd55352`; neopraveno (rozhodnutí: smazat/přepsat).

### A3. Opravené chyby v kódu (`research/combined_paper_execution.py`)

Doloženo syntetickými unit testy (oba nové testy na `bd55352` selžou, na `da2f665` projdou):

1. **Identita P/L:** `unrealized_pnl` nezahrnoval zaplacený vstupní poplatek, takže
   `realized + unrealized` nadhodnocoval `equity − 10 000` o vstupní poplatky otevřených pozic
   (syntetický příklad: −0,19996 vs. −1,14996 USDT).
2. **Časování rebalance:** výzkumný backtest rebalancuje první hodinu UTC měsíce s daty do
   posledního dne předchozího měsíce; kód před opravou až 2. den s daty do 1. dne (nesoulad
   s testovaným pravidlem, nikoli look-ahead).

Zpětná kompatibilita byla ověřena **pouze na syntetickém ledgeru** (viz A5). Dopad na skutečný
produkční ledger je neověřený (C).

Kontrolováno čtením kódu bez nálezu chyby: `elite_paper.advance`, `swing_paper.net`,
`bestof_ema4h.close_ema`, Combined `fetch_daily` (vyřazuje neuzavřenou denní svíčku),
`FOR UPDATE` zámek a idempotence rebalance v rámci měsíce.

### A4. Lokální smoke test commitu `da2f6659f0bb42e54be7c97a4b7d64bc9998bd14`

Samostatný git worktree, skript `run_smoke.sh <sha>` (mimo repozitář). Testovací data:
dočasná **prázdná** PostgreSQL 16 v kontejneru (`postgresql://postgres@/xrpsmoke?host=/var/tmp&port=5434`),
po testu smazána.

1. `python -m pytest -q -p no:cacheprovider` → 231 prošlo / 6 selhalo.
2. `env -u DATABASE_URL uvicorn app_v8_ui:app --port 8801` (příkaz z `render.yaml`) → start OK,
   `/` 200, `/health` 200, `/combined/status` **404**, 0× Traceback. Tato aplikace PAPER workery
   neobsahuje.
3. `env -u DATABASE_URL uvicorn app_v8_fly:app --port 8802` → start odmítnut (exit 3,
   `ValueError: Persisted ledger required`) — záměrné fail-closed chování, i na `bd55352`.
4. `uvicorn app_v8_fly:app` s prázdnou testovací DB:
   - 4a bez markeru → start odmítnut (exit 3, `TypeError` v `fly_accounting_reconcile`, chybí
     řádek `v8fixed_state`).
   - 4b s ručně vloženým **testovacím stub markerem** `fly-ledger-reconcile-20261011` →
     start OK, 0× Traceback; `FLY LEGACY RECOVERY nothing_to_recover`,
     `FLY ACCOUNTING RECONCILIATION already_applied (test_stub)`; HTTP 200 na `/`, `/health`,
     `/combined`, `/combined/status`, `/combined/health`, `/elite-paper/status`, `/swing/status`,
     `/news-paper/status`, `/bestof/status`, `/lh-whale/status`, `/research/market-evidence/status`;
     vytvořeno 27 tabulek. Combined: `AWAITING_FIRST_SCAN`, 0 řádků (sken `PAPER_SCAN_ERROR`,
     proxy 403 na Binance). ELITE: `disabled_other_service` (kód spouští worker jen při
     `RENDER_SERVICE_ID == srv-dang770ae00c73em1sm0`, `elite_paper.py:197`).

### A5. Syntetický test kompatibility Combined ledgeru

**Ledger, cíle i ceny jsou vymyšlená testovací data**, nikoli snapshot produkce. Ledger vytvořen
kódem `bd55352`, poté zpracován `combined_paper_postgres.apply` z `da2f665`. Varianty předpokladu
`last_rebalance_day` = 2026-11-03 a 2026-11-04 (oba výsledky shodné):

- sken 2026-11-05: 0 obchodů, pozice a qty beze změny;
- identita `equity − 10 000 = realized + unrealized` platí (nerealizovaný P/L 17,6961 vs.
  starý vzorec 19,5961 USDT — syntetické ceny);
- opakovaný sken ledger nemění; první sken 2026-12-01 → `MONTHLY_REBALANCE`.

### A6. Připravený, NEPROVEDENÝ tržní backtest

`research/combined_selection_replay/` — zmrazený protokol, runner, SHA-256 manifest 292
archivů. 6 syntetických testů mechaniky prošlo (shoda výchozího pravidla, jen uzavřené dny,
limity vah, identita P/L, monotónnost nákladů, nezávislost na budoucích svíčkách, odmítnutí
neshodného SHA-256). Nejsou důkazem ziskovosti. Data nepoužitá při ladění začínají 10/2026
(1 rebalance) → výsledek bude neprůkazný.

---

## B. Historické výzkumné důkazy (commitnuté výsledky, žádný nový backtest)

✔ = nezávisle přepočteno z commitnutých ledgerů (součty čistého P/L sedí na cent, překryvy 0).
↗ = převzato z reportu/JSON, nepřepočteno. Všechna období byla použita při vývoji nebo výběru;
žádný řádek není výsledkem na nepoužitých datech.

| Strategie | Zdroj | Období | Obchody | Čisté P/L 1× | PF 1× | Max DD | 2× náklady |
|---|---|---|---:|---:|---:|---:|---|
| TV Consensus, 9 variant ✔ | `research/tv_validation_20261012` | 21.9.–12.10.2026 | 30–47 | −61,48 až −139,58 | 0,45–0,63 | 0,76–1,40 % | záporné |
| ELITE V18 ✔ | `elite-research-v1` cost audit | 4/2023–9/2026 | 97 | +4 717,96 | 2,45 | 11,15 % ↗ (hodinový mark) | +3 562,61, PF 2,10 |
| ELITE V18 bloky ✔ | tamtéž | 2023 / 24H1 / 24H2 / 25–26 | 18/17/18/44 | +42,89 / −492,26 / +2 443,11 / +2 387,47 | 1,07/0,09/4,28/3,00 | | 2023: −59,86 |
| ELITE V56 ✔ | `elite-research-v1` v56 | 4/2023–9/2026 | 77 | +820,51 | 2,01 | 2,18 % ↗ | +601,03, PF 1,67 |
| ELITE V56 bloky ✔ | tamtéž | 2023 / 24H1 / 24H2 / 25–26 | 18/15/15/29 | −40,13 / −96,22 / +760,86 / +194,04 | 0,82/0,43/7,50/1,67 | | |
| VMM_V1 (základ Combined) ↗ | `volatility-managed-momentum-research-20261022` JSON | 2023–9/2026 | 95 | +3 530,50 | 1,508 | 15,108 % | +3 214,59, PF 1,46 |
| Combined výběr | — | — | — | **nikdy netestováno** | — | — | — |
| BEST FIB 5m ↗ | `fib-timeframe-20261020` | 4–6/2026, 7–9/2026 | 2 / 1 | +6,41 / −9,18 | | | −9,18 |
| Whale trendline ↗ | `WHALE_TRENDLINE.md` | půlrok, riziko 0,1 % | 15 | +72,37 | | | +57,43 |

- Koncentrace ✔: V18 — 3 nejlepší obchody = 111 % čistého zisku (zbylých 94 dohromady ve
  ztrátě). V56 — bez 3 nejlepších +61,79 USDT (1×), −121,13 USDT (2×).
- V18 překročil vlastní limit propadu 10 % a V56 měl jen 2/4 kladné bloky (↗ `elite-research-v1`).
  VMM_V1 neprošel předregistrovanými branami (2022 a 2025 záporné, DD > 15 %).
- Větev `autocorr-regime-research-20261024`: 36 validačních README — 35 s rozhodnutím
  NEPROŠEL, 1 = TV validace (všechny varianty ztrátové). Ostatní větve byly prohledány jen
  výběrově; tvrzení se vztahuje pouze na prohledané výsledky.

**Závěr B:** V prohledaných výsledcích jsem nenašel strategii s průkazným kladným výsledkem
po nákladech na datech nepoužitých při ladění. Combined výběrové filtry nemají žádný backtest
a byly napsány po zveřejnění validačních let. Nové strategie nebyly přidány.

---

## C. Produkce — NEOVĚŘENO

Nic z následujícího nebylo pozorováno; jde o otevřené body k ověření v Renderu / DB:

1. Zda proběhl deploy po merge a zda služba běží na commitu `da2f665`.
2. Skutečný start command služby. `render.yaml` uvádí `app_v8_ui:app` (bez PAPER workerů);
   dokumentace (`NEWS_PAPER.md`, `reports/elite-forward-paper-20261104.md`) a `elite_paper.py`
   počítají se sdílenou službou `app_v8_fly` (`srv-dang770ae00c73em1sm0`).
3. Chyby v logu po startu; výsledek `FLY ACCOUNTING RECONCILIATION` (podle kódu a reportu
   z 12. 10. by měl být `already_applied` — neověřeno).
4. Které PAPER workery skutečně běží (Combined, ELITE V18/V56, Swing, Best-of, NEWS_LONG,
   Whale, LH Whale) a zda FLY/FAST/LEADLAG/TV zůstávají pozastaveny.
5. Stav a časy posledních zápisů: `combined_best_paper_state.updated_at`,
   `elite_forward_accounts`, `swing_paper_accounts`, `news_paper_state`, `blue_whale_state` aj.
6. Skutečný `last_rebalance_day` a pozice Combined ledgeru; zda Combined po spuštění otevřel
   pozice uprostřed měsíce (kód to při prvním skenu dělá — zda k tomu došlo, neověřeno);
   zda nasazení nezměnilo počet obchodů.
7. Zda Whale trendline v produkci obchoduje s 3% rizikem (kód `app_blue_whale_mirror.py:383`;
   historický vzorek byl při 0,1 %).

## Rizika k rozhodnutí uživatele (nic neměněno)

- Whale trendline: kód cílí 3 % riziko na obchod, testováno 0,1 % (15 obchodů).
- Nesoulad `render.yaml` vs. dokumentace o spouštěné aplikaci (C2).
- 6 zastaralých Whale testů — smazat nebo přepsat.
