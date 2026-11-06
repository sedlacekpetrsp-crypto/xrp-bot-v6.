"""Owner reset 2026-11-06: one-time new epoch for LIQUIDITY v2 and LH-WHALE, history archived."""
import copy
import json
import liquidity_local as local
import lh_whale as lh
import paper_epoch as pe


class FakeDB:
    def __init__(self, state):
        self.state, self.resets, self.trades, self._row = copy.deepcopy(state), {}, [], None
    def __enter__(self): return self
    def __exit__(self, *a): pass
    def execute(self, sql, args=None):
        if sql.startswith("SELECT state FROM"):
            self._row = [copy.deepcopy(self.state)]
        elif sql.startswith("SELECT 1 FROM paper_epoch_resets"):
            self._row = [1] if args[0] in self.resets else None
        elif sql.startswith("INSERT INTO paper_epoch_resets"):
            if args[0] in self.resets:
                self._row = None
            else:
                self.resets[args[0]] = json.loads(args[1]); self._row = [args[0]]
        elif sql.startswith("UPDATE") and "_state SET state" in sql:
            self.state = json.loads(args[0]); self._row = None
        elif sql.startswith("INSERT INTO") and "_trades" in sql:
            self.trades.append(args[0]); self._row = None
        else:
            self._row = None
        return self
    def fetchone(self): return self._row


def old_state(module, position=None):
    s = module.initial()
    s.update(balance=9950.23, count=21, wins=6, seen=1793000000000, cooldown=0, activated_at=1792000000000,
             last_cycle_at=module.iso(1793000000000), position=position, trades=[{"id": "x:1", "pnl": -1}])
    return s


def test_reset_once_when_flat_and_archive_kept():
    for module, bot in ((local, "LIQUIDITY_V2"), (lh, "LH_WHALE")):
        db = FakeDB(old_state(module))
        now = 1793100000000
        from unittest.mock import patch
        with patch.object(module, "connect", return_value=db):
            module.tick("test", dict(price=100, time=now), None, now)
            assert db.state["balance"] == 10000.0 and db.state["count"] == 0 and db.state["trades"] == []
            assert db.state["seen"] == 1793000000000 and db.state["previous_epoch"]["count"] == 21
            assert db.resets[bot]["balance"] == 9950.23 and db.resets[bot]["count"] == 21
            # second tick: no second reset
            db.state["balance"] = 10010.0
            module.tick("test", dict(price=100, time=now + 60000), None, now + 60000)
            assert db.state["balance"] == 10010.0 and len(db.resets) == 1


def test_no_reset_while_position_open():
    pos = {"direction": 1, "entry_price": 100, "qty": 1, "stop_loss": 90, "take_profit": 120}
    s = old_state(local, position=pos)
    out = pe.maybe_reset(FakeDB(s), "LIQUIDITY_V2", s, local.initial)
    assert out is s and out["balance"] == 9950.23


def test_other_bots_never_reset():
    s = old_state(local)
    assert pe.maybe_reset(FakeDB(s), "BEST", s, local.initial) is s
