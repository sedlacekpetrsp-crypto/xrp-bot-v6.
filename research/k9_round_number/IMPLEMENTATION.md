# K9 — implementační poznámky ke kroku 0 a fázi A (k oponentuře, NEmění zmrazený PROTOCOL.md)

Stav 2026-11-16 (autopilot běh #67): kód + syntetické testy, **nic se nestahovalo ani nepočítalo**. Spuštění až po
oponentuře ChatGPT k PROTOCOL.md (dialog 0351) a jen v rozsahu kroku 0 → fáze A.

- `audit.py` (krok 0): 3 aktiva × 82 měsíců (2020-01..2026-10) Binance Vision UM `klines/1m`; SHA-256 vs CHECKSUM se
  ověřuje PŘED parsováním; stavy OK / MISSING / CHECKSUM_FAIL / PARSE_FAIL / LOW_COVERAGE (< 99 % minut);
  brána < 90 % OK měsíců ⇒ DATA NO-GO; manifest JSON se SHA-256 každého ZIP. CSV s hlavičkou i bez, časy ms i µs.
- `phase_a.py` (fáze A): před detekcí úplná minutová mřížka (mezera = NaN ⇒ okno 60 min přes mezeru nevytvoří
  událost, nic se neimputuje); řádky s NaN metrikou (minuta s nulovým objemem v okně) se z D vynechají.
- **Volby k posouzení (oponent ChatGPT):**
  1. Souhrnný CI přes aktiva = společný bootstrap STEJNÝCH dnů pro všechna aktiva (zachová korelaci), váhy pevné
     = podíl kulatých událostí aktiva v původním vzorku. Alternativa: váhy přepočítávat v každé replikaci.
  2. Repliky, kde některé aktivum nemá v převzorkovaných dnech kulatou nebo placebo událost, se vyřadí (počet
     `valid_reps` se reportuje).
  3. Hranice období: událost s časem < 2024-01-01 00:00 UTC = vývoj; okno lookback smí sahat přes hranici (jen
     minulost, žádný look-ahead).
- Testy: `tests/test_k9_round_number.py` (6) + `tests/test_k9_step0_phase_a.py` (13), lokálně 19 passed.

## Oponentura ChatGPT 0353 (kolo 3, téma uzavřeno) → dodatek 1 PROTOCOL.md
- Volba 1 (pevné váhy, společné dny): SOUHLAS + povinně CI po aktivech → `pooled_diff()["per_asset"][a]["lo"/"hi"]`.
- Volba 2 (vyřazení replik): PODMÍNĚNÝ SOUHLAS → `invalid_frac` > 5 % ⇒ INCONCLUSIVE (`evaluate`).
- Volba 3 (lookback přes hranici): SOUHLAS beze změny.
- Síla: `power_table()` (jen počty/den) + `decisive_power()`; expozice: `exposure_table()`.
- Testy: +5 syntetických (`tests/test_k9_step0_phase_a.py`), lokálně 24 passed.

## Fáze B (2026-11-17, kód PŘED daty, nespuštěno)
- `phase_b.py` — obchody (vstup open t+1, výstup close t+H, 1 pozice/aktivum, funding), předbrána + výběr H*, brány a)–g),
  rozpad, benchmarky (B&H stejně vážený, exposure-matched long), drawdown, expozice.
- `phase_b_run.py` — FAIL CLOSED runner (schválení vlastníka, SHA-256 dat = manifest kroku 0, stage dev/final, výběr H*
  commitnutý v HEAD a vázaný na SHA-256 PROTOCOL.md).
- `verify_phase_b.py` — nezávislý přepočet E, ×2, ×3, Δ placebo a DSR z `phaseB_trades.csv` (neimportuje runner).
- `tools/research/deflated_sharpe.py` + test — beze změny převzato z `research/broad-trend-20261109` (`25e8014`).
- Workflow `k9-phaseB.yml` — spouští se jen commitem RUN_REQUEST_PHASEB_DEV / _FINAL ve větvi `research/k9-phaseB-*`.
- Testy `tests/test_k9_phase_b.py` (25, syntetické): vstup/výstup a znaménko, žádný look-ahead z minuty t, blokace,
  chybějící minuty, funding hrany, předbrána a shoda H, zasazená hrana ⇒ GO a kontroly (placebo, náhodný vstup, síla,
  chybějící minuty) ⇒ NO-GO/INCONCLUSIVE, stabilita, bootstrap, oddělení dev od závěru, end-to-end + nezávislý přepočet.
- Oprava 3 (dialog 0369): `random_trades(exclude_times=…, diag=…)` vylučuje všechny kulaté signální minuty aktiva
  (`build_trades` stats `signal_times` vč. blokovaných); runner vykazuje `random_support.excluded_signal_minutes`.
  +2 syntetické testy; nezávislý křížový audit `research/k9_placebo_audit` (ChatGPT) na syntetice: bez opravy 4
  kontaminované, s opravou 0 (PASS).

