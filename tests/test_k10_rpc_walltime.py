"""Offline regression for K10 sequential RPC pacing; no market data or network."""
import json
from research.k10_step0 import ledger_probe as lp


def test_rpc_latency_includes_mandatory_pacing(monkeypatch):
    clock = [10.0]
    class Reply:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            clock[0] += 0.05
            return json.dumps({"result": {"status": "success", "ledger": {}}}).encode()
    monkeypatch.setattr(lp.urllib.request, "urlopen", lambda req, timeout: Reply())
    monkeypatch.setattr(lp.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(lp.time, "sleep", lambda s: clock.__setitem__(0, clock[0] + s))
    result, size, seconds = lp.make_rpc("https://example.invalid", pause=0.2)("ledger", {"ledger_index": 1})
    assert result["status"] == "success"
    assert size > 0
    assert abs(seconds - 0.25) < 1e-8


def test_cost_threshold_includes_pacing():
    # 100,000 ledgers * 0.2 seconds = 5.56 h, beyond the frozen 5 h gate.
    windows = [{"count": 100_000, "sample": {"ledgers": 20, "seconds": 4.0, "bytes": 1000}}]
    assert lp.verdict(windows)["verdict"] == "INFEASIBLE_DIRECT"
