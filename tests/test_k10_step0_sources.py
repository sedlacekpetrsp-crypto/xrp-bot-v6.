"""K10 §6.2 preregistered sources + §6.3 ledger probe: offline synthetic tests only."""
import json

import pytest

from research import k10_step0_sources as S
from research.k10_step0 import ledger_probe as P

A, B = "rLNaPoKeeBjZe2qs6x52yVPZpZ8td4dc6w", "rEb8TK3gBgk5auZkwc6sHnwrGVJH8DuaLh"


@pytest.fixture(scope="module")
def cfg():
    return S.load_sources()


def test_sources_frozen_json_only(cfg):
    assert [s["id"] for s in cfg["sources"]] == ["S1", "S2"]
    assert all("json" in s["format"].lower() for s in cfg["sources"])
    assert cfg["cdx_query"]["params"]["matchType"] == "exact"


def test_allowlist_normalized_and_unique(cfg):
    assert cfg["_alias_to_entity"]["binance"] == "binance"
    assert cfg["_alias_to_entity"]["okex"] == cfg["_alias_to_entity"]["okx"] == "okx"


def test_exact_match_only_no_suffix_stripping(cfg):
    pairs = [(A, "  BINANCE "), (B, "Binance Hot Wallet")]
    assert S.attribute(pairs, cfg) == {A: "binance", B: None}
    assert S.non_allowlisted_names(pairs, cfg) == ["binance hot wallet"]


def test_conflict_is_unknown_F1(cfg):
    assert S.attribute([(A, "Binance"), (A, "Bitstamp")], cfg) == {A: None}
    assert S.attribute([(A, "Binance"), (A, "Ripple")], cfg) == {A: None}
    assert S.attribute([(A, "Binance"), (A, "binance")], cfg) == {A: "binance"}


def test_s1_reads_only_account_name_F2():
    raw = json.dumps([{"account": A, "name": "Kraken", "desc": "Binance"},
                      {"account": B, "domain": "binance.com"}, "junk"]).encode()
    assert S.parse_s1(raw) == [(A, "Kraken")]
    assert S.parse_s1(b"<html>Binance</html>") == []
    assert S.parse_s1(b"\xff\xfe") == []


def test_s2_bound_to_url_account():
    ok = json.dumps({"account": A, "accountName": {"name": "Upbit", "account": A}}).encode()
    assert S.parse_s2(ok, A) == [(A, "Upbit")]
    assert S.parse_s2(ok, B) == []
    other = json.dumps({"Account": A, "accountName": {"name": "Upbit", "account": B}}).encode()
    assert S.parse_s2(other, A) == []
    assert S.parse_s2(json.dumps({"account": A, "parentName": {"name": "Binance"}}).encode(), A) == []


class FakeChain:
    """close_time grows 4 s per ledger from 2019-09-01; payload size fixed."""

    def __init__(self, fail=False, top=None):
        self.t0 = 1567296000 - P.RIPPLE_EPOCH
        self.fail = fail
        self.top = top or 40_000_000

    def rpc(self, method, params):
        if self.fail:
            raise OSError("blocked")
        if method == "server_info":
            return {"info": {"complete_ledgers": f"{P.FIRST_LEDGER}-{self.top}",
                             "validated_ledger": {"seq": self.top}}}, 100, 0.01
        idx = params["ledger_index"]
        led = {"ledger_index": str(idx), "close_time": self.t0 + 4 * (idx - P.FIRST_LEDGER), "validated": True}
        if params.get("transactions"):
            led["transactions"] = [{"TransactionType": "Payment"}, {"TransactionType": "OfferCreate"}]
            return {"ledger": led, "validated": True}, 50_000, 0.1
        return {"ledger": led, "validated": True}, 200, 0.01


def test_binary_search_exact():
    ch = FakeChain()
    t = ch.t0 + P.RIPPLE_EPOCH + 4 * 1000 + 1
    idx = P.first_at_or_after(ch.rpc, t, P.FIRST_LEDGER, ch.top)
    assert idx == P.FIRST_LEDGER + 1001
    assert P.close_unix(ch.rpc, idx - 1) < t <= P.close_unix(ch.rpc, idx)


def test_probe_counts_and_verdict():
    ch = FakeChain()
    res = P.probe(lambda h: ch.rpc, hosts=["h1"], years=(2020,), n_sample=3)
    w = res["windows"][0]
    assert w["count"] == 90 * 86400 // 4
    assert w["sample"] == {"ledgers": 3, "bytes": 150_000, "seconds": 0.3, "tx": 6, "payments": 3}
    # 1 944 000 ledgers * 0.1 s = 54 h > 5 h
    assert res["result"]["verdict"] == "INFEASIBLE_DIRECT"


def test_all_hosts_fail_closed():
    res = P.probe(lambda h: FakeChain(fail=True).rpc, hosts=["a", "b"], years=(2020,))
    assert res["result"] == {"verdict": "DATA_SOURCE_UNAVAILABLE"}
    assert all("error" in h for h in res["hosts"])
