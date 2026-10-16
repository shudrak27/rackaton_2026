"""Checks for independent units, historical region selection and planning overlays."""

import numpy as np
import pandas as pd
import pytest

from screening.evaluation.real_data import (
    exclusive_planning_segments,
    experiment_sizes,
    group_rates,
    hypothesis_masks,
    regional_shortlist,
    wilson_interval,
)


def test_wilson_intervals_do_not_collapse_at_zero_or_full_attendance():
    low, high = wilson_interval([0, 10], [10, 10])
    assert low[0] == 0 and high[0] == pytest.approx(0.2775328)
    assert low[1] == pytest.approx(0.7224672) and high[1] == pytest.approx(1)


def test_cluster_intervals_keep_repeated_people_from_inflating_precision():
    independent = pd.DataFrame({"PERSON_ID": range(100), "group": "a",
                                "attended_12m": [0, 1] * 50})
    one = group_rates(independent, "group").iloc[0]
    repeated = group_rates(pd.concat([independent] * 5), "group").iloc[0]
    assert one.ci_method == "wilson"
    assert repeated.ci_method == "person_cluster_normal"
    assert repeated.clients == 100 and repeated.n == 500
    assert repeated.attendance == one.attendance == 0.5
    expected_radius = 1.959963984540054 * np.sqrt(0.25 / 99)
    assert repeated.ci_high == pytest.approx(0.5 + expected_radius)
    assert repeated.ci_high - repeated.ci_low > 0.19


def test_regional_selection_does_not_use_reporting_year_outcomes(cfg):
    df = pd.DataFrame({"PERSON_ID": range(8), "year": [2020] * 4 + [2024] * 4,
                       "VZP_TERRITORIAL_AREA": ["a", "a", "b", "b"] * 2,
                       "attended_12m": [0, 0, 1, 1, 1, 1, 0, 0]})
    original = regional_shortlist(df, cfg)
    df.loc[df.year.eq(2024), "attended_12m"] = 1 - df.loc[df.year.eq(2024), "attended_12m"]
    pd.testing.assert_frame_equal(original, regional_shortlist(df, cfg))
    assert original.loc[original.selected, "VZP_TERRITORIAL_AREA"].tolist() == ["a"]


def test_planning_segments_preserve_production_priority_and_unknown_history(cfg):
    df = pd.DataFrame({
        "PERSON_ID": ["a", "b", "c", "d"], "INVITATION_DATE": "01.01.2024",
        "VZP_TERRITORIAL_AREA": "area", "PRIOR_INVITATION_COUNT": [4, 2, 4, 2],
        "PRIOR_SCREEN_COUNT_5Y": [2, 0, 0, 0],
        "MONTHS_SINCE_LAST_SCREEN": [1, np.nan, np.nan, np.nan],
        "HEALTHCARE_CONTACT_12M_CNT": [0, 3, 0, 3],
        "GP_REGISTERED": "A", "GYN_REGISTERED_FLAG": "N",
        "GP_PREVENTION_24M_CNT": 0, "GYN_PREVENTION_24M_CNT": 0,
        "SCREENING_12M_FLAG": "N", "attended_12m": 0,
    })
    segment = exclusive_planning_segments(df, cfg, ["area"])
    assert segment.tolist() == ["recently_screened", "regional", "low_contact", "regional"]
    hypotheses = hypothesis_masks(df, cfg, ["area"])
    assert hypotheses["regional"].all()
    assert hypotheses["low_contact"].tolist() == [True, False, True, False]


def test_experiment_sizes_use_clients_instead_of_invitation_counts(cfg):
    segments = pd.DataFrame({"segment": ["low_contact", "recently_screened"],
                             "n": [100_000, 100_000], "clients": [10, 10],
                             "attendance": [0.1, 0.1]})
    table = experiment_sizes(segments, cfg)
    assert table.segment.eq("low_contact").all()
    assert table.available_clients.eq(10).all()
    assert not table.feasible_at_full_recruitment.any()
    assert table.n_control.eq(table.n_treatment).all()
