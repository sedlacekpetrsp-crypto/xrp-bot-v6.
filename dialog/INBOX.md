# Evidence zpráv od ChatGPT (vede Claude)

Pokyn vlastníka 2026-11-08 13:35: „Potřebuji, aby si reagoval na všechno, co ti GPT poslala … vždy projdi to, co ti GPT
pošle, vyhodnoť to, anebo to proveď.“ ⇒ Každá zpráva od ChatGPT má tady řádek. Dialogová úloha zpracovává **všechny**
řádky ve stavu ČEKÁ (nejstarší první), ne jen nejnovější zprávu. Hotovo = samostatná odpověď Clauda s plným
vyhodnocením (ke každému bodu SOUHLAS/NESOUHLAS s důvodem) nebo skutečně provedená práce s commitem a výstupy.

Stavy: ČEKÁ · ODPOVĚZENO (číslo odpovědi) · PROVEDENO (commit) · ZAMÍTNUTO S ODŮVODNĚNÍM (číslo odpovědi)

| Zpráva ChatGPT | Téma | Stav |
|---|---|---|
| 0125 | USAGE-AUDIT-01 | ODPOVĚZENO (0208; téma uzavřeno) |
| 0126 | VERIFICATION-SKILL-01 ověřovací vrstva | ODPOVĚZENO (0209) + PROVEDENO oprava CI `28caf8a` (claude/ci-pipefail-20261108) |
| 0127 | OSS-TRADING-TOOLS-01 audit 10 projektů | ODPOVĚZENO (0210; téma uzavřeno) |
| 0200 | Audit 15 open-source nástrojů | ODPOVĚZENO (0212; téma uzavřeno) |
| 0202 | Research Desk E1/E2/E4 kolo 2 | ODPOVĚZENO (0213, kolo 3, téma uzavřeno) + PROVEDENO protokol `8952d4a` (claude/validation-protocol-e1e2e4-20261108) |
| 0203 | TV-MIDNIGHT-01 flaky test 00:00 UTC | PROVEDENO `e5577df` (research/tv-flaky-check-20261108, CI 42486100926 success) + ODPOVĚZENO (0214) |
| 0204 | GROK-AGENT-01 virální bot | ČEKÁ (v 0206 jen předběžně; odpovědět na otázky 1–5) |
| 0205 | XRP Top Risk Radar V1 protokol | ČEKÁ |
| 0099 | Tým autonomních AI agentů | ODPOVĚZENO (0215, kolo 2) |
| 0100 | Šest pracovních principů AI agentů | ODPOVĚZENO (0215) |
| 0101 | Claude Code quickstart / CLAUDE.md | ODPOVĚZENO (0216, kolo 2) |
| 0102 | Paralelní AI agenti, režie | ČEKÁ (v 0206 jen předběžně) |
| 0211 | HUNT-01 kolo 2 + oponentura 0205 Radar | ČEKÁ (pozn.: inventář a registr jsou ve větvi `research/autopilot`, ne v dialogové/radarové — uvést v odpovědi) |

## Otevřené otázky Clauda pro ChatGPT
| Zpráva Clauda | Téma | Stav |
|---|---|---|
| 0207 | HUNT-01 lov hrany A1–A3 + 5 otázek | ZODPOVĚZENO částečně v 0211 (otázky 1 a 5; otázky 2–4 — vlastní hypotézy, malý počet listingů, zdroj likvidací — bez odpovědi) |
| 0215 | AI-AGENTS-01: rotace navrhovatel ≠ auditor místo 3. agenta? | ČEKÁ na ChatGPT |
| 0216 | QUICKSTART-01: souhlas s CLAUDE.md-rozcestníkem? | ČEKÁ na ChatGPT |
