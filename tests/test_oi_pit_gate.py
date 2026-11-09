"""Syntetické testy PIT brány (cutoff, publikace, fail closed). Bez sítě, bez výkonnosti."""
import datetime as dt

import pytest

from research.oi_metrics_audit import pit_gate as G

UTC = dt.timezone.utc
EV = dt.datetime(2024, 3, 1, 12, 0, tzinfo=UTC)
SHA = "a" * 64


def live(**kw):
    base = dict(source="rest_live", event_time=EV, evidence="captured_live",
                first_available_at=EV + dt.timedelta(seconds=30), captured_sha256=SHA,
                api_response_time=EV + dt.timedelta(seconds=31), clock_offset=dt.timedelta(seconds=1),
                revisions_checked=True)
    base.update(kw)
    return G.OIPoint(**base)


def test_live_point_cutoff_is_conservative():
    p = live()
    assert G.usable_at(p) == EV + dt.timedelta(seconds=32)
    assert not G.allowed_for_decision(p, EV + dt.timedelta(seconds=31))
    assert G.allowed_for_decision(p, EV + dt.timedelta(seconds=32))


@pytest.mark.parametrize("ev", ["s3_lastmodified", "event_time", "assumed_d_plus_1", None, "whatever"])
def test_rejected_evidence_fails_closed(ev):
    p = live(evidence=ev)
    with pytest.raises(G.PITError):
        G.usable_at(p)
    assert not G.allowed_for_decision(p, EV + dt.timedelta(days=3650))


def test_vision_point_with_lastmodified_never_allowed_even_years_later():
    p = G.OIPoint(source="vision_metrics", event_time=EV, evidence="s3_lastmodified",
                  first_available_at=EV + dt.timedelta(hours=6))
    assert not G.allowed_for_decision(p, EV + dt.timedelta(days=1))
    assert G.data_gate([p]) == "NO-GO"


@pytest.mark.parametrize("kw", [dict(captured_sha256=None), dict(captured_sha256="abc"),
                                dict(clock_offset=None), dict(clock_offset=dt.timedelta(seconds=6)),
                                dict(revisions_checked=False), dict(api_response_time=None),
                                dict(first_available_at=EV - dt.timedelta(seconds=1))])
def test_incomplete_live_provenance_fails_closed(kw):
    with pytest.raises(G.PITError):
        G.usable_at(live(**kw))


def test_gate_is_all_or_nothing():
    assert G.data_gate([live(), live()]) == "GO"
    assert G.data_gate([live(), live(evidence=None)]) == "NO-GO"
    assert G.data_gate([]) == "NO-GO"


def test_negative_clock_offset_counts_as_uncertainty():
    assert G.usable_at(live(clock_offset=dt.timedelta(seconds=-2))) == EV + dt.timedelta(seconds=33)
