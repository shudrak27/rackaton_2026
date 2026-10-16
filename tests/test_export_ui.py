import pandas as pd
import pytest

from screening.data import schema as s
from screening.export_ui import MIN_CELL, rate_table, wilson


def test_wilson_contains_proportion_and_is_bounded():
    lo, hi = wilson(19, 100)
    assert 0 < lo < 0.19 < hi < 1
    assert wilson(0, 50)[0] == pytest.approx(0, abs=1e-12)


def test_rate_table_suppresses_small_groups():
    df = pd.DataFrame({"g": ["a"] * (MIN_CELL - 1) + ["b"] * MIN_CELL,
                       s.ATTENDED: [1] * (2 * MIN_CELL - 1)})
    rows = rate_table(df, "g")
    assert [r["group"] for r in rows] == ["b"]
    assert rows[0]["n"] == MIN_CELL and rows[0]["attendance"] == 1


def test_targeting_comparison_counts_people():
    import numpy as np

    from screening.export_ui import targeting_comparison
    y = np.array([1, 1, 1, 1, 0, 0, 0, 0, 1, 0])          # 1 = non-attendance
    perfect = y.astype(float)
    rows = targeting_comparison(y, perfect, np.zeros(10), shares=(0.4,))
    r = rows[0]
    assert r["n"] == 4 and r["top_wasted_model"] == 0 and r["bottom_attendance_model"] == 1.0
