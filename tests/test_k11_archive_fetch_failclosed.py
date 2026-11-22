"""Regression: incomplete Wayback PIT evidence must not yield a data GO (PAPER only)."""
from research import k11_step0_collector as c
from test_k11_step0_collector import FakeNet


def test_missing_archive_snapshot_forces_data_no_go():
    class MissingSnapshot(FakeNet):
        def __call__(self, url):
            if url.startswith("https://web.archive.org/web/"):
                return 503, b""
            return super().__call__(url)

    rows, manifest = c.collect(MissingSnapshot())
    assert manifest["archive_snapshot_fetch_failures"]
    assert manifest["verdict"] == "DATA_NO_GO"
    assert manifest["returns_computed"] is False
    assert all(not row.get("pit_ok", False) for row in rows)


def test_complete_archive_snapshot_has_no_fetch_failures():
    _, manifest = c.collect(FakeNet())
    assert manifest["archive_snapshot_fetch_failures"] == []
    assert manifest["returns_computed"] is False
