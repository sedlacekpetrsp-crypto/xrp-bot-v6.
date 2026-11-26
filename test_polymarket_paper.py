import json

import pytest

from polymarket_paper.collector import Runner, market_from_event, window_slug
from polymarket_paper.core import (DOWN, UP, InstantPair, LegIn, Position,
                                   buy_cost, parse_asks, taker_fee)
from polymarket_paper.report import summarize


def book(*asks):
    # Polymarket vrací asky sestupně (nejlevnější na konci)
    return {"asks": [{"price": str(p), "size": str(s)} for p, s in sorted(asks, reverse=True)]}


def test_fee_matches_docs_example():
    assert taker_fee(100, 0.5, 0.07) == pytest.approx(1.75)


def test_parse_and_walk_book():
    asks = parse_asks(book((0.99, 100), (0.40, 5), (0.42, 10)))
    assert asks[0] == (0.40, 5)
    total, avg = buy_cost(asks, 10, 0.0)
    assert total == pytest.approx(5 * 0.40 + 5 * 0.42)
    assert buy_cost(parse_asks(book((0.4, 3))), 10, 0.0) is None


def test_instant_pair_only_when_edge_after_fees():
    s = InstantPair(clip=10, min_edge=0.01)
    pos = Position()
    cheap = s.on_book(pos, parse_asks(book((0.48, 50))), parse_asks(book((0.49, 50))), 0.01)
    assert [x[0] for x in cheap] == [UP, DOWN]
    # 0.50 + 0.50 = 1.00 -> žádný obchod
    assert s.on_book(pos, parse_asks(book((0.50, 50))), parse_asks(book((0.50, 50))), 0.0) == []
    # 0.49 + 0.49 je pod 1, ale s poplatkem 0.07 už edge nestačí
    assert s.on_book(pos, parse_asks(book((0.49, 50))), parse_asks(book((0.495, 50))), 0.07) == []


def test_leg_in_buys_cheap_then_completes_pair():
    s = LegIn(clip=10, cheap=0.45, target_pair_cost=0.97, max_imbalance=10)
    pos = Position()
    o = s.on_book(pos, parse_asks(book((0.40, 50))), parse_asks(book((0.62, 50))), 0.0)
    assert o and o[0][0] == UP
    pos.add(*o[0])
    # druhá strana drahá: 0.40 + 0.62 > 0.97 -> čekat, nekupovat víc UP (limit nerovnováhy)
    assert s.on_book(pos, parse_asks(book((0.40, 50))), parse_asks(book((0.62, 50))), 0.0) == []
    # druhá strana zlevní: 0.40 + 0.55 <= 0.97 -> dorovnat DOWN
    o = s.on_book(pos, parse_asks(book((0.44, 50))), parse_asks(book((0.55, 50))), 0.0)
    assert o and o[0][0] == DOWN
    pos.add(*o[0])
    assert pos.matched == 10
    assert pos.settle(UP) == pytest.approx(10 - 4.0 - 5.5)


def test_leg_in_no_new_legs_near_expiry():
    s = LegIn(clip=10, stop_new_legs_sec=60)
    assert s.on_book(Position(), parse_asks(book((0.30, 50))), parse_asks(book((0.70, 50))), 0.0,
                     secs_left=30) == []


def gamma_event(slug, closed=False, prices=("0.5", "0.5")):
    return [{"slug": slug, "markets": [{
        "slug": slug, "outcomes": json.dumps(["Up", "Down"]),
        "clobTokenIds": json.dumps(["T_UP", "T_DN"]), "closed": closed,
        "outcomePrices": json.dumps(list(prices)), "feesEnabled": True,
        "feeSchedule": {"rate": 0.01}}]}]


def test_market_parsing_reads_fee_rate():
    m = market_from_event(gamma_event("x")[0])
    assert m["tokens"] == ["T_UP", "T_DN"] and m["rate"] == 0.01


def test_full_cycle_buy_then_settle(tmp_path):
    t0 = 1795693500  # začátek 15m okna
    slug, _ = window_slug("xrp", "15m", t0 + 10)
    state = {"closed": False}

    def fetch(url):
        if "gamma" in url:
            if state["closed"]:
                return gamma_event(slug, True, ("1", "0"))
            return gamma_event(slug)
        return book((0.47, 100)) if "T_UP" in url else book((0.48, 100))

    r = Runner(tmp_path, fetch=fetch)
    r.step(["xrp"], ["15m"], now=t0 + 10)
    state["closed"] = True
    r.step(["xrp"], ["15m"], now=t0 + 900 + 60)
    out = summarize(tmp_path)
    assert out["instant_pair"]["markets"] == 1
    assert out["instant_pair"]["pnl"] > 0  # pár 0.95 + poplatky < 1


def test_service_status_without_db(monkeypatch):
    import polymarket_paper.service as svc
    monkeypatch.delenv("DATABASE_URL", raising=False)
    out = svc.status()
    assert out["mode"].startswith("PAPER") and out["strategies"] == {}


def test_sink_failure_does_not_stop_runner(tmp_path):
    def bad_sink(kind, row):
        raise RuntimeError("db down")
    r = Runner(None, fetch=lambda u: [], sink=bad_sink)
    r.log("fills", {"x": 1})  # nesmí vyhodit výjimku
