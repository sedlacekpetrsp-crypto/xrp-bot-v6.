"""Synthetic K10 RPC validation regression tests; no network, market data or returns."""
import pytest

from research.k10_step0.ledger_probe import close_unix, sample_cost, require_validated


@pytest.mark.parametrize("res,led", [
    ({}, {}),
    ({"validated": False}, {}),
    ({"validated": "true"}, {}),
    ({"validated": 1}, {}),
    ({"validated": True}, {"validated": False}),
    ({"validated": False}, {"validated": True}),
])
def test_validation_rejects_missing_or_ambiguous_flags(res, led):
    with pytest.raises(RuntimeError, match="explicit validated"):
        require_validated(res, led, 123)


@pytest.mark.parametrize("res,led", [
    ({"validated": True}, {}),
    ({}, {"validated": True}),
    ({"validated": True}, {"validated": True}),
])
def test_validation_accepts_explicit_boolean_true(res, led):
    require_validated(res, led, 123)


def test_close_unix_rejects_missing_validation():
    def rpc(method, params):
        return {"ledger": {"ledger_index": 123, "close_time": 100}}, 10, 0.01
    with pytest.raises(RuntimeError, match="explicit validated"):
        close_unix(rpc, 123)


def test_sample_cost_rejects_missing_validation():
    def rpc(method, params):
        return {"ledger": {"ledger_index": 123, "transactions": []}}, 10, 0.01
    with pytest.raises(RuntimeError, match="explicit validated"):
        sample_cost(rpc, 123, 1)


def test_close_unix_rejects_wrong_index_even_when_validated():
    def rpc(method, params):
        return {"validated": True, "ledger": {"ledger_index": 124, "close_time": 100}}, 10, 0.01
    with pytest.raises(RuntimeError, match="index mismatch"):
        close_unix(rpc, 123)
