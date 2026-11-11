import datetime as dt

from research.k7_macro_calendar.step0 import (announce_utc, coverage, gate, parse_meetings, scheduled,
                                               window_hours, year_sections)

HTML = """<h4><a>2020 FOMC Meetings</a></h4>
<div class="fomc-meeting__month col"><strong>January</strong></div><div class="fomc-meeting__date col">28-29</div>
<div class="fomc-meeting__month col"><strong>March</strong></div><div class="fomc-meeting__date col">3 (unscheduled)</div>
<div class="fomc-meeting__month col"><strong>March</strong></div><div class="fomc-meeting__date col">17-18*</div>
<div class="fomc-meeting__month col"><strong>Apr/May</strong></div><div class="fomc-meeting__date col">28-29</div>
<div class="fomc-meeting__month col"><strong>Oct/Nov</strong></div><div class="fomc-meeting__date col">31-1</div>
<h4><a>2019 FOMC Meetings</a></h4>
<div class="fomc-meeting__month col"><strong>December</strong></div><div class="fomc-meeting__date col">10-11*</div>"""


def test_structured_parse_and_tags():
    secs = year_sections(HTML)
    assert set(secs) == {2019, 2020}
    m, method = parse_meetings(secs[2020], 2020)
    assert method == "structured" and len(m) == 5
    s = [str(x["end_date"]) for x in scheduled(m)]
    assert s == ["2020-01-29", "2020-03-18", "2020-04-29", "2020-11-01"]


def test_text_fallback_ignores_release_dates():
    sec = "January 29-30 Minutes Released February 20, 2019 March 19-20* July 30-31 October 4 (notation vote)"
    m, method = parse_meetings(sec, 2019)
    assert method == "text"
    assert [str(x["end_date"]) for x in scheduled(m)] == ["2019-01-30", "2019-03-20", "2019-07-31"]


def test_dst_and_window():
    assert announce_utc(dt.date(2024, 1, 31)).hour == 19  # EST
    assert announce_utc(dt.date(2024, 7, 31)).hour == 18  # EDT
    t = announce_utc(dt.date(2024, 7, 31))
    w = window_hours(t)
    assert len(w) == 96 and w[48] == int(t.timestamp())
    assert coverage(set(w), t) == 1.0 and coverage(set(w[1:]), t) < 1


def _rows(n, pit="PROVEN", cov=1.0):
    return [{"pit_status": pit, "actual_at": "x", "coverage_1h": cov} for _ in range(n)]


def test_gate():
    assert gate(_rows(60))["GO_counts"] and gate(_rows(60))["final_segment"] == 15
    assert not gate(_rows(59))["GO_counts"]
    assert not gate(_rows(70, pit="UNKNOWN"))["GO_counts"]
    assert not gate(_rows(70, cov=0.99))["GO_counts"]
