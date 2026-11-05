# Kontrola strategií a kódu — 2026-11-05 (průběžný záznam)

Pracovní větev: `claude/xrp-bot-strategy-backtest-7hu2l1`, vytvořena ze stavu
`v8-fly-layer-test` @ `bd55352`. Do `v8-fly-layer-test` ani `main` se nezapisuje.

## 1. Kontrola repozitáře

- GitHub API uvádí `default_branch = main` (main @ `cfcde7a`, 2026-09-20),
  NE `v8-fly-layer-test`. Render (`render.yaml`, služba `xrp-bot-v8`) spouští
  `app_v8_ui:app`; podle zadání nasazuje `v8-fly-layer-test`.
- Ostatní větve (46) jsou pouze čteny (`git show`, `git ls-tree`).

## 2. Blokace prostředí

- Síťová politika prostředí odmítá CONNECT (HTTP 403) na `data-api.binance.vision`,
  `data.binance.vision`, `api.binance.com`, `fapi.binance.com`, OKX, Kraken, Coinbase.
- Návrh nového prostředí s povolenými hosty `data.binance.vision`,
  `data-api.binance.vision` uživatel zamítl (nelze schválit z telefonu).
- **Nové tržní backtesty proto NEBYLY provedeny.** Postup spuštění viz oddíl 7.

## 3. Testy (lokálně, Python 3.13)

| Stav | Výsledek celé sady `python -m pytest` |
|---|---|
| Výchozí `bd55352`, bez `pytest-asyncio` | 199 prošlo / 30 selhalo |
| Výchozí `bd55352`, s `pytest-asyncio` | 210 prošlo / 19 selhalo (19 shodně s reportem z 2026-11-04) |
| Tato větev | **231 prošlo / 6 selhalo** |

- 11× `test_market_data`: chyběl plugin `pytest-asyncio` (nejde o chybu kódu).
  Přidán `requirements-dev.txt`; Render dál instaluje jen `requirements.txt`.
- 13× `test_tv_consensus`: (a) fixture nesplňovala zpřísněný vstupní filtr
  (`trend_5m`, `fresh_*`, `CONSENSUS_IMPULSE`, skóre >= 88); (b) testy měly
  napevno staré prahy BE 0,8R / trailing 1,1R / stale 45 min / 2 potvrzení obratu,
  kód má 0,9R / 1,4R / 75 min + 2 různé svíčky / 3 potvrzení; (c) v celé sadě
  `app_v8_fly` globálně injektuje USER_PAUSED guard a obal `cycle()` — testy byly
  závislé na pořadí. Opraveny pouze testy, produkční TV logika beze změny (TV zůstává
  pozastaven).
- Zbývá 6 známých selhání (3× `test_whale_fib_vwap`, 3× `test_whale_signals`):
  testují odstraněné chování (`VWAP_TREND_PULLBACK` → `RECLAIM`, pauza
  `VWAP_REVERSION`, Telegram scanner). Selhávají shodně na výchozím commitu; neopravováno,
  vyžaduje rozhodnutí, zda testy smazat nebo přepsat.

## 4. Opravené doložené chyby (pouze v této větvi, NENASAZENO)

`research/combined_paper_execution.py` (běžící Combined PAPER monitor):

1. **Identita P/L:** `unrealized_pnl` nezahrnoval zaplacený vstupní poplatek, takže
   `realized + unrealized` nadhodnocoval `equity − 10 000` o vstupní poplatky
   otevřených pozic (syntetický příklad: −0,19996 vs. −1,14996 USDT). Opraveno;
   regresní test kontroluje identitu při zisku, ztrátě i stop-lossu.
2. **Časování rebalance:** výzkumný backtest rebalancuje první hodinu měsíce s daty
   do posledního dne předchozího měsíce; živý kód až 2. den s daty do 1. dne.
   Nejde o look-ahead, ale o nesoulad s testovaným pravidlem. Opraveno; zpětně
   kompatibilní se stavem v DB (uložený `last_rebalance_day` z listopadu nevyvolá
   mimořádný rebalance). Oba nové testy na původním kódu selžou, po opravě projdou.

