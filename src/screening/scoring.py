"""Scoring of new invitations with a trained model bundle (models/model.joblib):
risk of non-attendance + segment + recommended intervention per client."""

import joblib
import pandas as pd

from screening.data import schema as s
from screening.data.load import prepare
from screening.features.build import build
from screening.segments import rules


def make_bundle(model, X_train: pd.DataFrame, name: str) -> dict:
    """Everything needed to reproduce the feature matrix at scoring time."""
    categories = {c: list(X_train[c].cat.categories) for c in X_train.columns
                  if isinstance(X_train[c].dtype, pd.CategoricalDtype)}
    return {"model": model, "features": list(X_train.columns), "categories": categories,
            "model_name": name}


def load_bundle(path) -> dict:
    return joblib.load(path)


def feature_matrix(df: pd.DataFrame, bundle: dict, cfg: dict) -> pd.DataFrame:
    df, _ = build(df, cfg)
    X = df.reindex(columns=bundle["features"])  # missing columns -> NaN
    for c, levels in bundle["categories"].items():
        # same category codes as in training; unseen levels -> NaN
        values = X[c].astype(object)
        X[c] = pd.Categorical(values.where(values.isin(levels)), categories=levels)
    return X


def score(raw: pd.DataFrame, bundle: dict, cfg: dict) -> pd.DataFrame:
    df = prepare(raw, cfg, require_target=False)
    X = feature_matrix(df, bundle, cfg)
    risk = bundle["model"].predict_proba(X)[:, 1]
    segment = rules.assign(df, cfg)
    out = df[[s.CLIENT_ID, s.INVITATION_DATE]].copy()
    out["risk_non_attendance"] = risk
    out["risk_decile"] = pd.qcut(pd.Series(risk).rank(method="first"), 10,
                                 labels=range(1, 11)).astype(int).to_numpy()
    out["segment"] = segment.to_numpy()
    out["intervention"] = out["segment"].map(rules.INTERVENTIONS)
    return out.sort_values("risk_non_attendance", ascending=False).reset_index(drop=True)
