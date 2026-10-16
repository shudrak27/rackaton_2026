"""Budget feasibility, client exclusivity and accounting for assumed outreach effects."""

import numpy as np
import pandas as pd
import pytest

from screening.policy.budget import allocate, summary


def test_greedy_allocation_and_accounting():
    df = pd.DataFrame({"client_id": [1, 2, 3], "segment": ["a", "b", "a"],
                       "risk_non_attendance": [0.8, 0.9, 0.7]})
    before = df.copy(deep=True)
    cfg = {"sms": {"cost_czk": 2, "uplift_pp": {"a": 2, "b": 1}},
           "call": {"cost_czk": 10, "uplift_pp": {"a": 5, "b": 8}}}
    plan = allocate(df, cfg, 14)
    assert plan["client_id"].tolist() == [1, 3, 2]
    assert plan["intervention"].tolist() == ["sms", "sms", "call"]
    report = summary(plan)
    assert report["budget_spent_czk"] == 14
    assert report["expected_additional_screenings"] == pytest.approx(0.12)
    assert report["cost_per_additional_screening_czk"] == pytest.approx(14 / 0.12)
    assert sum(r["budget_spent_czk"] for r in report["by_segment"]) == 14
    assert sum(r["n_clients"] for r in report["by_intervention"]) == 3
    pd.testing.assert_frame_equal(df, before)


def test_repeated_invitation_only_one_action_per_client():
    df = pd.DataFrame({"client_id": [1, 1, 2], "segment": ["a", "b", "a"]}, index=[4, 4, 4])
    cfg = {"sms": {"cost_czk": 2, "uplift_pp": {"a": 1, "b": 3}}}
    plan = allocate(df, cfg, 20)
    assert plan["client_id"].tolist() == [1, 2]
    assert plan["segment"].tolist() == ["b", "a"]
    assert not plan["client_id"].duplicated().any()


def test_skips_unaffordable_action_and_selects_cheaper_alternative():
    df = pd.DataFrame({"client_id": [1], "segment": ["a"]})
    cfg = {"call": {"cost_czk": 10, "uplift_pp": {"a": 20}},
           "sms": {"cost_czk": 2, "uplift_pp": {"a": 1}}}
    assert allocate(df, cfg, 2)["intervention"].tolist() == ["sms"]


def test_risk_headroom_free_actions_and_nonpositive_effects():
    df = pd.DataFrame({"client_id": [1, 2, 3], "segment": ["a", "b", "c"],
                       "risk_non_attendance": [0.01, 0.9, 0.9]})
    cfg = {"free": {"cost_czk": 0, "uplift_pp": {"a": 5, "b": 0, "c": -2}}}
    plan = allocate(df, cfg, 0)
    assert plan["client_id"].tolist() == [1]
    assert plan["expected_additional_screenings"].tolist() == [0.01]
    assert summary(plan)["cost_per_additional_screening_czk"] == 0


@pytest.mark.parametrize("budget", [0, 1])
def test_empty_plan_has_stable_schema_and_summary(budget):
    df = pd.DataFrame({"client_id": [1], "segment": ["unknown"]})
    plan = allocate(df, {"sms": {"cost_czk": 2, "uplift_pp": {"a": 1}}}, budget)
    report = summary(plan)
    assert plan.empty and report["n_clients"] == 0
    assert report["budget_spent_czk"] == report["expected_additional_screenings"] == 0
    assert report["cost_per_additional_screening_czk"] is None
    assert report["by_segment"] == report["by_intervention"] == []
    assert allocate(df.iloc[:0], {}, budget).columns.tolist() == plan.columns.tolist()


@pytest.mark.parametrize("budget", [-1, np.nan, np.inf])
def test_rejects_invalid_budget(budget):
    with pytest.raises(ValueError, match="budget"):
        allocate(pd.DataFrame({"client_id": [1], "segment": ["a"]}), {}, budget)


@pytest.mark.parametrize("cost,effect", [(-1, 2), (np.nan, 2), (1, np.inf), (1, 101)])
def test_rejects_invalid_intervention_assumptions(cost, effect):
    with pytest.raises(ValueError):
        allocate(pd.DataFrame({"client_id": [1], "segment": ["a"]}),
                 {"sms": {"cost_czk": cost, "uplift_pp": {"a": effect}}}, 10)


def test_empty_config_and_missing_client():
    df = pd.DataFrame({"client_id": [1], "segment": ["a"]})
    assert allocate(df, {}, 10).empty
    with pytest.raises(ValueError, match="client_id"):
        allocate(df.assign(client_id=None), {}, 10)


def test_fractional_crown_costs_do_not_lose_an_affordable_client():
    df = pd.DataFrame({"client_id": [1, 2, 3], "segment": ["a"] * 3})
    plan = allocate(df, {"sms": {"cost_czk": 0.1, "uplift_pp": {"a": 1}}}, 0.3)
    assert len(plan) == 3
    assert summary(plan)["budget_spent_czk"] == 0.3


@pytest.mark.parametrize("risk", [np.nan, -0.1, 1.1])
def test_rejects_invalid_risk(risk):
    with pytest.raises(ValueError, match="risk_non_attendance"):
        allocate(pd.DataFrame({"client_id": [1], "segment": ["a"],
                               "risk_non_attendance": [risk]}), {}, 10)


def test_categorical_segments_with_unlisted_values():
    df = pd.DataFrame({"client_id": [1, 2, 3],
                       "segment": pd.Categorical(["a", "unlisted", None])})
    plan = allocate(df, {"sms": {"cost_czk": 2, "uplift_pp": {"a": 1}}}, 10)
    assert plan["client_id"].tolist() == [1]
