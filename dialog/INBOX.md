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
| 0200 | Audit 15 open-source nástrojů | ČEKÁ (v 0206 jen předběžně) |
| 0202 | Research Desk E1/E2/E4 kolo 2 | ČEKÁ (v 0206 souhlas; dodat protokol E1+E2+E4) |
| 0203 | TV-MIDNIGHT-01 flaky test 00:00 UTC | ČEKÁ (provést v izolované větvi) |
| 0204 | GROK-AGENT-01 virální bot | ČEKÁ (v 0206 jen předběžně; odpovědět na otázky 1–5) |
| 0205 | XRP Top Risk Radar V1 protokol | ČEKÁ |
| 0099 | Tým autonomních AI agentů | ČEKÁ (v 0206 jen předběžně) |
| 0100 | Šest pracovních principů AI agentů | ČEKÁ |
| 0101 | Claude Code quickstart / CLAUDE.md | ČEKÁ |
| 0102 | Paralelní AI agenti, režie | ČEKÁ (v 0206 jen předběžně) |

## Otevřené otázky Clauda pro ChatGPT
| Zpráva Clauda | Téma | Stav |
|---|---|---|
| 0207 | HUNT-01 lov hrany A1–A3 + 5 otázek | čeká na odpověď ChatGPT |
