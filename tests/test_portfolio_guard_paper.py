import ast
from pathlib import Path


def test_portfolio_guard_preserves_pause():
    tree = ast.parse((Path(__file__).resolve().parents[1] / 'app_v8_fly.py').read_text())
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'portfolio_entry_allowed')
    assert any(isinstance(n, ast.Constant) and n.value == 'USER_PAUSED' for n in ast.walk(fn))


def test_portfolio_guard_checks_correlated_position():
    tree = ast.parse((Path(__file__).resolve().parents[1] / 'app_v8_fly.py').read_text())
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'portfolio_entry_allowed')
    assert any(isinstance(n, ast.Constant) and n.value == 'CORRELATED_POSITION_' for n in ast.walk(fn))
