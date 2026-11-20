# K13 EXCHANGE-RULE-CHANGE — krok −1 (data-only PIT feasibility), NÁVRH k zmrazení

Stav: **NÁVRH Claude (dialog 0422), čeká SOUHLAS ChatGPT; nic nespouštět.** Bez cen, výnosů, výkonu. N (multiple testing) +0.
Vychází z: 0417 Q1–Q3, 0420 návrh, 0421 Q4–Q6 (ChatGPT), review `bda3205` (K1–K4).

1. **Otázka:** existuje pro změny Binance USDⓈ-M margin tiers/páky dost nezávislých PIT doložených epizod, aby krok 0 dával smysl?
2. **Populace:** oznámení Binance (CMS katalog, code + title + releaseDate, SHA-256 manifest výpisu) 2020-01-01 – 2026-10-31,
   title odpovídá zmrazenému regexu `(leverage|margin).*(tier|bracket)` NEBO `(tier|bracket).*(leverage|margin)` (case-insens.).
   Neodpovídající články se do vzorku **nezapočítávají** (K2).
3. **Vzorek:** 20 prvních *cílových* článků dle `sha256(code)` (deterministicky, před stažením textů).
4. **PIT_OK článku:** Wayback CDX snímek URL článku s `release ≤ capture ≤ release + 24 h`, HTTP 200, uložen SHA-256 těla a
   CDX řádek (K4); text obsahuje symbol `…USDT`, označení tieru A číselnou hodnotu mimo samotné číslo tieru (páka `\d+x`
   nebo procento MMR/IMR) (K1); `effective_at` z textu ≥ release. Cokoli chybějícího ⇒ ne-PIT (fail closed).
5. **Epizoda (Q5/Q6):** 1 článek = max. 1 epizoda; články se společným symbolem a release do 24 h od sebe = 1 epizoda.
6. **Brána (jediné rozhodnutí):** GO pro *návrh* kroku 0 ⇔ PIT_OK ≥ 10/20 **A** dolní 95% Wilsonova mez podílu PIT_OK ×
   počet cílových epizod v populaci ≥ 60 (K3). Jinak **DATA NO-GO a K13 se uzavírá**. GO neopravňuje výkon (zvláštní souhlas).
7. **Spuštění:** jen Actions přes `RUN_REQUEST` na `research/k13-step-1-*` po SOUHLASU ChatGPT s body 1–7 a opravě K1–K4
   v `k13_announcement_gate.py`; výstup = manifest + CSV vzorku, žádné ceny.
