"""Scoring of new invitations with a trained model bundle (models/model.joblib):
risk of non-attendance + risk decile + segment + recommended intervention per invitation."""

import joblib
import numpy as np
import pandas as pd

from screening.data import schema as s
from screening.data.load import prepare
from screening.features.build import build
from screening.segments import rules


def make_bundle(model, X_train: pd.DataFrame, name: str, cfg: dict,
                reference_risk: np.ndarray | None = None) -> dict:
    """Everything needed to reproduce the feature matrix and risk deciles at scoring time.

    reference_risk (e.g. predictions on the test year) fixes the decile thresholds, so a
    client's decile does not depend on who else is in the scored batch."""
    categories = {c: list(X_train[c].cat.categories) for c in X_train.columns
                  if isinstance(X_train[c].dtype, pd.CategoricalDtype)}
    bins = None
    if reference_risk is not None and len(reference_risk):
        bins = np.quantile(reference_risk, np.linspace(0.1, 0.9, 9)).tolist()
    return {"model": model, "features": list(X_train.columns), "categories": categories,
            "model_name": name, "feature_cfg": cfg["features"], "risk_decile_bins": bins}


def load_bundle(path) -> dict:
    return joblib.load(path)


def _bundle_cfg(bundle: dict, cfg: dict) -> dict:
    return {**cfg, "features": bundle.get("feature_cfg", cfg["features"])}


def feature_matrix(built: pd.DataFrame, bundle: dict) -> pd.DataFrame:
    """Model input from a frame already passed through `build`."""
    X = built.reindex(columns=bundle["features"])  # missing columns -> NaN
    for c, levels in bundle["categories"].items():
        # same category codes as in training; unseen levels -> NaN
        values = X[c].astype(object)
        X[c] = pd.Categorical(values.where(values.isin(levels)), categories=levels)
    return X


def risk_decile(risk: np.ndarray, bins: list[float] | None) -> np.ndarray:
    """1 = lowest risk, 10 = highest. Without reference bins: ranks within the batch."""
    risk = np.asarray(risk, dtype=float)
    if bins is not None:
        return np.searchsorted(bins, risk, side="right") + 1
    if len(risk) == 0:
        return np.array([], dtype=int)
    pct = pd.Series(risk).rank(method="first", pct=True).to_numpy()
    return np.ceil(pct * 10).astype(int)


def score(raw: pd.DataFrame, bundle: dict, cfg: dict) -> pd.DataFrame:
    df = prepare(raw, cfg, require_target=False)
    built, _ = build(df, _bundle_cfg(bundle, cfg))
    X = feature_matrix(built, bundle)
    risk = bundle["model"].predict_proba(X)[:, 1] if len(X) else np.array([], dtype=float)
    segment = rules.assign(built, cfg)
    out = df[[s.CLIENT_ID, s.INVITATION_DATE]].copy()
    out["risk_non_attendance"] = risk
    out["risk_decile"] = risk_decile(risk, bundle.get("risk_decile_bins"))
    out["segment"] = segment.to_numpy()
    # not "intervention": that name belongs to budget allocation plans
    out["recommended_intervention"] = out["segment"].map(rules.INTERVENTIONS)
    return out.sort_values("risk_non_attendance", ascending=False).reset_index(drop=True)
