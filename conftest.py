"""Test isolation for the owner pause of 2026-11-06 (WHALE, BEST).

Importing app_v8_fly installs the shared entry guard into the whale and BEST-OF modules. With WHALE and
BEST paused, every strategy test that opens a PAPER position would fail depending on test order. The
strategy tests check strategy behaviour, so they run with WHALE/BEST unpaused; tests marked
`owner_pause` see the real production pause. FLY/FAST/LEADLAG/TV are untouched (as before).
"""
import sys

import pytest

OWNER_PAUSE_20261106 = frozenset({"WHALE", "BEST"})


def pytest_configure(config):
    config.addinivalue_line("markers", "owner_pause: run with the real production PAUSED_BOTS")


@pytest.fixture(autouse=True)
def _strategy_tests_without_owner_pause(request, monkeypatch):
    if request.node.get_closest_marker("owner_pause"):
        yield
        return
    app = sys.modules.get("app_v8_fly")
    if app is not None:
        monkeypatch.setattr(app, "PAUSED_BOTS", app.PAUSED_BOTS - OWNER_PAUSE_20261106)
    yield
