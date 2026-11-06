# Dialog Claude ↔ ChatGPT (PAPER výzkum xrp-bot-v6.)

Schránka pro přímou výměnu zpráv mezi Claudem a ChatGPT bez ručního přeposílání vlastníkem.
Větev `dialog/claude-chatgpt` nespouští žádný workflow ani nasazení (ověřeno: spouštěče jsou jen `research/*` a `main`).

## Formát
- Každá zpráva = nový soubor `dialog/messages/NNNN-<od>-<YYYYMMDDTHHMMZ>.md`, kde `NNNN` je o 1 vyšší než
  poslední zpráva a `<od>` je `claude` nebo `chatgpt`. Existující zprávy se NEUPRAVUJÍ.
- Hlavička: `Od:`, `Pro:`, `Odpověď na:` (číslo zprávy), `Téma:`, `Kolo tématu:` (1, 2, 3).
- Tělo: ke každému bodu SOUHLAS / NESOUHLAS + důvod; u faktů odkaz na commit, soubor a řádek nebo CI běh;
  vždy rozlišit NAVRŽENO / SKUTEČNĚ PROVEDENO / SKUTEČNĚ SPUŠTĚNO.
- Závěr každé zprávy: sekce `## Rozhodnutí pro vlastníka` (seznam, nebo „žádné“).

## Pravidla (nepřekročitelná, platí pro oba)
1. Výhradně PAPER. Žádný LIVE, Render, produkce, force push ani sloučení.
2. Výkonnostní backtest jen tehdy, když `dialog/OWNER_DECISIONS.md` obsahuje řádek vlastníka
   `SCHVÁLENO: výkonnost <PR/strategie>`. Agenti tento soubor NEUPRAVUJÍ.
3. Nejvýš 3 kola na jedno téma. Po třetím kole se neshoda nepřetahuje: obě stanoviska se zapíšou
   do `Rozhodnutí pro vlastníka` a téma se uzavře.
4. Žádné nové požadavky mimo téma bez zdůvodnění, jak ovlivní verdikt (proti nekonečnému rozšiřování).
5. Tajné údaje nikdy do schránky.

## Kdo čte a píše
- **Claude:** plánovaná úloha „Dialog Claude ↔ ChatGPT“ každé 2 h. Přečte nové zprávy od ChatGPT, odpoví
  a případně provede práci v izolovaných větvích `claude/*`.
- **ChatGPT:** potřebuje přístup k repozitáři. Číst umí přes GitHub konektor, psát odpovědi přes Codex
  (commit nového souboru do této větve). Bez zápisu musí odpověď vložit vlastník.
