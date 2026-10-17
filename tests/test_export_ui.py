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


def test_ranking_quality_random_level_is_attendance_rate():
    import numpy as np

    from screening.export_ui import ranking_quality
    y = np.array([1, 1, 1, 1, 0, 0, 1, 1, 1, 0])          # 1 = non-attendance, 30% attend
    rows = {r["scorer"]: r for r in ranking_quality(y, y.astype(float), np.zeros(10))}
    assert rows["random"]["ap_attendance"] == pytest.approx(0.3)
    assert rows["model"]["ap_attendance"] == pytest.approx(1.0) and rows["model"]["roc_auc"] == 1.0


def test_call_personas_pick_highest_risk_and_describe_them():
    import numpy as np

    from screening.data import schema as s
    from screening.export_ui import call_personas
    n = 100
    df = pd.DataFrame({s.ATTENDED: [0] * 50 + [1] * 50, s.N_PRIOR_INVITATIONS: [10] * 50 + [0] * 50,
                       s.AGE_BAND: ["65-69"] * 50 + ["45-49"] * 50, s.GYN_PREVENTION_24M: [0] * 50 + [2] * 50})
    risk = np.r_[np.full(50, 0.9), np.full(50, 0.1)]
    p = call_personas(df, risk, shares=(0.1,))
    call, letter = p["call"][0], p["letter_enough"]
    assert call["n"] == n // 10 and call["attendance"] == 0 and call["top_age_band"] == "65-69"
    assert call["median_prior_invitations"] == 10 and call["no_gyn_checkup_24m"] == 1
    assert letter["attendance"] == 1 and letter["top_age_band"] == "45-49"