Kontrolováno bez nálezu chyby: `elite_paper.advance` (náklady vstup/výstup,
`pnl = proceeds − debit`, equity po likvidačních nákladech, V18 breakout bez aktuální
svíčky, PK `id` událostí proti duplicitám), `swing_paper.net`, `bestof_ema4h.close_ema`,
Combined monitor (`fetch_daily` vyřazuje neuzavřenou denní svíčku, `FOR UPDATE` zámek,
idempotentní rebalance v rámci měsíce).

## 5. Hodnocení existujících strategií (z commitnutých důkazů, žádný nový backtest)

Metriky v tabulce jsem nezávisle přepočítal z commitnutých ledgerů, pokud jsou
dostupné (označeno ✔). Součty čistého P/L sedí na cent, překryvy pozic 0.

| Strategie (stav) | Data / období | Obchody | Čisté P/L (1×) | PF 1× | Max DD | Stres | Nepoužitá data |
|---|---|---:|---:|---:|---:|---|---|
| TV Consensus (pauza) ✔ | XRPUSDC 1m, kontrola 21.9.–12.10.2026 | 30–47 | −61,48 až −139,58 | 0,45–0,63 | 0,76–1,40 % | 2× skluz záporné | ne (překryv s dřívějším výzkumem) |
| ELITE V18 (exp. PAPER) ✔ | 4/2023–9/2026, souvisle | 97 | +4 717,96 (+47,2 %) | 2,45 | 11,15 % (> limit 10 %) | 2×: +3 562,61, PF 2,10 | ne — opakovaně použitá vývojová data |
| ELITE V18 bloky ✔ | 2023 / 24H1 / 24H2 / 25–26 | 18/17/18/44 | +42,89 / −492,26 / +2 443,11 / +2 387,47 | 1,07/0,09/4,28/3,00 | | 2× 2023 záporné | |
| ELITE V56 (exp. PAPER) ✔ | 4/2023–9/2026, souvisle | 77 | +820,51 (+8,2 %) | 2,01 | 2,18 % | 2×: +601,03, PF 1,67 | ne |
| ELITE V56 bloky ✔ | 2023 / 24H1 / 24H2 / 25–26 | 18/15/15/29 | −40,13 / −96,22 / +760,86 / +194,04 | 0,82/0,43/7,50/1,67 | | | |
| VMM_V1 (základ Combined) | 2023–9/2026 validace | 95 | +3 530,50 (+35,3 %) | 1,51 | 15,11 % (> 15 %) | 2×: viz JSON | 2025: −197,64 |
| Combined výběr (PAPER od 4.11.) | — | — | **netestováno** | — | — | — | — |
| Whale VWAP reversion (pauza) | viz `whale_vwap_validation` | | žádná varianta neprošla | | | | |
| BEST FIB 5m | 4–6/2026, 7–9/2026 | 2 / 1 | +6,41 / −9,18 | | | 2×: −9,18 | malý vzorek |
| Whale trendline (PAPER, **3 % riziko**) | půlrok, 0,1 % riziko | 15 | +72,37 | | | 2×: +57,43 | ne; 3 % riziko netestováno |

Koncentrace zisku (přepočteno): **V18 — 3 nejlepší obchody = 111 % čistého zisku**
(zbylých 94 obchodů je dohromady ve ztrátě); **V56 — bez 3 nejlepších +61,79 USDT**
při 1×, **−121,13 USDT** při 2×. Pozitivní výsledky obou stojí na jediném období
(2024 H2), V18 v 2024 H1 PF 0,09.

Výzkumné větve `autocorr-regime-research-20261024` a další: přes 30 dalších
předregistrovaných hypotéz (on-chain, makro, order flow, funding, opce, ETF…) —
**všechny NEPROŠEL**. Nenalezl jsem v repozitáři žádnou strategii, která by prošla
vlastními předem stanovenými branami na datech nepoužitých při ladění.

**Závěr:** Žádná běžící ani výzkumná strategie nemá průkazný kladný výsledek po
nákladech na nepoužitých datech. ELITE V18/V56 a Combined běží jako experimentální
PAPER na výslovné přání uživatele, nikoli jako validované. Combined výběrové filtry
nebyly nikdy backtestovány a byly napsány po zveřejnění validačních let. Nové strategie
jsem nepřidával — podle zadání mají přednost hodnocení existujících a data nejsou
k dispozici.

