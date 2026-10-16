"""Fast checks for allocation, ITT analysis and synthetic experiment outcomes."""

import numpy as np
import pandas as pd
import pytest

from screening.experiment.analysis import analyze, simulate_outcomes
from screening.experiment.assign import assign_arms, balance_table


def test_allocation_quotas_missing_strata_and_reproducibility():
    df = pd.DataFrame({"segment": np.repeat(["a", "b", None], [101, 7, 1]),
                       "quintile": np.arange(109) % 5})
    df.index = np.repeat(np.arange(55), 2)[:len(df)]
    arms = {"control": 0.5, "sms": 0.25, "call": 0.25}
    assigned = assign_arms(df, ["segment", "quintile"], arms, 42)
    pd.testing.assert_series_equal(assigned, assign_arms(df, ["segment", "quintile"], arms, 42))
    pd.testing.assert_index_equal(assigned.index, df.index)
    for positions in df.groupby(["segment", "quintile"], dropna=False).indices.values():
        counts = assigned.iloc[positions].value_counts()
        for arm, share in arms.items():
            assert abs(counts.get(arm, 0) - len(positions) * share) < 1


def test_allocation_global_block_zero_arm_and_seed_changes():
    df = pd.DataFrame({"client_id": np.arange(100)})
    arms = {"control": 0.5, "sms": 0.5, "unused": 0}
    a = assign_arms(df, [], arms, 1)
    assert a.value_counts().to_dict() == {"control": 50, "sms": 50}
    assert not a.equals(assign_arms(df, [], arms, 2))
    assert assign_arms(df.iloc[:0], [], arms, 1).empty


def test_allocation_categorical_missing_strata_and_input_unchanged():
    df = pd.DataFrame({"s": pd.Categorical(["a", "a", None, None], categories=["a", "unused"])})
    before = df.copy(deep=True)
    arm = assign_arms(df, ["s"], {"control": 0.5, "sms": 0.5}, 1)
    assert arm.iloc[:2].nunique() == arm.iloc[2:].nunique() == 2
    pd.testing.assert_frame_equal(df, before)


@pytest.mark.parametrize("arms", [{"a": 1}, {"a": 0.4, "b": 0.4},
                                  {"a": -0.5, "b": 1.5}, {"a": np.nan, "b": 1}])
def test_allocation_rejects_invalid_shares(arms):
    with pytest.raises(ValueError):
        assign_arms(pd.DataFrame(index=range(10)), [], arms, 1)


@pytest.mark.parametrize("clients", [[1, 1], [1, None]])
def test_allocation_rejects_repeated_or_missing_clients(clients):
    with pytest.raises(ValueError, match="client_id"):
        assign_arms(pd.DataFrame({"client_id": clients}), [], {"a": 0.5, "b": 0.5}, 1)


def test_balance_numeric_smd_and_categorical_missing_level():
    df = pd.DataFrame({"arm": ["control"] * 3 + ["sms"] * 3,
                       "age": [1, 2, 3, 3, 4, 5],
                       "region": ["a", "b", None, "a", "b", None]})
    result = balance_table(df, "arm", ["age", "region"])
    numeric = result.loc[result["covariate"].eq("age")].iloc[0]
    assert numeric["mean"] == 4 and numeric["mean_reference"] == 2
    assert numeric["smd"] == pytest.approx(2)
    categorical = result.loc[result["covariate"].eq("region")]
    assert len(categorical) == 3 and categorical["level"].isna().sum() == 1
    assert categorical["smd"].eq(0).all()


def test_balance_constant_unbalanced_and_singleton():
    df = pd.DataFrame({"arm": ["a", "a", "b", "b"], "x": [0, 0, 1, 1]})
    assert np.isposinf(balance_table(df, "arm", ["x"]).iloc[0]["smd"])
    assert np.isnan(balance_table(df.iloc[[0, 2]], "arm", ["x"]).iloc[0]["smd"])


def test_simulated_five_pp_effect_is_recovered():
    df = pd.DataFrame({"client_id": np.arange(200_000), "baseline": 0.2})
    df["arm"] = assign_arms(df, [], {"control": 0.5, "sms": 0.5}, 17)
    df["attended"] = simulate_outcomes(df, "arm", "baseline", {"control": 0, "sms": 5}, 71)
    pd.testing.assert_series_equal(df["attended"].rename("attended_12m"),
                                   simulate_outcomes(df, "arm", "baseline", {"control": 0, "sms": 5}, 71))
    result = analyze(df, "arm", "attended").iloc[0]
    assert result["n"] == result["n_control"] == 100_000
    assert 0 < result["ci_low_pp"] < 5 < result["ci_high_pp"]
    assert result["p_value"] < 0.001


def test_analysis_known_rates_and_itt_keeps_undelivered():
    df = pd.DataFrame({"arm": ["control"] * 100 + ["sms"] * 100,
                       "attended": [1] * 20 + [0] * 80 + [1] * 25 + [0] * 75,
                       "delivered": [False] * 200})
    result = analyze(df, "arm", "attended").iloc[0]
    assert result["difference_pp"] == pytest.approx(5)
    assert result["relative_effect"] == pytest.approx(0.25)
    assert result["attendance_control"] == 0.2
    assert result["n"] + result["n_control"] == 200
    se = np.sqrt(0.25 * 0.75 / 100 + 0.2 * 0.8 / 100)
    assert result["ci_low_pp"] == pytest.approx(100 * (0.05 - 1.959963984540054 * se))
    # Independent pooled two-proportion calculation: z ~= 0.8467.
    assert result["p_value"] == pytest.approx(0.397, abs=0.002)


def test_analysis_subgroups_missing_arm_and_zero_control_rate():
    df = pd.DataFrame({"arm": ["control", "sms", "control", "control", "sms"],
                       "attended": [0, 0, 1, 0, 1], "segment": ["a", "a", "b", None, None]})
    df["segment"] = pd.Categorical(df["segment"], categories=["a", "b", "unused"])
    result = analyze(df, "arm", "attended", by="segment")
    assert len(result) == 3 and result["segment"].isna().sum() == 1
    a = result.loc[result["segment"].eq("a")].iloc[0]
    b = result.loc[result["segment"].eq("b")].iloc[0]
    assert a["p_value"] == 1 and np.isnan(a["relative_effect"])
    assert b["n"] == 0 and np.isnan(b["difference_pp"])


@pytest.mark.parametrize("outcomes", [[0, None], [0, 2]])
def test_analysis_rejects_unobserved_or_nonbinary_outcomes(outcomes):
    with pytest.raises(ValueError):
        analyze(pd.DataFrame({"arm": ["control", "sms"], "y": outcomes}), "arm", "y")


def test_analysis_requires_control():
    with pytest.raises(ValueError, match="control"):
        analyze(pd.DataFrame({"arm": ["sms"], "y": [1]}), "arm", "y")


def test_simulator_probability_bounds_and_explicit_arm_effect():
    df = pd.DataFrame({"arm": ["control", "sms"], "p": [0, 0.99]}, index=[7, 7])
    outcomes = simulate_outcomes(df, "arm", "p", {"control": 0, "sms": 5}, 1)
    assert outcomes.tolist() == [0, 1] and outcomes.index.tolist() == [7, 7]
    with pytest.raises(ValueError, match="explicit uplift"):
        simulate_outcomes(df, "arm", "p", {"control": 0}, 1)
    with pytest.raises(ValueError, match="probabilities"):
        simulate_outcomes(df.assign(p=2), "arm", "p", {"control": 0, "sms": 5}, 1)
