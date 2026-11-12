# Delta-neutrální funding carry BTC/ETH — výsledky (PAPER výzkum)

Protokol `research/funding_carry/PROTOCOL.md` (commit `86fe510` před kódem; dodatky 1–2 jen k datům, před výsledky).
Backtest: GitHub Actions run 42209504198, Binance Vision 492 archivů (spot 1d, USDT-M perp 1d, fundingRate) se SHA-256
v `data_source.json`, 0 chybějících, 0 doplněných dnů. Závěrečný test končí 2026-10-27 (perp 1d 2026-10-28 chybí).

**Verdikt: ZAMÍTNUTO** — stopa A ✘ A2 (6 obchodů < 30), stopa B ✘ B5 (validace + závěrečný = 11 < 20).
Ostatní kritéria A i B a všechny testy robustnosti prošly. Ekonomicky navíc: v závěrečném testu výnos ×2 jen +0,22 %
za 22 měsíců, tj. **pod úrokem z hotovosti** (model počítá hotovost i marži s 0 % úrokem) ⇒ výhoda v letech 2025–26 zmizela.

Výběr na ladění ×1 (koš 10 000 USD): H=10 % +2 365,77 (10 obch.), H=20 % +2 263,06 ⇒ **zvoleno H = 10 % p.a.**
(info: H=5 % +2 361,95, H=30 % +2 184,45).

| Období | Náklady | Výnos | Sharpe* | Max DD | Obchodů | PF | Bez top 3 | Funding | Náklady USD |
|---|---|---|---|---|---|---|---|---|---|
| Ladění 2020-09…2022-12 | ×1 | +23,66 % | 8,49 | 0,27 % | 10 | 105 | +190,36 | 2 538,55 | 164,95 |
| Validace 2023–2024 | ×1 | +9,70 % | 11,03 | 0,25 % | 6 | ∞ | +242,39 | 1 059,01 | 90,33 |
| Validace | ×2 | +8,76 % | 8,14 | 0,50 % | 6 | ∞ | +199,29 | 1 054,77 | 179,92 |
| Validace | ×3 | +7,83 % | 5,85 | 0,75 % | 6 | ∞ | +156,63 | 1 050,55 | 268,76 |
| Závěrečný 2025-01…2026-10-27 | ×1 | +0,78 % | 2,70 | 0,14 % | 5 | ∞ | +9,96 | 131,93 | 55,29 |
| Závěrečný | ×2 | +0,22 % | 0,45 | 0,31 % | 5 | 2,94 | −11,49 | 131,57 | 110,25 |
| Závěrečný | ×3 | −0,33 % | −0,45 | 0,48 % | 5 | 0,21 | −32,80 | 131,21 | 164,90 |

B&H 50/50 BTC/ETH ×1: ladění +108,4 % (Sharpe 0,80, DD 76,9 %), validace +321,4 % (1,71, 34,0 %), závěrečný −21,7 % (0,00, 60,0 %).
*Sharpe z denních výnosů včetně dnů bez pozice (0 %) — u nízkovolatilní strategie je číslo vysoké a s B&H srovnatelné jen orientačně.

Robustnost: DSR validace ×1 = 1,00 (N = 140, V[SR] = 0,5 p.a.; SR0 0,098/den, SR 0,577/den, skew 1,14, kurt 13,9);
soused H=5 % validace ×2 +963,70 > 0; walk-forward ×2: 2021 +1 893,61, 2022 −57,36, 2023 +297,71, 2024 +529,98 ⇒ 3/4 kladné.
Likvidace 0. Kontrola: trades.csv (122 řádků) vs results.json — 19 bloků, 0 neshod (počet i součet net_pnl).

Poučení: funding carry je reálný, ale jeho výnos kopíruje páku trhu (2021: ~38 % p.a. na koš; 2023–24 ~4,5 % p.a.;
2025–26 < 0,5 % p.a.) a při spot poplatcích 0,095 % na obě nohy ho ×3 náklady smažou. Nízký obrat (5–6 epizod za 2 roky)
nesplní počet obchodů. Případná další verze (nová hypotéza, ne ladění): přidat úrok z hotovosti/marže jako měřítko
(excess return), levnější nohy (maker/perp poplatky) a průřez více aktiv kvůli počtu epizod.
