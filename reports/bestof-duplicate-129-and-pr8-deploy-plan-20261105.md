# BEST-OF: duplicitní záznam id 129 a plán nasazení PR #8 (2026-11-05)

Výhradně PAPER. Vše níže je **čtecí analýza** (jen `SELECT` přes Render konektor, logy Renderu).
V produkční databázi ani na Renderu se nic nezměnilo. Žádná oprava se neprovádí bez souhlasu vlastníka.

## 1. Analýza záznamu id 129

### Oba řádky v `bestof_trades`

| id | symbol | setup | side | opened_at (UTC) | closed_at (UTC) | entry | exit | qty | pnl | reason | xmin |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 128 | XRPUSDT | BREAKOUT | LONG | 2026-11-05 08:20:29.773893 | 09:14:07.761682 | 1.322965 | 1.314837 | 1091.9168 | −10.3147 | STOP LOSS | 3431366 |
| 129 | XRPUSDT | BREAKOUT | LONG | 2026-11-05 08:20:29.773893 | 09:14:10.872418 | 1.322965 | 1.314837 | 1091.9168 | −10.3147 | STOP LOSS | 3431382 |

Stejná pozice (shodný `symbol + setup + opened_at`), shodné ceny, množství i P/L. Liší se jen čas
uzavření (o 3,1 s) a transakce zápisu (`xmin`). Jde o **jedno skutečné uzavření zapsané dvakrát**,
ne o dva obchody.

### Původ (logy Renderu, služba srv-dang770ae00c73em1sm0)

| čas UTC | instance | událost |
|---|---|---|
| 09:13:20 | — | start ručního deploye `edaa938` (dep-dbm4hc5bedkc73b761ng) |
| 09:13:57–09:14:01 | `s79bn` (nová, `edaa938`) | startup aplikace |
| 09:14:09.46 | `s79bn` (nová) | `CLOSE V8.1 FIX XRPUSDT STOP LOSS -10.3147` ⇒ **id 128** |
| 09:14:11.63 | `9r8m5` (stará, `9b41f6d`) | `CLOSE V8.1 FIX XRPUSDT STOP LOSS -10.3147` ⇒ **id 129** |
| 09:15:01 | — | druhý ruční deploy `edaa938` (dep-dbm4i5ec6qcc73fve6tg) |
| 09:15:04 | `9r8m5` (stará) | `Shutting down` |
| 09:15:38–09:15:41 | `47nzj` (aktuální) | startup aplikace |

