# Audit produkčních PAPER botů — 2026-11-06 13:50 SEČ

Jen čtení (SELECT přes Render konektor, kód `v8-fly-layer-test` @ `edaa938`). Nic se nezměnilo.
Výhradně PAPER. Návrhy níže čekají na souhlas vlastníka.

## Běžící boty (smyčka aktivní, otevírají obchody)

| bot | obchodů | čistý P/L | PF | výhry | poplatky | posl. 30 dní | poslední obchod | návrh |
|---|---|---|---|---|---|---|---|---|
| BLUE WHALE mirror (`blue_whale_trades`) | 10 | −727,70 | – (0 výher) | 0 % | – | 6 obch. / −630,19 | 2026-11-06 | **POZASTAVIT** nové vstupy |
| BEST-OF (`bestof_trades`, vč. dupl. 129) | 132 | −390,85 | 0,56 | 23,5 % | 239,16 | 102 obch. / −407,35 | 2026-11-06 | **POZASTAVIT** a předělat (poplatky = 61 % ztráty, 3,4 obchodu/den) |
| SWING supertrend_4h | 7 | −212,55 | – (0 výher) | 0 % | 23,88 | 7 obch. | 2026-11-03 | **POZASTAVIT** |
| SWING aroon_1h_4h | 2 | −100,75 | – | 0 % | 11,97 | 0 | 2026-10-07 | pozastavit spolu se supertrend (malý vzorek) |
| LIQUIDITY v2 | 21 | −49,77 | – | 28,6 % | 73,30 | 21 obch. | 2026-11-05 | ponechat, vyhodnotit po 50 obchodech |
| LH-WHALE | 2 | +17,09 | – | 50 % | 6,97 | 2 obch. | 2026-10-24 | ponechat (málo dat) |
| ELITE V18 / V56 (forward) | 0 | 0 | – | – | 0 | 0 | – | ponechat (zatím žádný signál) |
| COMBINED_BEST_SIGNALS_V1 | 0 | 0 | – | – | 0 | 0 | – | ponechat (0 kandidátů) |
| NEWS PAPER | 0 | 0 | – | – | 0 | 0 | – | ponechat nebo vypnout — nikdy neobchodoval |

## Už pozastavené (`PAUSED_BOTS` = FLY, FAST, LEADLAG, TV)

| bot | obchodů | čistý P/L | PF | poslední obchod |
|---|---|---|---|---|
| FLY (`v8fixed_trades`, bez 3 vyloučených) | 287 | −821,80 | 0,56 | 2026-10-11 |
| TV consensus | 112 | −436,87 | 0,45 | 2026-10-11 |
| FAST scalp | 104 | −413,46 | 0,13 | 2026-10-05 |
| LEADLAG | 8 | −50,44 | 0,05 | 2025-09-25 → 2026-09-25 |

Návrh: nechat pozastavené; při příští úpravě kódu jejich smyčky vůbec nespouštět (teď běží naprázdno).

## Historické verze (neběží od září/října, jen tabulky)
v6 −627,43 · v7 −317,05 · v71 −60,00 · v8 −226,03 · v81 −1 283,41 · v81fix −56,55 · v81breakout −19,22 ·
v9 −22,58 · candle_v8 −178,22 · **candle_v8_fixed +93,17 (PF 1,11, 62 obchodů — jediný kladný)** · trades v1 −303,87.
Tabulky zabírají dohromady < 1 MB ⇒ mazání nic neušetří; ponechat jako historii (pravidlo: nemazat).
`candle_v8_fixed` stojí za samostatný výzkum (proč skončil 2026-10-02, zda by obstál po nákladech na delším vzorku).

## Data a náklady
- DB 1 GB, použito ~210 MB. **193 MB (92 %) = `research_market_samples`** (sběr 1×/min od 2026-10-17, ~10 MB/den).
  Kolektor má strop 256 MB ⇒ zastaví se sám zhruba **2026-11-12**; DB se tedy nezaplní. Pokud vzorky nikdo
  nepoužívá, sběr vypnout hned; pokud ano, exportovat do komprimovaných souborů a pak promazat (jen se souhlasem).
- `blue_whale_state` 4 MB = jeden řádek, který roste (historie v JSON) — pozastavení WHALE to zastaví.
- **Peníze:** Render účtuje službu a databázi paušálně podle plánu, ne podle počtu botů. Vypnutí botů samo
  nic neušetří; ušetřit lze jen změnou plánu. Služba bere ~165 MB z 512 MB RAM a ~3 % CPU — menší placený plán
  nemá smysl a free tier usíná (rozbil by 24/7). Hlavní přínos vypnutí = méně ztrátových PAPER obchodů a čistší data.

## Shrnutí
Všechny aktivní boty se skutečným vzorkem obchodů jsou po nákladech ve ztrátě. Součet všech PAPER účtů ≈ −6 000 USDT
(vč. historických verzí). Doporučení: pozastavit BLUE WHALE, BEST-OF a oba SWING; ponechat LIQUIDITY, LH-WHALE,
ELITE, COMBINED jako forward testy; rozhodnout o sběru `research_market_samples`.
