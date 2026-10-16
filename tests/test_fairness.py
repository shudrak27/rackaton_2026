"""Group AUC and representation use a global shortlist, including missing groups."""

import numpy as np
import pandas as pd
import pytest

from screening.evaluation.fairness import group_metrics


def test_global_selection_shares_and_perfect_auc():
    df = pd.DataFrame({"region": ["a", "a", "b", "b"], "y": [0, 1, 0, 1],
                       "risk": [0.1, 0.9, 0.2, 0.8]}, index=[1, 1, 1, 1])
    before = df.copy(deep=True)
    report = group_metrics(df, "y", "risk", "region", top_k=0.5).set_index("region")
    assert report["roc_auc"].eq(1).all()
    assert report["top_k_share"].eq(0.5).all()
    assert report["population_share"].eq(0.5).all()
    assert report["selection_rate"].eq(0.5).all()
    assert report["non_attendance"].eq(0.5).all()
    pd.testing.assert_frame_equal(df, before)


def test_top_k_is_global_and_auc_ties_get_half_credit():
    df = pd.DataFrame({"group": ["a", "a", "b", "b"], "y": [0, 1, 0, 1],
                       "risk": [0.8, 0.8, 0.2, 0.1]})
    report = group_metrics(df, "y", "risk", "group", 0.5).set_index("group")
    assert report.loc["a", "top_k_share"] == 1
    assert report.loc["b", "top_k_share"] == 0
    assert report.loc["a", "roc_auc"] == 0.5
    assert report.loc["b", "roc_auc"] == 0


def test_missing_and_unused_categorical_groups_and_single_class():
    df = pd.DataFrame({"group": pd.Categorical(["a", "a", None], categories=["a", "unused"]),
                       "y": [1, 1, 0], "risk": [0.8, 0.9, 0.1]})
    report = group_metrics(df, "y", "risk", "group", top_k=1)
    assert len(report) == 2 and report["group"].isna().sum() == 1
    assert report["roc_auc"].isna().all()
    assert report["n"].sum() == 3
    assert report["top_k_share"].sum() == pytest.approx(1)
    assert report["population_share"].sum() == pytest.approx(1)


def test_empty_input_and_tiny_shortlist():
    df = pd.DataFrame({"group": ["a", "b"], "y": [0, 1], "risk": [0.5, 0.5]})
    report = group_metrics(df, "y", "risk", "group", 0.001)
    assert report["n_top_k"].tolist() == [1, 0]
    assert group_metrics(df.iloc[:0], "y", "risk", "group").empty


@pytest.mark.parametrize("top_k", [0, -0.1, 1.1, np.nan])
def test_rejects_invalid_top_k(top_k):
    with pytest.raises(ValueError, match="top_k"):
        group_metrics(pd.DataFrame({"g": [], "y": [], "p": []}), "y", "p", "g", top_k)


@pytest.mark.parametrize("y,score", [(None, 0.5), (2, 0.5), (1, np.nan), (0, 1.1)])
def test_rejects_invalid_outcomes_or_scores(y, score):
    with pytest.raises(ValueError):
        group_metrics(pd.DataFrame({"g": ["a"], "y": [y], "p": [score]}), "y", "p", "g")