## 6. Rizika k rozhodnutí uživatele (nic neměněno)

- Whale trendline cílí 3 % riziko na obchod (kód `app_blue_whale_mirror.py:383`),
  historický vzorek 15 obchodů byl při 0,1 %. 30× vyšší riziko než testované.
- Combined monitor otevřel první pozice uprostřed měsíce (4. 11.), což backtest
  nikdy nedělá; oprava časování rebalance není nasazena.
- `main` je na GitHubu výchozí větví, ale Render nasazuje `v8-fly-layer-test`.

## 7. Nové tržní backtesty — NEPROVEDENO

Harness a zmrazený protokol: `research/combined_selection_replay/` (README, `run.py`,
`reference_vmm_20261022.json` se SHA-256 manifestem 292 archivů). Po povolení
`data.binance.vision` spustit podle README. Syntetické testy mechaniky
(`tests/test_combined_selection_replay.py`, 6 testů: shoda výchozího pravidla,
pouze uzavřené dny, limity vah, identita P/L, monotónnost nákladů, nezávislost na
budoucích svíčkách, odmítnutí neshodného SHA-256) prošly — nejsou důkazem ziskovosti.
Očekávání: čistá data od 10/2026 dají jen 1 rebalance → výsledek bude neprůkazný.

## 8. Po sloučení PR #5 (2026-11-05)

- PR #5 sloučen do `v8-fly-layer-test` → merge commit `da2f6659f0bb42e54be7c97a4b7d64bc9998bd14`
  (rodiče `bd55352`, `2fad28a`). `main` beze změny (`cfcde7a`).
- **Render NEOVĚŘEN:** session nemá Render API klíč/CLI; síť blokuje `api.render.com`
  i `*.onrender.com`; žádné připojení k produkční PostgreSQL. Stav deploye, nasazený commit,
  logy, workery ani časy zápisů nebyly zkontrolovány.
- Nesoulad konfigurace: `render.yaml` spouští `app_v8_ui:app` (importuje jen `app_v8`, PAPER
  endpointy vrací 404), dokumentace i ELITE modul počítají se sdílenou službou `app_v8_fly`
  (`srv-dang770ae00c73em1sm0`). Skutečný start command je nutné ověřit v Render dashboardu.

### Lokální smoke test sloučeného kódu `da2f665` (bez produkčních dat)

- `uvicorn app_v8_ui:app`: start OK, `/` a `/health` 200, bez Traceback.
- `uvicorn app_v8_fly:app` bez `DATABASE_URL`: start záměrně odmítnut
  (`Persisted ledger required`, fail-closed, existuje i před PR #5).
- `uvicorn app_v8_fly:app` s dočasnou lokální PostgreSQL 16 (prázdná DB + marker
  `fly-ledger-reconcile-20261011`, který v produkci existuje): start OK,
  `FLY LEGACY RECOVERY nothing_to_recover`, `FLY ACCOUNTING RECONCILIATION already_applied`;
  200 na `/`, `/health`, `/combined`, `/combined/status`, `/combined/health`, `/elite-paper/status`,
  `/swing/status`, `/news-paper/status`, `/bestof/status`, `/lh-whale/status`,
  `/research/market-evidence/status`. Combined worker běží, skeny končí `PAPER_SCAN_ERROR`
  (proxy 403 na Binance) → lokálně žádný zápis. ELITE lokálně `disabled_other_service`
  (spouští se jen pod produkčním `RENDER_SERVICE_ID`).
- Kompatibilita stavu Combined v PostgreSQL (simulované ceny): ledger vytvořený kódem
  `bd55352` 4. 11. → sken novým kódem 5. 11.: 0 obchodů, pozice a qty beze změny, identita
  P/L platí (nerealizovaný P/L +17,70 místo dřívějších +19,60 USDT = rozdíl vstupních
  poplatků), opakovaný sken idempotentní, první sken 1. 12. provede `MONTHLY_REBALANCE`.
  Lokální DB poté smazána.
