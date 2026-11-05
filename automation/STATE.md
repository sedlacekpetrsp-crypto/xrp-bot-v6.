# Autopilot STATE — přepisuje se každým během

Poslední aktualizace: 2026-11-05 08:46 UTC (založení + autopilot běh #1, run 41996806445).

Plánovaná úloha: `trig_01PCaCadnJSZo5XYuLEdH8uR`, cron `44 */3 * * *` UTC, navazuje v session
`session_01SUMe5gCQBc55fV2C6FFoZu`. Vypnout/změnit: claude.ai → plánované úlohy, nebo požádat Claude.

## Produkce (poslední známé hodnoty)

- Služba `xrp-fly-whale-24-7` (`srv-dang770ae00c73em1sm0`), start `uvicorn app_v8_fly:app`,
  větev `v8-fly-layer-test`. Auto Deploy v praxi nereaguje na merge (merge PR #5/#6 nespustily deploy) ⇒ deploy ručně.
- `v8-fly-layer-test` = `edaa938` (PR #5 + #6 + #7). **Nasazeno ručně**, proces běží od
  2026-11-05 09:13:58 UTC. Historie: `bd55352` (do 09:01) → `9b41f6d` (09:01–09:13) → `edaa938`.
- Autopilot kontroluje i značku nasazeného kódu v `/` (`code_markers`).
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

1. VYŘEŠENO 2026-11-05 09:01 UTC: vlastník ručně nasadil `9b41f6d` (Render Manual Deploy, 1 min 13 s,
   úspěšný). Restart potvrzen (`process_started_utc` 09:01:52). Příčina: předchozí deploy měl
   Trigger „API“ a merge PR #5/#6 auto deploy nespustily ⇒ Auto Deploy pravděpodobně vypnutý
   (neověřeno v nastavení). **Každá další změna v `v8-fly-layer-test` vyžaduje ruční deploy.**
2. HOTOVO: PR #6 (Whale testy) sloučen 08:48 UTC a nasazen spolu s PR #5.
3. Combined replay: každý měsíc doplnit nový měsíc čistých dat (`--end` = 1. den dalšího měsíce)
   jako NOVÝ běh se stejným protokolem; evidovat obchody (`trades` v results.json) — runner zatím
   ukládá jen souhrny ⇒ přidat export ledgeru obchodů BEZ změny pravidel (samostatný commit + test).
4. Forward PAPER evidence: týdně souhrn obchodů ELITE V18/V56, Combined, LH-WHALE, LIQUIDITY,
   Swing (počet, P/L, PF) — nutných ≥ 30 nových obchodů na strategii před jakýmkoli závěrem.
5. `test_expired_and_future_signals_never_open` prochází jen formálně (Telegram tok) — navrhnout
   odstranění/přepsání v PR.
6. `render.yaml` neodpovídá skutečné službě (`app_v8_ui` vs `app_v8_fly`) — opravit v PR (nemá vliv,
   pokud Render nepoužívá Blueprint; ověřit přes Render).

## Čeká na vlastníka

- Žádné čekající PR. PR #7 (`edaa938`, Whale trendline 0,1 % / 35 % / 0,24 %) nasazen ručně,
  restart 2026-11-05 09:13:58 UTC, dashboard potvrzuje „cílové riziko 0,1 %“.

## Blokace a co je potřeba od vlastníka

- Render konektor: claude.ai → Settings → Connectors → Render → Reconnect.
- Nasazení PR #5/#6: schváleno a provedeno (09:01 UTC).
