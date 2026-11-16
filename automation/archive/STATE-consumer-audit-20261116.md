# Audit konzumentů `automation/STATE.md` (PR #60, podmínka 3 z dialogu 0344)

Datum: 2026-11-16 11:10 UTC · Claude (autopilot běh #66) · jen čtení, `git grep` nad `origin/research/autopilot` @ `7ede20b`
a `origin/dialog/claude-chatgpt` @ `245e33e`.

## Postup (reprodukovatelné)
```
git grep -n -i "automation/\|STATE\.md\|STATE-do\|KDE POKRAČOVAT\|CHECKPOINT" origin/research/autopilot -- '*.py' '*.yml' '*.yaml' '*.sh' '*.json'
git grep -n "STATE" origin/research/autopilot -- '*.md' ':!automation/STATE.md' ':!automation/REPORTS.md' ':!automation/TEST_LOG.md' ':!dialog/messages' ':!reports' ':!automation/DIALOG.md'
git grep -n "STATE" origin/dialog/claude-chatgpt -- dialog/README.md
```

## Výsledek
| Konzument | Co čte | Dopad kompakce |
|---|---|---|
| Kód / workflow (`*.py`, `.github/workflows/*.yml`, `*.sh`, `*.json`) | nic — žádný výskyt `STATE.md`; workflow čtou jen `automation/RUN_REQUEST` a `automation/PREDEPLOY_REF`; výskyty „checkpoint“ v `research_market_evidence.py` jsou nesouvisející svíčkové checkpointy | žádný |
| `automation/RUNBOOK.md` kroky 1, 4, 5, 6 | celý soubor; „minulý stav“, „poslední hodnoty, otevřené úkoly, blokace“, „nejvyšší otevřená položka backlogu“ | žádný — sekce *Otevřené úkoly*, *Čeká na vlastníka*, *Blokace* zůstávají doslovně (orig 315–356), poslední hodnoty = CHECKPOINT |
| `automation/RESEARCH_FRAMEWORK.md` §5 „pořadí fronty ve STATE.md“ | pořadí výzkumné fronty | **přesun** — FRONTA v2 a fronta 11-05 jsou jen v archivu ř. 177–314; řešeno odkazem v hlavičce nového STATE.md a výtahem aktivních bodů. §5 obsahově určuje priority sám, nemění se |
| Prompt plánované úlohy (vlastník) | „V STATE.md respektuj pořadí rozhodnutí od nejnovějšího“, poslední stav | žádný — všechny sekce ROZHODNUTÍ (11-09, 11-08 ×2, 11-07, 11-05) zůstávají doslovně; poslední stav = CHECKPOINT |
| `dialog/README.md` | žádný výskyt `STATE` | žádný |
| `reports/*.md`, `dialog/messages/*` | historické odkazy (např. „zapsat do STATE.md výchozí hodnoty“) | žádný — historické dokumenty, ne čtenáři aktuálního stavu |
| Řádek 3 „Poslední aktualizace … KDE POKRAČOVAT“ | rolující stav běhů (21 kB) | nahrazen CHECKPOINTem; autopilot po merge přepisuje CHECKPOINT místo prodlužování ř. 3 |

Mimo `research/autopilot`: větev `claude/claude-md-rozcestnik-20261109` (nesloučený CLAUDE.md) — při jejím případném
sloučení zkontrolovat odkaz na STATE.md stejným grepem.

## Závěr
Žádný strojový konzument; jediný sémantický posun = umístění fronty (§5), ošetřen odkazem. `check_state_compaction.py`
prokazuje bezeztrátovost, tento audit kompatibilitu. Merge dál jen s novým rozhodnutím vlastníka a po přegenerování
nad tehdejším tipem (autopilot mění ř. 3 každým během).
