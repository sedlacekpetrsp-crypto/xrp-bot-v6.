import importlib.util, pathlib
_p = pathlib.Path(__file__).resolve().parents[1] / "research/g1_power_preflight/g1_power.py"

def _mod():
    import contextlib, io
    spec = importlib.util.spec_from_file_location("g1_power", _p)
    m = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()):
        spec.loader.exec_module(m)
    return m

def test_symmetric_point_pass_is_half():
    m = _mod()
    assert abs(m.p_pass(21, 0.5, 0.5, False) - 0.5) < 1e-12  # P(X>=11 | Bin(21,.5)) = 0.5

def test_min_k_wilson():
    m = _mod()
    assert m.out[21]["min_k_recall_ci"] == 15
    assert m.wilson_lo(15, 21) > 0.5 >= m.wilson_lo(14, 21)

def test_monotone_in_p():
    m = _mod()
    vals = [m.p_pass(21, p / 10, 0.5, True) for p in range(1, 10)]
    assert vals == sorted(vals)
