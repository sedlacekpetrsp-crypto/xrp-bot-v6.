# C krok 0 — doplnění R12/R13 (2026-11-08, autopilot běh #35)

Stejný nástroj a metoda jako `failure-attribution-xcheck-20261107.md` (validace 2023–24, náklady ×1, zvolená varianta; brány A1/A2/A5 při 0,5× lineárně z ×1/×2).
Vstupy: `research/max_effect/` (`b75328d`, run 42474245583) a `research/xs_momentum/` (`370e833`, run 42474090383). Ledger trades.csv = results.json u obou (1 702,32 / −620,45).

| Hypotéza | PR | Obch. | Hrubý ×1 | Náklady ×1 | % hrubého | Hrubý bez top 3 | Sharpe val. 0,5× / B&H | DD val. 0,5× / B&H | Závěr. čistý 0,5× | (a) | A1 | A2 | A5 | Nákladově limitovaná? |
|---|---:|---:|---:|---:|---:|---:|---|---|---:|:-:|:-:|:-:|:-:|---|
| `max_effect` (R12) | #33 | 156 | 2 103 | 401 | 19,1 | −3 908 | 0,58 / 1,73 | 38,1 / 37,3 | 1 121 | ✘ | ✘ | ✔ | ✔ | NE — bez top 3, A1 |
| `xs_momentum` (R13) | #35 | 104 | −302 | 318 | — | −4 641 | −0,01 / 1,73 | 27,3 / 37,3 | −1 420 | ✘ | ✘ | ✔ | ✘ | NE — hrubý záporný, A1, A5 |

**Celkem 0/18 nákladově limitovaných ⇒ STOP 0 platí i s R12/R13; téma C zůstává uzavřené.**
Výhradně PAPER, žádná nová data, žádný backtest.
