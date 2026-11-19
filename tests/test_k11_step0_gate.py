import pytest
from research.k11_step0_gate import audit_gate

def event(article="a", token="X", date="2025-01-02T00:00:00Z", **changes):
    e = dict(article_id=article, token=token, announced_at=date, event_type="spot_delist",
             pit_ok=True, perp_ok=True, coverage_ok=True)
    e.update(changes)
    return e

def test_empty(): assert audit_gate([])["verdict"] == "DATA_NO_GO"

def test_duplicate():
    with pytest.raises(ValueError, match="duplicate"): audit_gate([event(), event()])

def test_naive_timestamp():
    with pytest.raises(ValueError, match="timezone"): audit_gate([event(date="2025-01-02T00:00:00")])

def test_missing_pit():
    with pytest.raises(ValueError, match="non-boolean"): audit_gate([event(pit_ok=None)])

def test_cluster():
    rows = [event(article="same", token=f"T{i}") for i in range(60)]
    assert audit_gate(rows)["independent_articles"] == 1
    assert audit_gate(rows)["verdict"] == "DATA_NO_GO"

def test_oos():
    rows = [event(article=f"a{i}", token=f"T{i}", date="2024-06-01T00:00:00Z") for i in range(60)]
    assert audit_gate(rows)["oos_events"] == 0
    assert audit_gate(rows)["verdict"] == "DATA_NO_GO"

def test_threshold():
    rows = [event(article=f"a{i//2}", token=f"T{i}") for i in range(60)]
    assert audit_gate(rows)["verdict"] == "DATA_GO"

def test_pit_denominator():
    rows = [event(article=f"a{i//2}", token=f"T{i}") for i in range(60)]
    rows += [event(article=f"bad{i}", token=f"B{i}", pit_ok=False) for i in range(30)]
    assert audit_gate(rows)["pit_unverified_ratio"] == pytest.approx(1/3)
    assert audit_gate(rows)["verdict"] == "DATA_NO_GO"

def test_nonspot():
    assert audit_gate([event(event_type="futures_delist")])["spot_events"] == 0
