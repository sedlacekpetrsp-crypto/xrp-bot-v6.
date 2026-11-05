# Autopilot STATE — přepisuje se každým během

Poslední aktualizace: 2026-11-05 ~08:45 UTC (ruční založení, session Claude Code).

## Produkce (poslední známé hodnoty)

- Služba `xrp-fly-whale-24-7` (`srv-dang770ae00c73em1sm0`), start `uvicorn app_v8_fly:app`,
  větev `v8-fly-layer-test`, Auto Deploy zapnut — **podle předání ChatGPT**, neověřeno Claude.
- `v8-fly-layer-test` = `da2f665` (PR #5). Proces běží od 2026-11-04 ~19:58 UTC (uptime
  ze `/health`) ⇒ **PR #5 není nasazen**; produkce běží na `bd55352` (shoda s ChatGPT).
- Snapshot 08:39 UTC (run 41996097278): všechny endpointy 200, `paused_bots` FAST/FLY/LEADLAG/TV,
  vše `persistence: postgres`, žádné chyby. Součet P/L 14 PAPER účtů −3 170,34 USDT
  (detail `reports/paper-status-snapshot-20261105.md`).
- Combined ledger: 0 pozic, 0 obchodů, `last_rebalance_day` 2026-11-03 ⇒ nasazení PR #5
  v listopadu nevyvolá obchod navíc.

## Vyřešeno

- `WAIT postgres` u LH-WHALE/LIQUIDITY-LOCAL není chyba (tisk po úspěšném zápisu, `WAIT` = bez
  signálu): `lh_whale.py:215`, `liquidity_local.py:140`.
- Combined replay: NEPROŠEL (`research/combined_selection_replay/RESULTS_20261105.md`).
- 6 zastaralých Whale testů nahrazeno; sada 238/0 (větev `research/combined-selection-replay-20261105`).
- Soupis 110 hypotéz: `reports/hypothesis-inventory-20261105.md`.

## Otevřené úkoly (priorita shora)

1. **Proč se `da2f665` nenasadil** — potřebuje Render (deploy events). BLOKOVÁNO: konektor Render
   `needs_reconnect`. Do té doby sledovat `process_started_utc`.
2. Po souhlasu vlastníka: PR s Whale testy + `tools/` do `v8-fly-layer-test` (spustí deploy PR #5).
3. Combined replay: každý měsíc doplnit nový měsíc čistých dat (`--end` = 1. den dalšího měsíce)
   jako NOVÝ běh se stejným protokolem; evidovat obchody (`trades` v results.json) — runner zatím
   ukládá jen souhrny ⇒ přidat export ledgeru obchodů BEZ změny pravidel (samostatný commit + test).
4. Forward PAPER evidence: týdně souhrn obchodů ELITE V18/V56, Combined, LH-WHALE, LIQUIDITY,
   Swing (počet, P/L, PF) — nutných ≥ 30 nových obchodů na strategii před jakýmkoli závěrem.
5. `test_expired_and_future_signals_never_open` prochází jen formálně (Telegram tok) — navrhnout
   odstranění/přepsání v PR.
6. `render.yaml` neodpovídá skutečné službě (`app_v8_ui` vs `app_v8_fly`) — opravit v PR (nemá vliv,
   pokud Render nepoužívá Blueprint; ověřit přes Render).

## Blokace a co je potřeba od vlastníka

- Render konektor: claude.ai → Settings → Connectors → Render → Reconnect.
- Souhlas k nasazení PR #5 (zatím nedán).
