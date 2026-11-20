"""K11 strict minute parsing regression tests; synthetic only, no market data."""
import io
import zipfile
import pytest
from research.k11_step0_collector import open_minutes


def _zip(rows):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        z.writestr("minutes.csv", "open_time,open,high,low,close\n" +
                   "".join(f"{v},0,0,0,0\n" for v in rows))
    return out.getvalue()


def test_valid_millisecond_minutes():
    assert len(open_minutes(_zip([1735689600000, 1735689660000]))) == 2


def test_valid_microsecond_minutes():
    assert len(open_minutes(_zip([1735689600000000, 1735689660000000]))) == 2


@pytest.mark.parametrize("rows", [
    [1735689600001],               # non-minute ms
    [1735689600000001],            # non-minute us
    [1735689600],                  # seconds incorrectly treated as ms
    [1735689600000, 1735689600000000],  # same minute in different units
    [999999999999999999],          # implausible epoch
])
def test_invalid_timestamps_fail_closed(rows):
    with pytest.raises(ValueError):
        open_minutes(_zip(rows))


def test_exact_duplicate_row_tolerated_not_inflating():  # review Claude: duplikát nemůže nafouknout množinu minut
    assert len(open_minutes(_zip([1735689600000, 1735689600000, 1735689660000]))) == 2


def test_mixed_units_different_minutes_fail_closed():
    with pytest.raises(ValueError):
        open_minutes(_zip([1735689600000, 1735689660000000]))
