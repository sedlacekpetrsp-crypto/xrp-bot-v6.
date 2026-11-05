# Stav PAPER botů — snapshot 2026-11-05 08:39 UTC

Zdroj: veřejné stavové endpointy služby `https://xrp-fly-whale-24-7.onrender.com`, čtené
pouze GET z GitHub Actions (run `41996097278`, job `127139517325`, workflow
`.github/workflows/paper-status-snapshot.yml`, bez tajných údajů). Všechny endpointy HTTP 200.
Úplné odpovědi jsou v logu běhu: https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./actions/runs/41996097278
Render API, logy služby ani přímé připojení k DB tato session nemá — data níže jsou to,
co vrací aplikace.

## Nasazení

- `/health`: `status ok`, `uptime_seconds 45649` → proces běží od 2026-11-04 ~19:58 UTC.
  Shoduje se s deployem `bd55352` uvedeným v předání od ChatGPT (19:58 UTC). Restart po merge
  PR #5 (07:40 UTC 5. 11.) neproběhl → **PR #5 není nasazen** (nepřímý důkaz z uptime).
- `paused_bots`: FAST, FLY, LEADLAG, TV — pauza drží.

## PAPER účty (start 10 000 každý)

| Bot | Stav | Obchody | Čisté P/L | Poslední cyklus (UTC) | Persistence |
|---|---|---:|---:|---|---|
| FLY | pauza | 287 | −821,80 (PF 0,558) | 08:38:51 | postgres |
| WHALE | běží | — | −718,29 | 08:38:58 | postgres |
| FAST | pauza | 104 | −413,46 | 08:38:49 | postgres |
| TV | pauza | 112 | −436,87 | 08:38:51 | postgres |
| BEST-OF | běží, 2 otevřené (ETH EMA4h, XRP BREAKOUT) | 127 | −372,68 (realizováno) | 08:39:00 | postgres |
| LEADLAG | pauza | — | −50,44 | 08:38:49 | postgres |
| LH-WHALE | běží, WAIT | 2 | +17,09 | 08:38:56 | postgres |
| LIQUIDITY V2 | běží, WAIT | 19 (win 26 %) | −60,60 | 08:39:00 | postgres |
| AROON 1h | běží | 2 (win 0 %) | −100,75 | 08:39:00 | postgres |
| SUPERTREND 4h | běží | 7 (win 0 %) | −212,55 | 08:39:00 | postgres |
| NEWS_LONG | běží, čeká na zprávu | 0 | 0,00 | 08:39:00 | postgres |
| ELITE V18 / V56 | běží (start 4. 11. 19:31) | 0 / 0 | 0,00 / 0,00 | last_tick 08:38:50 | postgres |
| COMBINED | RUNNING, 0 kandidátů | 0 | 0,00 | updated 08:31:31 | postgres |

Součet čistého P/L všech 14 účtů: **−3 170,34 USDT** (pouze BEST-OF má otevřené pozice,
jejichž nerealizovaný výsledek není započten). Kladný je jen LH-WHALE (+17,09, 2 obchody).
Žádné `last_error`/`persistence_error`; všechny účty hlásí `persistence: postgres`.

## Kompatibilita produkčního Combined ledgeru s PR #5

Ledger z `/combined/status` (čte `combined_best_paper_state` z PostgreSQL): hotovost 10 000,
0 pozic, 0 obchodů, `last_rebalance_day` 2026-11-03. Analýza `tools/combined_ledger_precheck.analyse`:

- po nasazení PR #5 v listopadu: žádný rebalance navíc, změna nerealizovaného P/L 0 (bez pozic);
- 2026-12-01: nový kód rebalancuje 1. 12., starý by rebalancoval až 2. 12. — to je zamýšlená
  oprava časování, nikoli chyba.

**Oprava dřívějšího tvrzení:** Combined po spuštění žádné pozice neotevřel (0 kandidátů);
tvrzení o „pozicích otevřených uprostřed měsíce“ bylo odvozené z kódu a neplatí.
