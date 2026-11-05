# Evidence testů a kontrol (1 řádek na běh, nejnovější dole)

| UTC | Commit | Typ | Výsledek | Odkaz |
|---|---|---|---|---|
| 2026-11-05 07:25 | bd55352 | pytest lokálně | 210 / 19 selhalo (s pytest-asyncio) | report strategy-review |
| 2026-11-05 07:52 | da2f665 | pytest + smoke lokálně | 231 / 6; start app_v8_fly s test DB OK | report strategy-review A4 |
| 2026-11-05 08:23 | 5db2686 | Combined replay (CI) | EVALUATED, NEPROŠEL; SHA-256 8da9517f… | actions/runs/41993843175 |
| 2026-11-05 08:35 | e9f3917 | pytest lokálně | 238 / 0 | reports/followup-20261105.md |
| 2026-11-05 08:39 | aec6baa | status snapshot (CI) | 6× HTTP 200, P/L součet −3 170,34, PR #5 nenasazen | actions/runs/41996097278 |
| 2026-11-05 08:44 | 550bc81 | autopilot checks #1 (CI) | 6× HTTP 200; tests 238 passed; proces od 2026-11-04 19:58 UTC (PR #5 nenasazen); P/L součet −3 170,35; extra_rebalance false | actions/runs/41996806445 |
| 2026-11-05 08:53 | 5a99dd8 | autopilot checks #4 po merge PR #6 (9b41f6d) | 6× HTTP 200; tests OK; proces stále od 2026-11-04 19:58 UTC ⇒ **deploy neproběhl** ani 5 min po merge; účty beze změny | actions/runs/41997935726 |
| 2026-11-05 08:55 | acb6191 | autopilot checks #5 | stejné jako #4: proces od 2026-11-04 19:58 UTC, 7 min po merge PR #6 stále bez deploye | actions/runs/41998250268 |
