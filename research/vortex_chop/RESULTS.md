# A4 VORTEX+CHOP 5/15m BTC — výsledky (run 42533686116, protokol `0c506a1`, kód `346da07`)

**Verdikt: ZAMÍTNUTO** (oba rámce, všechny brány P0–P4 selhaly). Žádná varianta netestovat bez nové předregistrace.

Data: Binance Vision BTCUSDT spot + USDT-M perp 5m/15m, 2020-01…2026-10, 328 archivů, SHA-256 = `.CHECKSUM` 100 %.
Nezávislý přepočet z `trades.csv.gz`: 6/6 období shoda, 0 neshod. N = 210 (202 + 8 buněk).

## Zvolené buňky (výběr v ladění podle z-skóre) — stopa P (binární kontrakt, cena 0,50 + k·1 ¢)

| TF / buňka | období | signálů | hit rate | Wilson 95% dolní | nejlepší naivní | P ×2 (součet na 1 $ sázky) |
|---|---|---:|---:|---:|---:|---:|
| 5m n28 CHOP<38,2 | ladění | 21 764 | 48,66 % | 48,00 % | obrat 54,23 % | −1 397 |
| | validace | 28 292 | 47,67 % | 47,09 % | obrat 51,72 % | −2 357 |
| | závěrečné | 28 250 | 48,23 % | 47,65 % | obrat 51,34 % | −2 046 |
| 15m n28 CHOP<38,2 | ladění | 7 754 | 50,28 % | 49,17 % | obrat 53,70 % | −256 |
| | validace | 7 091 | 49,33 % | 48,17 % | obrat 52,69 % | −364 |
| | závěrečné | 6 694 | 49,10 % | 47,91 % | obrat 52,38 % | −373 |

Break-even ×1/×2/×3 = 51/52/53 %. DSR validace ×2: 5m 0,000, 15m 0,000 (denní Sharpe −0,56 / −0,23).
Všech 8 buněk ve všech obdobích má hit rate 46,8–50,3 % — Vortex+CHOP předpovídá směr další svíčky **hůř než mince**.
Bez svíček s pohybem < 0,02 % (rozdíl Chainlink vs. Binance) se obraz nemění (5m val 47,1 %, 15m val 49,3 %).

## Stopa F (perp, 10 000 USDT/obchod, round-trip 0,115 % ×1)
Hrubá hrana na obchod −0,3 až +1,4 bp vs. náklad 11,5 bp ×1 ⇒ ztráta ve všech obdobích (validace ×2: 5m PF 0,06, 15m PF 0,15).
B&H BTC perp validace +466 %, závěrečné −17 %. (Max DD stopy F je bez skládání a equity klesá pod nulu ⇒ neinformativní.)

## Postřeh (post-hoc, NETESTOVÁNO, NIC NEPROHLAŠOVAT)
Naivní „obrat předchozí svíčky“ má na stejných barech 51–54 %. Jde nejspíš o krátkodobý mean-reversion/bid-ask bounce
OHLC svíček; na perpu je pohyb 5/15 min menší než náklad. U binárního kontraktu by to byla nová hypotéza — jen s novou
předregistrací, daty Chainlink/Polymarket a forward vzorkem po 2026-11-09. Odesláno ChatGPT k oponentuře (dialog 0230).

## Závěr pro vlastníka
Tvrzený výsledek virálního bota nelze vysvětlit Vortex+CHOP signálem; souhlasí to s hypotézou complete-set arbitráže
(dialog 0228/0229), která bez PIT order booku Polymarketu zůstává DATA BLOCKED.
