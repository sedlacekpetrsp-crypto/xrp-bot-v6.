"""Synthetic, offline fail-closed tests for K10 ledger RPC integrity."""
import pytest

from research.k10_step0.ledger_probe import close_unix, sample_cost, RIPPLE_EPOCH


def fake_rpc(requested_index, returned_index, validated=True):
    def rpc(method, params):
        assert method == "ledger"
        assert params["ledger_index"] == requested_index
        return ({"ledger": {"ledger_index": returned_index, "close_time": 123,
                             "transactions": [{"TransactionType": "Payment"}]},
                 "validated": validated}, 100, 0.5)
    return rpc


def test_close_time_rejects_wrong_ledger():
    with pytest.raises(RuntimeError, match="index mismatch"):
        close_unix(fake_rpc(100, 99), 100)


def test_sample_rejects_wrong_ledger():
    with pytest.raises(RuntimeError, match="index mismatch"):
        sample_cost(fake_rpc(100, 99), 100, 1)


def test_sample_rejects_unvalidated_ledger():
    with pytest.raises(RuntimeError, match="not validated|explicit validated"):
        sample_cost(fake_rpc(100, 100, validated=False), 100, 1)


def test_valid_ledger_still_works():
    assert close_unix(fake_rpc(100, 100), 100) == 123 + RIPPLE_EPOCH
    assert sample_cost(fake_rpc(100, 100), 100, 1) == {
        "ledgers": 1, "bytes": 100, "seconds": 0.5, "tx": 1, "payments": 1
    }
