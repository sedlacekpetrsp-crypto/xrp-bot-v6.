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
