"""Probability calibration on the most recent training months.

Attendance drifts between years (17.8 % in 2020, ~19.5 % later), so a model fitted on older
invitations over-predicts non-attendance. The base model is fitted on train minus the last
`holdout_months`; a monotone calibrator is fitted on that recent holdout. Ranking (AUC) is
practically unchanged; probabilities become usable for budget calculations.

IsotonicRegression / LogisticRegression on one feature: no joblib parallelism involved.
"""

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

from screening.data import schema as s


def recent_holdout(train_df: pd.DataFrame, months: int) -> tuple[pd.Series, pd.Series]:
    """Boolean masks (fit, holdout): holdout = invitations in the last `months` of train."""
    start = train_df[s.INVITATION_DATE].max() - pd.DateOffset(months=months)
    holdout = train_df[s.INVITATION_DATE] > start
    return ~holdout, holdout


def _logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p)).reshape(-1, 1)


class CalibratedModel:
    """Wraps a fitted model; `base` stays accessible for explanations and MLflow logging."""

    def __init__(self, base, method: str = "isotonic"):
        if method not in ("isotonic", "sigmoid"):
            raise ValueError(f"unknown calibration method {method!r}")
        self.base = base
        self.method = method

    def fit(self, X_holdout: pd.DataFrame, y_holdout: pd.Series) -> "CalibratedModel":
        p = self.base.predict_proba(X_holdout)[:, 1]
        if self.method == "isotonic":
            self.calibrator = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1).fit(p, y_holdout)
        else:
            self.calibrator = LogisticRegression(C=1e6).fit(_logit(p), y_holdout)
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        p = self.base.predict_proba(X)[:, 1]
        if self.method == "isotonic":
            q = self.calibrator.predict(p)
        else:
            q = self.calibrator.predict_proba(_logit(p))[:, 1]
        return np.column_stack([1 - q, q])
