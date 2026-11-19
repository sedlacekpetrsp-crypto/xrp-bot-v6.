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


# --- review Claude (dialog 0404): window, canonical identity, PIT tri-state ---
@pytest.mark.parametrize("date", ["2027-03-01T00:00:00Z", "2019-12-31T23:59:59Z", "2026-11-01T00:00:00Z"])
def test_outside_window_fails_closed(date):
    with pytest.raises(ValueError, match="window"): audit_gate([event(date=date)])

def test_window_edges_accepted():
    r = audit_gate([event(article="a", date="2020-01-01T00:00:00Z"),
                    event(article="b", date="2026-10-31T23:59:59Z")])
    assert r["eligible_events"] == 2 and r["oos_events"] == 1

def test_offset_converted_before_oos_split():
    # 2025-01-01 00:30 +01:00 == 2024-12-31 23:30 UTC => development, not OOS
    assert audit_gate([event(date="2025-01-01T00:30:00+01:00")])["oos_events"] == 0

@pytest.mark.parametrize("changes", [dict(token="pepe"), dict(token="PEPE "), dict(article=" a1")])
def test_non_canonical_identity_rejected(changes):
    with pytest.raises(ValueError, match="non-canonical"): audit_gate([event(**changes)])

def test_pit_status_breakdown_and_denominator():
    rows = [event(article=f"a{i}", token=f"T{i}") for i in range(7)]
    rows += [event(article="u", token="U", pit_ok=False, pit_status="unverified"),
             event(article="c", token="C", pit_ok=False, pit_status="contradicted"),
             event(article="d", token="D", pit_ok=False)]
    r = audit_gate(rows)
    assert (r["pit_unverified"], r["pit_contradicted"]) == (2, 1)
    assert r["pit_unverified_ratio"] == pytest.approx(3 / 10)

@pytest.mark.parametrize("changes", [dict(pit_ok=True, pit_status="contradicted"),
                                     dict(pit_ok=False, pit_status="ok"),
                                     dict(pit_ok=False, pit_status="maybe")])
def test_pit_status_inconsistent_rejected(changes):
    with pytest.raises(ValueError, match="pit_status"): audit_gate([event(**changes)])


# --- review Claude (dialog 0406): one article = one UTC instant (ChatGPT 5499c90 mechanism, integrated into the gate) ---
def test_article_split_across_oos_boundary_rejected():
    with pytest.raises(ValueError, match="inconsistent announced_at"):
        audit_gate([event(article="a", token="X", date="2024-12-31T23:59:00Z"),
                    event(article="a", token="Y", date="2025-01-01T00:01:00Z")])

def test_article_same_instant_other_offset_accepted():
    r = audit_gate([event(article="a", token="X", date="2025-03-01T12:00:00Z"),
                    event(article="a", token="Y", date="2025-03-01T13:00:00+01:00")])
    assert (r["eligible_events"], r["independent_articles"]) == (2, 1)
