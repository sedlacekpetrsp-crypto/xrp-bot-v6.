import gzip, importlib.util, pathlib

spec = importlib.util.spec_from_file_location("tl", pathlib.Path(__file__).parents[1] / "tools/research/trial_ledger.py")
tl = importlib.util.module_from_spec(spec); spec.loader.exec_module(tl)


def test_count_trades_excludes_placebo_and_benchmarks():
    raw = b"variant,pnl\nA,1\nB,2\nA,3\nplacebo_x,1\nbuy_hold,0\nEQW,1\n"
    assert tl.count_trades(raw, False) == (2, ["A", "B"])
    assert tl.count_trades(gzip.compress(raw), True)[0] == 2


def test_count_trades_without_variant_column_is_one():
    assert tl.count_trades(b"pnl\n1\n2\n", False)[0] == 1


def test_count_results_rules():
    assert tl.count_results(b'{"candidates":[1,2],"challenge_candidates":[3]}')[0] == 3
    assert tl.count_results(b'{"variants":{"a":1,"b":2}}')[0] == 2
    assert tl.count_results(b'{"runs":{}}')[0] == 1
    assert tl.count_results(b"not json")[0] == 1


def test_part_d_snapshot_totals():
    lo, hi = tl.part_d()
    assert all(x["table"] not in tl.D_MAPPED for x in lo)
    assert not any(x["table"] in tl.D_NOT_TRADES for x in lo + hi)
    assert len(lo) == 16 and len(hi) == 49
