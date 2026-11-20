from research.pit_source_lineage_gate import gate

T = "2026-11-20T10:00:00Z"
D = "2026-11-20T12:00:00Z"


def row(origin, hash_, parent=None, **kw):
    return dict(origin_publisher=origin, archive_custodian="web.archive.org",
                source_id=origin, content_hash=hash_, published_at=T,
                captured_at=T, claim_id="C1", derived_from=parent, **kw)


def run(rows, **kw):
    return gate(rows, decision_at=D, claim_id="C1", **kw)


def test_independent():
    assert run([row("a.com", "a"), row("b.com", "b")])["status"] == "DATA_GO"


def test_syndicated_hash():
    assert run([row("a.com", "same"), row("b.com", "same")])["reason"] == "syndicated_content"


def test_derived_from():
    r = run([row("a.com", "a"), row("b.com", "b", "a.com")])
    assert r["independent_origins"] == 1


def test_cycle():
    assert run([row("a.com", "a", "b.com"), row("b.com", "b", "a.com")])["reason"] == "lineage_cycle"


def test_unverified_parent():
    assert run([row("a.com", "a", "missing.com")])["reason"] == "unverified_primary_origin"


def test_archive_as_publisher():
    assert run([row("web.archive.org", "a")])["reason"] == "archive_as_publisher"


def test_missing_lineage():
    r = row("a.com", "a")
    del r["derived_from"]
    assert run([r])["reason"] == "missing_provenance"


def test_mixed_claim():
    r = row("a.com", "a")
    r["claim_id"] = "C2"
    assert run([r])["reason"] == "mixed_claims"


def test_alias_dedup():
    r = run([row("www.a.com", "a"), row("a.com", "a")],
            aliases={"www.a.com": "a.com"})
    assert r["independent_origins"] == 1


def test_future_capture():
    r = row("a.com", "a")
    r["captured_at"] = "2026-11-21T10:00:00Z"
    assert run([r])["reason"] == "not_available_asof"


def test_asof_bound():
    assert run([row("a.com", "a"), row("b.com", "b")])["asof_bound"] == "2026-11-20T10:00:00+00:00"


def test_no_performance_authorization():
    assert run([row("a.com", "a"), row("b.com", "b")])["performance_authorized"] is False
