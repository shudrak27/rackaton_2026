"""Executable evidence for audit findings; strict xfails become actionable regression tests.

Each test expresses the desired contract, not the current faulty behavior. Remove the
corresponding xfail marker when fixing a finding. Unexpected passes require review.
"""

import numpy as np
import pandas as pd
import pytest

from screening.data import schema as s
from screening.data.load import prepare
from screening.experiment.analysis import analyze
from screening.experiment.power import n_per_group
from screening.features.build import build
from screening.policy.budget import allocate
from screening.scoring import score
from screening.segments.rules import assign


class ConstantRisk:
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        return np.tile([0.2, 0.8], (len(X), 1))


def _invitations(n: int = 10) -> pd.DataFrame:
    return pd.DataFrame({s.CLIENT_ID: range(n), s.INVITATION_DATE: ["2024-01-01"] * n})


def _bundle() -> dict:
    return {"model": ConstantRisk(), "features": [s.AGE], "categories": {}}


@pytest.mark.parametrize("value", ["UNKNOWN", None, 0.5, 2])
def test_audit_invalid_attendance_is_rejected(cfg, value):
    with pytest.raises(ValueError):
        prepare(_invitations().assign(attended_12m=value), cfg)


@pytest.mark.parametrize("source,derived", [
    (s.MONTHS_SINCE_LAST, "overdue"),
    (s.N_PRIOR_INVITATIONS, "first_invitation"),
])
def test_audit_excluded_sources_do_not_generate_model_inputs(cfg, source, derived):
    config = {**cfg, "features": {**cfg["features"], "exclude": [source]}}
    _, features = build(pd.DataFrame({source: [0, 30]}), config)
    assert derived not in features


def test_audit_scoring_retains_rows_with_optional_outcome(cfg):
    config = {**cfg, "data": {**cfg["data"], "cutoff_date": "2024-06-01"}}
    raw = _invitations().assign(attended_12m=0)
    result = score(raw, _bundle(), config)
    assert len(result) == len(raw)


@pytest.mark.parametrize("n", [0, 1])
def test_audit_scoring_supports_small_batches(cfg, n):
    result = score(_invitations(n), _bundle(), cfg)
    assert len(result) == n


def test_audit_missing_registration_is_not_evidence_of_low_contact(cfg):
    assert assign(pd.DataFrame(index=range(2)), cfg).eq("other").all()


def test_audit_two_boolean_registrations_count_as_two(cfg):
    df, _ = build(pd.DataFrame({s.HAS_GP: [True], s.HAS_GYN: [True]}), cfg)
    assert df["n_registrations"].iloc[0] == 2


def test_audit_scoring_output_can_feed_budget_allocation(cfg):
    scored = score(_invitations(), _bundle(), cfg)
    actions = {"sms": {"cost_czk": 2, "uplift_pp": {"low_contact": 1, "other": 1}}}
    assert len(allocate(scored, actions, 20)) == len(scored)


@pytest.mark.xfail(strict=True, reason="A10: duplicate clients inflate ITT sample sizes")
def test_audit_analysis_rejects_duplicate_randomization_units():
    df = pd.DataFrame({"client_id": [1, 1, 2, 2], "arm": ["control"] * 2 + ["sms"] * 2,
                       "attended": [0, 0, 1, 1]})
    with pytest.raises(ValueError):
        analyze(df, "arm", "attended")


@pytest.mark.xfail(strict=True, reason="A11: invalid design parameters are not validated")
@pytest.mark.parametrize("kwargs", [
    {"mde": 0}, {"ratio": 0}, {"ratio": -1}, {"alpha": 1}, {"power": 0},
])
def test_audit_power_rejects_invalid_design(kwargs):
    params = {"p_control": 0.1, "mde": 0.02, **kwargs}
    with pytest.raises(ValueError):
        n_per_group(**params)
