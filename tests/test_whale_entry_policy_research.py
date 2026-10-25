"""Read-only source-level guardrails for Blue Whale research; no trading worker starts."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "app_blue_whale_mirror.py").read_text(encoding="utf-8")
tree = ast.parse(source)

def constant(name):
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return node.value
    raise AssertionError(name)

def test_paper_only_label():
    assert "PAPER ONLY" in source
    assert "No live orders" in source

def test_vwap_reversion_remains_paused():
    value = constant("PAUSED_STRATEGIES")
    assert "VWAP_REVERSION" in ast.unparse(value)

def test_net_reward_filter_remains_present():
    assert "WHALE_MIN_NET_RR" in source
    assert "FEE_RATE" in source
    assert "SLIPPAGE_RATE" in source

def test_risk_and_position_caps_remain_present():
    for name in ("MAX_OPEN_POSITIONS", "MAX_TOTAL_RISK_RATE", "RISK_PER_TRADE"):
        constant(name)
