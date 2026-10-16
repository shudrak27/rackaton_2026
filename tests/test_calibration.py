import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import roc_auc_score

from screening.data import schema as s
from screening.models.calibration import CalibratedModel, recent_holdout


class ShiftedModel:
    """Ranks correctly but over-predicts the positive class by a fixed logit shift."""

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        p = 1 / (1 + np.exp(-(X["z"].to_numpy() + 1.0)))
        return np.column_stack([1 - p, p])


def _data(n: int, seed: int) -> tuple[pd.DataFrame, pd.Series]:
    rng = np.random.default_rng(seed)
    z = rng.normal(0, 1.5, n)
    y = (rng.random(n) < 1 / (1 + np.exp(-z))).astype(int)
    return pd.DataFrame({"z": z}), pd.Series(y)


@pytest.mark.parametrize("method", ["isotonic", "sigmoid"])
def test_calibration_removes_bias_and_keeps_ranking(method):
    X_cal, y_cal = _data(20_000, 0)
    X_te, y_te = _data(20_000, 1)
    base = ShiftedModel()
    model = CalibratedModel(base, method).fit(X_cal, y_cal)
    raw = base.predict_proba(X_te)[:, 1]
    cal = model.predict_proba(X_te)[:, 1]
    assert abs(raw.mean() - y_te.mean()) > 0.1
    assert abs(cal.mean() - y_te.mean()) < 0.01
    assert roc_auc_score(y_te, cal) == pytest.approx(roc_auc_score(y_te, raw), abs=0.005)
    assert np.allclose(model.predict_proba(X_te).sum(axis=1), 1)


def test_recent_holdout_takes_last_months():
    dates = pd.date_range("2020-01-01", "2022-12-01", freq="MS")
    df = pd.DataFrame({s.INVITATION_DATE: dates})
    fit, holdout = recent_holdout(df, 6)
    assert holdout.sum() == 6 and (fit ^ holdout).all()
    assert df.loc[holdout, s.INVITATION_DATE].min() > df.loc[fit, s.INVITATION_DATE].max()


def test_unknown_method_rejected():
    with pytest.raises(ValueError):
        CalibratedModel(ShiftedModel(), "magic")
