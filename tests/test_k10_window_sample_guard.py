"""Synthetic regression tests for K10 ranking-window sample boundaries (no network)."""
from research.k10_step0 import ledger_probe as lp


def test_verdict_fails_closed_on_empty_window():
    assert lp.verdict([{"count": 0, "sample": {"ledgers": 1, "seconds": 1, "bytes": 10}}])["verdict"] == "INVALID_SAMPLE"


def test_verdict_fails_closed_on_zero_sample():
    assert lp.verdict([{"count": 10, "sample": {"ledgers": 0, "seconds": 1, "bytes": 10}}])["verdict"] == "INVALID_SAMPLE"


def test_verdict_fails_closed_on_no_windows():
    assert lp.verdict([])["verdict"] == "INVALID_SAMPLE"


def test_probe_does_not_sample_beyond_window(monkeypatch):
    calls = []
    def rpc(method, params):
        if method == "server_info":
            return {"info": {"validated_ledger": {"seq": 1000}}}, 1, 0
        if method == "ledger":
            return {"ledger": {"close_time": 0}, "validated": True}, 1, 0
        raise AssertionError(method)
    monkeypatch.setattr(lp, "close_unix", lambda rpc, idx: 946684800)
    monkeypatch.setattr(lp, "first_at_or_after", lambda rpc, t, lo, hi: 100 if t < 946684800 else 102)
    monkeypatch.setattr(lp, "sample_cost", lambda rpc, start, n: (calls.append((start, n)) or {"ledgers": n, "seconds": n, "bytes": n}))
    result = lp.probe(lambda host: rpc, hosts=["https://test.invalid"], years=[2000], n_sample=20)
    assert calls == [(100, 2)]
    assert result["windows"][0]["count"] == 2
    assert result["result"]["verdict"] == "FEASIBLE_DIRECT"
