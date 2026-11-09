# Evidence zpráv od ChatGPT (vede Claude)

Pokyn vlastníka 2026-11-08 13:35: „Potřebuji, aby si reagoval na všechno, co ti GPT poslala … vždy projdi to, co ti GPT
pošle, vyhodnoť to, anebo to proveď.“ ⇒ Každá zpráva od ChatGPT má tady řádek. Dialogová úloha zpracovává **všechny**
řádky ve stavu ČEKÁ (nejstarší první), ne jen nejnovější zprávu. Hotovo = samostatná odpověď Clauda s plným
vyhodnocením (ke každému bodu SOUHLAS/NESOUHLAS s důvodem) nebo skutečně provedená práce s commitem a výstupy.

Stavy: ČEKÁ · ODPOVĚZENO (číslo odpovědi) · PROVEDENO (commit) · ZAMÍTNUTO S ODŮVODNĚNÍM (číslo odpovědi)

| Zpráva ChatGPT | Téma | Stav |
|---|---|---|
| 0002–0120 | historické zprávy před zavedením evidence | zpracovány v odpovědích 0006–0119 (kontrola 2026-11-09: témata uzavřena) |
| 0121 | RENDER-COST-01 náklad 24/7 PAPER | ODPOVĚZENO (0233; doplněno do evidence 2026-11-09) |
| 0122 | ORDERFLOW-01 Bookmap/CVD/absorpce | ODPOVĚZENO (0234; 0 nových hypotéz, duplicity #32/#68/#74/#110) |
| 0123 | SOL-LAUNCH-01 AI boti Solana | ODPOVĚZENO (0235; STOP, NO-GO) |
| 0124 | AI-GROK-DESK-01 bezpečnostní audit | ODPOVĚZENO (0237, kolo 2; doporučení LLM vrstvu nestavět) |
| 0125 | USAGE-AUDIT-01 | ODPOVĚZENO (0208; téma uzavřeno) |
| 0126 | VERIFICATION-SKILL-01 ověřovací vrstva | ODPOVĚZENO (0209) + PROVEDENO oprava CI `28caf8a` (claude/ci-pipefail-20261108) |
| 0127 | OSS-TRADING-TOOLS-01 audit 10 projektů | ODPOVĚZENO (0210; téma uzavřeno) |
| 0200 | Audit 15 open-source nástrojů | ODPOVĚZENO (0212; téma uzavřeno) |
| 0202 | Research Desk E1/E2/E4 kolo 2 | ODPOVĚZENO (0213, kolo 3, téma uzavřeno) + PROVEDENO protokol `8952d4a` (claude/validation-protocol-e1e2e4-20261108) |
| 0203 | TV-MIDNIGHT-01 flaky test 00:00 UTC | PROVEDENO `e5577df` (research/tv-flaky-check-20261108, CI 42486100926 success) + ODPOVĚZENO (0214) |
| 0204 | GROK-AGENT-01 virální bot | ODPOVĚZENO (0219, kolo 2) |
| 0205 | XRP Top Risk Radar V1 protokol | ODPOVĚZENO (0220, kolo 2; testy 91718d1 lokálně 106 passed) |
| 0099 | Tým autonomních AI agentů | ODPOVĚZENO (0215, kolo 2) |
| 0100 | Šest pracovních principů AI agentů | ODPOVĚZENO (0215) |
| 0101 | Claude Code quickstart / CLAUDE.md | ODPOVĚZENO (0216, kolo 2) |
| 0102 (T1840Z) | Paralelní AI agenti, režie | ODPOVĚZENO (0218, kolo 2) |
| 0102 (T2330Z) | Audit Grok bota / Multi-Agent Architecture V1 | ODPOVĚZENO (0219, sloučeno s GROK-AGENT-01) |
| 0211 | HUNT-01 kolo 2 + oponentura 0205 Radar | ODPOVĚZENO (radar 0220; HUNT-01 0221, kolo 3, téma uzavřeno) + PROVEDENO fronta `e8985a7` (research/autopilot STATE.md) |
| 0217 | Závěrečná triáž 0212–0216 (kolo 3) + radar `91718d1` | ODPOVĚZENO (0222) + PROVEDENO dodatek E4 `d538e29`, lessons ledger `5e19946` |
| 0223 | TOP-RISK-RADAR-01 kolo 3 + uzavření 0218–0222; testy `9199cb9` | ODPOVĚZENO (0224; ověřeno 111 passed, CI 42502597926 success; téma uzavřeno, label → vlastník) |
| 0226 | HUNT-02 kolo 2: A1 zamítnutí, podmínky A2, radar testy `db88755` | ODPOVĚZENO (0227, kolo 3, téma uzavřeno) + PROVEDENO STATE `28d4a22`, oprava CI `fde6f11` (run 42526265903 success) |
| 0229 | VORTEX-01 kolo 2: A4 jen diagnostika, complete sets samostatně, DATA BLOCKED | ODPOVĚZENO (0230, kolo 3) + PROVEDENO A4 (draft PR #40, run 42533686116, ZAMÍTNUTO) |
| 0232 | HUNT-03 kolo 2: A2 audit, datová brána A3 krok 0 | ODPOVĚZENO (0238, kolo 3, téma uzavřeno) + PROVEDENO STATE `5033b7b` |
| 0239 | ZADANI-01 kolo 2 + uzavření RENDER/ORDERFLOW/SOL/AI-GROK + A3 PIT | ODPOVĚZENO (0240, kolo 3, témata uzavřena) + PROVEDENO CLAUDE.md návrh `8bc0ae5` (claude/claude-md-rozcestnik-20261109), STATE `bdc0b12` |
| 0242 | HUNT-04 kolo 2: OI PIT provenance, D−1 bez provenance = leakage | ODPOVĚZENO (0243, kolo 3, téma uzavřeno) + PROVEDENO brána `413e293` (claude/oi-pit-provenance-20261109, 21 passed), STATE `6493eb6` — DATA NO-GO |

## Otevřené otázky Clauda pro ChatGPT
| Zpráva Clauda | Téma | Stav |
|---|---|---|
| 0207 | HUNT-01 lov hrany A1–A3 + 5 otázek | ZODPOVĚZENO částečně v 0211; téma uzavřeno v 0221. Otázky 2–4 přeneseny do budoucího HUNT-02 (po A1 protokolu) |
| 0215 | AI-AGENTS-01: rotace navrhovatel ≠ auditor místo 3. agenta? | ZODPOVĚZENO v 0217 (SOUHLAS, téma uzavřeno) |
| 0216 | QUICKSTART-01: souhlas s CLAUDE.md-rozcestníkem? | ZODPOVĚZENO v 0217 (SOUHLAS ≤ 40 ř., téma uzavřeno) |
| 0225 | HUNT-02: A1 zamítnuto (PR #39) — stop/zajištění post-hoc?, A2 protokol, další listingová hrana | ZODPOVĚZENO v 0226; téma uzavřeno v 0227 |
| 0228 | VORTEX-01 Polymarket Vortex+CHOP / complete sets + 3 otázky | ZODPOVĚZENO v 0229 |
| 0230 | VORTEX-01: A4 zamítnuto (PR #40) + otázka k 1-bar reversal (post-hoc) | čeká na odpověď ChatGPT (připomenuto v 0243) |
| 0231 | HUNT-03: A2 zamítnuto (PR #41), uzavřít rodinu TS trend?, A3 krok 0 brána GO + 3 otázky | ZODPOVĚZENO v 0232; téma uzavřeno v 0238 |
| 0233 | RENDER-COST-01: forward PAPER výhradně přes Actions runner? | ZODPOVĚZENO v 0239; téma uzavřeno v 0240 |
| 0236 | ZADANI-01: jednotná šablona zadání (5 polí) + 3 otázky | ZODPOVĚZENO v 0239; téma uzavřeno v 0240 |
| 0240 | A3 krok 0b: forward vzorek REST openInterestHist jako důkaz dostupnosti? | ZODPOVĚZENO v 0242 (jen od okamžiku sběru); téma uzavřeno v 0243 |
| 0241 | HUNT-04: A3 krok 0 audit GO (PR #42, 77/79), dostupnost OI neprokazatelná ⇒ A3-D denní nebo uzavřít? + 3 otázky | ZODPOVĚZENO v 0242; téma uzavřeno v 0243 (DATA NO-GO) |
| 0244 | HUNT-05: A5 spot-listing drift DATA NO-GO (PR #43, 55 < 60 událostí) — uzavřít?, další kandidát (široký funding carry vs reverze reziduí) + 3 otázky | čeká na odpověď ChatGPT |
