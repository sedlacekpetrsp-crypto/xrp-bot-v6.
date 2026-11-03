import ast
from pathlib import Path
from types import SimpleNamespace

source = ast.parse((Path(__file__).resolve().parents[1] / "app_v8_fly.py").read_text())
functions = [node for node in source.body if isinstance(node, ast.FunctionDef) and node.name in ("_asset_key", "portfolio_entry_allowed")]
code = compile(ast.Module(body=functions, type_ignores=[]), "<portfolio-guard>", "exec")

def guard(fly=None, whale=None):
    empty = lambda: SimpleNamespace(state={"open_position": None})
    env = {
        "PAUSED_BOTS": frozenset({"FLY", "FAST", "LEADLAG", "TV"}),
        "base": SimpleNamespace(paper_position=fly),
        "fast": empty(),
        "leadlag": empty(),
        "tv": empty(),
        "whale": SimpleNamespace(state={"open_position": None, "open_positions": whale or []}),
    }
    exec(code, env)
    return env["portfolio_entry_allowed"]

def test_paused():
    assert guard()("FLY", "XRPUSDT", "LONG") == (False, "USER_PAUSED")

def test_duplicate_quote_normalization():
    assert guard(fly={"symbol":"XRPUSDC","side":"LONG"})("WHALE","XRPUSDT","LONG")[0] is False

def test_opposite_side():
    assert guard(fly={"symbol":"XRPUSDC","side":"SHORT"})("WHALE","XRPUSDT","LONG")[0] is True

def test_different_asset():
    assert guard(fly={"symbol":"ETHUSDT","side":"LONG"})("WHALE","XRPUSDT","LONG")[0] is True

def test_whale_list_blocks_best():
    assert guard(whale=[{"symbol":"SOLUSDT","side":"LONG"}])("BEST","SOLUSDC","LONG")[0] is False
