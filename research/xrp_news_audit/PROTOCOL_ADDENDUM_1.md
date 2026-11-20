# A6 krok 0 — dodatek 1: brána G1 ve dvou oddělených verzích (2026-11-09, po datech)

Na žádost oponentury (dialog 0252 §1). Dodatek NEMĚNÍ verdikt ani výsledky; jen odděluje původní a opravené pravidlo.

## G1 v1 (platná pro tento audit, `625aa88`, PROTOCOL.md ř. 26)
- Text: odhad titulků jen-XRP |s| ≥ 2 ≥ 300 (2020–24) a ≥ 100 (2025–26), Z1 „odhadem“.
- Chyba: „odhad“ nebyl definován; bodový odhad z 2 zásahů (2020–24) extrapolovaný ze vzorku 243/~245 tis. souborů
  projde i při 95% intervalu Poisson 26–5 570. Brána tak nerozlišuje „dost dat“ od „neznámo“.
- Výsledek v1: Z1 formálně ✓ (bodový odhad 1 974 / 3 092). **Nepřijato jako GO** (AUDIT.md `ecd3965`) — rozhodnuto
  ve směru přísnosti, ne zpětnou změnou pravidla.

## G1 v2 (NAVRŽENO jen pro budoucí audity A6, neaplikuje se zpětně)
- Odhad počtu se posuzuje **dolní mezí 95% intervalu** (Poisson, extrapolace podle podílu vzorku) ≥ 300 / ≥ 100.
- Při < 10 zásazích ve vzorku je G1 automaticky „nerozhodnuto“ ⇒ nutné zvětšit vzorek, ne rozhodovat.
- Pro tento audit by v2 dala G1 ✗ (dolní mez 26 ≪ 300) — výsledek je stejný jako verdikt: DATA NO-GO.

## Stav A6 po dialogu 0250/0252
- A6-S historicky: DATA NO-GO. Forward RSS sběr: NEspouštět (bez jiného konzumenta a zmrazených kritérií).
- A6-F (zprávy jako risk filtr): neimplementovat bez PIT feedu a bid/ask/hloubky; případně nahradit
  fail-closed market-quality bránou (ARCH-RISK-01 audit 4.2), která zprávy nepotřebuje.