Příčina: při zero-downtime deployi běžela stará instance ještě ~1 min souběžně s novou. Obě měly
pozici načtenou ze stejného stavu, obě vyhodnotily stop-loss a obě zapsaly uzavření. `save_trade`
neměla žádnou kontrolu duplicity (opravuje draft PR #8).

### Dopad na PAPER equity a statistiky

| ukazatel | aktuálně (s id 129) | správně (bez id 129) |
|---|---|---|
| `paper_balance` ve stavu | 9 617,0027 | 9 617,0027 — **správně, beze změny** |
| počet obchodů | 129 | 128 |
| výhry / prohry | 30 / 99 | 30 / 98 |
| win rate | 23,26 % | 23,44 % |
| součet P/L tabulky | −393,3120 | −382,9973 |
| profit factor | 0,554 | 0,560 |

- Zůstatek je správný: 10 000 − 382,9973 = 9 617,0027 odpovídá tabulce **bez** id 129. Každá
  instance odečetla ztrátu jen ve své paměti ze stejného výchozího stavu, uložený stav ji tedy
  obsahuje jednou.
- Chybně jsou jen statistiky a historie na dashboardu BEST-OF (načítají se z `bestof_trades`):
  o 1 obchod a −10,31 USDT víc, než odpovídá zůstatku.
- Cooldown ani otevřené pozice dotčené nejsou (pozice byla po uzavření odebrána v obou instancích).

### Další tabulky (stejná kontrola duplicit `symbol/setup/opened_at`)

- `bestof_trades`: 1 skupina (id 128+129). Starší záznamy bez `opened_at`: 0.
- `blue_whale_trades`, `fast_scalp_trades`, `leadlag_trades`, `tv_consensus_trades`,
  `v10_precision_trades`, `v81fix_trades`, `v8_trades`, `v9_trades`: 0 duplicit.
- `v8fixed_trades` (FLY): 3 skupiny, poslední 2026-10-07 — už ošetřeny tabulkou
  `fly_trade_exclusions` (id 250, 290, 314; reconciliation `already_applied`).

## 2. Návrh bezpečné opravy id 129 (NEPROVEDENO, čeká na souhlas)

**Doporučeno — varianta A: tabulka výjimek (stejný vzor jako FLY), nic se nemaže.**

1. Kód (součást PR #8 nebo samostatný PR, jeden společný deploy):
   - `CREATE TABLE IF NOT EXISTS bestof_trade_exclusions (trade_id INTEGER PRIMARY KEY,
     canonical_trade_id INTEGER NOT NULL, reason TEXT NOT NULL, authorized_at TIMESTAMPTZ DEFAULT NOW())`
   - načítání historie v `load_state`: `... FROM bestof_trades t WHERE NOT EXISTS
     (SELECT 1 FROM bestof_trade_exclusions e WHERE e.trade_id = t.id)`
   - testy: vyloučený řádek se nepočítá do statistik, zůstatek se nemění.
2. Data (až po vašem souhlasu, jedna transakce):
   `INSERT INTO bestof_trade_exclusions (trade_id, canonical_trade_id, reason)
    VALUES (129, 128, 'Duplicate close of opening 2026-11-05 08:20:29 during overlapping deploy 09:14 UTC')`
3. Ověření: dashboard 128 obchodů / −383,00; `paper_balance` beze změny 9 617,0027.
4. **Návrat:** `DELETE FROM bestof_trade_exclusions WHERE trade_id = 129;` + restart ⇒ přesně původní stav.
   Řádek 129 zůstává v `bestof_trades` po celou dobu.

Varianta B (nedoporučeno): přesun id 129 do archivní tabulky a smazání z `bestof_trades`. Vratné
zpětným vložením, ale mění historickou tabulku a nemá precedens v projektu.

Pozn.: zápis do produkční DB nelze provést z autopilota (konektor je jen pro čtení) — provede ho
vlastník, nebo se dočasně povolí jeden konkrétní zápis.

## 3. Plán nasazení PR #8 (merge = okamžitý deploy, Auto Deploy zapnutý)

Stav ověření: oprava `418f897` + testy `139d8b5`; proti skutečnému PostgreSQL ověřeno opakované
zpracování, 8 souběžných instancí, držení zámku po celou transakci a rollback při chybě; bez opravy
testy selžou. CI run 42008665479: 23 passed + 5× 6 passed.

**Před nasazením**
1. Souhlas vlastníka s PR #8 (a případně s variantou A výše — pak oba commity v jednom deployi).
2. Rebase/ověření, že PR #8 vychází z aktuálního HEAD `v8-fly-layer-test` (nyní `edaa938`).
3. Zvolit chvíli, kdy **BEST-OF nemá otevřenou pozici** (`/` nebo stav `positions` = prázdné) a
   ideálně ani jiné boty — samotný deploy opravy má ještě jedno riziko duplikátu: stará instance
   (bez zámku) může zapsat po nové.
4. Zapsat do STATE.md výchozí hodnoty: počet řádků `bestof_trades`, `paper_balance`, live commit.

**Nasazení**
5. Merge PR #8 do `v8-fly-layer-test` (vlastník). Render spustí deploy sám — **nespouštět ruční deploy
   navíc** (dnešní duplikát vznikl při dvou ručních deployích rychle po sobě).
6. Sledovat deploy do stavu `live` a ukončení staré instance (`Shutting down`).

**Ověření po nasazení (autopilot, jen čtení)**
7. Live commit = merge PR #8, obsahuje `da2f665` a `418f897`.
8. Duplicitní SELECT na `bestof_trades` ⇒ jen známá skupina 128/129, žádná nová.
9. `paper_balance` a počet obchodů beze skoku; v logu případně `SAVE TRADE SKIPPED DUPLICATE CLOSE`
   (= ochrana zafungovala), žádné `SAVE TRADE ERROR`.

**Návrat (rollback)**
10. Revert merge commitu v `v8-fly-layer-test` (nový commit, žádný force push) ⇒ auto deploy předchozí
    verze `edaa938`. Oprava nemění schéma ani data, rollback je proto bez migrace.

**Po nasazení (doporučeno, samostatně)**
11. Systémová ochrana pro všechny boty: leader lock (advisory lock na celý obchodní loop), aby při
    deployi obchodovala jen jedna instance.
