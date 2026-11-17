# A4 VORTEX+CHOP NA 5/15 MIN BTC — předregistrovaný DIAGNOSTICKÝ protokol

Stav: zapsáno a commitnuto 2026-11-09 (autopilot běh #38) PŘED kódem a PŘED stažením dat. Po prvním
výsledku se nic neladí. Výhradně PAPER výzkum, veřejná data, žádné klíče, žádné objednávky, žádný Polymarket účet.

## Původ a dohoda
- Podnět vlastníka 2026-11-08 23:15 SEČ (virální příspěvek „Quant Vortex Structure“, Polymarket BTC Up/Down 5/15 min).
- Dialog 0228 → 0229 (ChatGPT): A4 je jen **diagnostika směrového indikátoru**; arbitrážní PnL complete-setů
  (UP+DOWN < 1 $) se jako důkaz nesmí použít. Complete-set arbitráž = samostatná hypotéza, bez PIT order booku
  Polymarketu verdikt **DATA BLOCKED** (zde se netestuje).
- Rodina: denní/hodinová TA na BTC zamítnuta mnohokrát (PR #36: 0/18 nákladově limitovaných). Odlišnost: 5/15min
  horizont a binární výplata (náklad = cena kontraktu, ne fee+skluz perpu). Proto přísná brána P0 (hrubá hrana ≥ 3× náklad).

## Data (veřejná, Binance Vision, přes GitHub Actions)
- Spot `BTCUSDT` klines 5m a 15m, měsíční archivy 2020-01 … 2026-10 (`data/spot/monthly/klines`).
- USDT-M perp `BTCUSDT` klines 5m a 15m, stejné měsíce (`data/futures/um/monthly/klines`) — jen pro stopu F.
- Každý archiv: SHA-256 proti `.CHECKSUM`; manifest v `data_source.json`. Chybějící/MISMATCH archiv ⇒ běh skončí chybou
  (žádné tiché vynechání). Časové značky v µs (spot od 2025) převést na ms.
- Omezení: Polymarket rozhoduje podle Chainlink BTC/USD, ne podle Binance; na 5/15 min se směr může lišit u svíček
  s malým pohybem. Proto se hit rate uvádí i bez svíček s |close/open − 1| < 0,02 % (informativně, ne pro verdikt).

## Signál (pevně, bez ladění mimo mřížku)
Na barech časového rámce TF ∈ {5m, 15m}, po uzavření baru t (jen data ≤ t):
- TR_t = max(H_t, C_{t−1}) − min(L_t, C_{t−1}); VM+_t = |H_t − L_{t−1}|; VM−_t = |L_t − H_{t−1}|.
- VI+ = ΣVM+ / ΣTR, VI− = ΣVM− / ΣTR přes posledních n barů.
- CHOP = 100 · log10( ΣTR(n) / (max H(n) − min L(n)) ) / log10(n).
- Vstup jen pokud CHOP < práh. Směr: VI+ > VI− ⇒ UP, VI− > VI+ ⇒ DOWN, rovnost ⇒ žádný signál.
- Předpovídá se bar t+1: UP vyhrává, když C_{t+1} ≥ O_{t+1} (pravidlo Polymarketu „Up“ při ≥), jinak DOWN.
- Mřížka: n ∈ {14, 28} × práh ∈ {38,2; 50} × TF ∈ {5m, 15m} = **8 buněk ⇒ N = 202 + 8 = 210**.
  (STATE.md uvádí mřížku 4 na rámec; oba rámce jsou samostatné trhy ⇒ započteno 8.)

## Období (chronologicky, bez překryvu)
- Ladění 2020-01-01 … 2022-12-31; validace 2023-01-01 … 2024-12-31; závěrečné 2025-01-01 … 2026-10-31.
- Závěrečné období je opotřebované a režimově známé ⇒ smí jen ZAMÍTNOUT.
- Výběr: pro každý TF zvolit v LADĚNÍ buňku s nejvyšším z-skóre hit rate proti 0,5 (min. 1 000 signálů). Všechny buňky
  se reportují ve všech obdobích; verdikt jen podle zvolené buňky každého TF.

## Stopa P — binární kontrakt (proxy Polymarket Up/Down)
- Sázka na začátku okna t+1 na předpovězenou stranu za cenu q = 0,50 + k·0,01, k ∈ {1, 2, 3} (náklady ×1/×2/×3:
  spread + fee, oficiální fee tabulka NEOVĚŘENA ⇒ citlivost). Výplata 1 při výhře. Výnos na 1 $ = 1[výhra]/q − 1.
- Optimistický předpoklad: cena na začátku okna ≈ 0,50 (bez informace trhu). Skutečná vykonatelnost = DATA BLOCKED.
- Break-even hit rate = q (×1 0,51; ×2 0,52; ×3 0,53).
- Naivní srovnání na STEJNÝCH barech: pokračování předchozího baru, obrat předchozího baru, vždy UP.

## Stopa F — USDT-M perp (realizovatelná alternativa)
- Pozice ve směru signálu za open baru t+1, výstup za close t+1, 1× notional 10 000 USDT, bez skládání.
- Náklad za obchod (round-trip): fee 0,095 % + skluz 0,02 %, ×1/×2/×3. Funding zanedbán (držení ≤ 15 min, většinou
  bez settlementu) — uvedeno jako omezení.
- Benchmark: B&H BTC perp stejného období (výnos, denní Sharpe, max DD).

## Brány (vše pro zvolenou buňku; selhání kterékoli ⇒ ZAMÍTNUTO)
- P0 Ladění: hit rate − 0,5 ≥ 3 × 0,01 (hrubá hrana ≥ 3× náklad ×1), tj. hit rate ≥ 0,53.
- P1 Validace: Wilsonův 95% dolní odhad hit rate > 0,52 (break-even ×2).
- P2 Validace: hit rate ≥ nejlepší naivní srovnání na stejných barech + 1 p. b.
- P3 Validace, stopa P ×2: denní řada výnosů (fixní sázka 1 $ na signál) ⇒ DSR ≥ 0,95 s N = 210, V[SR] = 0,5/365.
- P4 Závěrečné ×2: hit rate > 0,52 (jen zamítací).
- Stopa F (informativně, kandidát jen pokud projde i P): validace ×2 čistý zisk > 0, PF > 1,2, denní Sharpe > B&H;
  závěrečné ×2 čistý zisk > 0.
- I při průchodu: max. „diagnostika prošla → forward PAPER sběr ≥ 60–90 dní“; nikdy „zisková strategie“.

## Výstupy
`trades.csv.gz` (každý signál ZVOLENÉ buňky každého TF: tf, cell, období, čas, směr, výsledek, perp výnos; ostatní buňky jen souhrny — velikost), `results.json`, `RESULTS.md`,
`data_source.json`; `verify.py` nezávisle přepočte hit rate a součty stopy F z `trades.csv.gz`.
