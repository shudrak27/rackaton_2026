"""First look at a (new) dataset: column overview, target by year / prior invitations,
duplicates, and a leakage check.

Leakage check: ROC-AUC of every single feature against the target. A feature that predicts
non-attendance almost perfectly on its own (default > 0.95) is most likely measured AFTER the
invitation (e.g. "months since last screening" counted from the export date) and should go to
`features.exclude`.
"""

import pandas as pd
from sklearn.metrics import roc_auc_score

from screening.data import schema as s


def columns_overview(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
        "column": df.columns,
        "dtype": [str(t) for t in df.dtypes],
        "missing_share": df.isna().mean().to_numpy(),
        "n_unique": df.nunique().to_numpy(),
        "example": [df[c].dropna().iloc[0] if df[c].notna().any() else None for c in df.columns],
    })


def target_by(df: pd.DataFrame, col: str, clip: int | None = None) -> pd.DataFrame:
    key = df[col].clip(upper=clip) if clip is not None else df[col]
    return (df.groupby(key, observed=True)[s.ATTENDED].agg(n="size", attendance="mean")
              .reset_index())


def single_feature_auc(df: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    y = df[s.TARGET].to_numpy()
    rows = []
    for c in features:
        x = df[c]
        if isinstance(x.dtype, pd.CategoricalDtype) or not pd.api.types.is_numeric_dtype(x):
            # in-sample target encoding; slightly optimistic, fine for a warning
            key = x.astype(object).fillna("NA")
            x = key.map(df[s.TARGET].groupby(key).mean())
        x = x.astype(float)
        # missing as its own (lowest) value: "missing" itself can leak
        x = x.fillna(x.min() - 1 if x.notna().any() else 0)
        auc = roc_auc_score(y, x) if x.nunique() > 1 else 0.5
        rows.append({"feature": c, "auc": max(auc, 1 - auc), "missing_share": df[c].isna().mean()})
    return pd.DataFrame(rows).sort_values("auc", ascending=False).reset_index(drop=True)


def profile(df: pd.DataFrame, features: list[str]) -> dict[str, pd.DataFrame]:
    out = {
        "columns": columns_overview(df),
        "by_year": target_by(df, s.INVITATION_YEAR),
        "single_feature_auc": single_feature_auc(df, features),
    }
    if s.N_PRIOR_INVITATIONS in df.columns:
        out["by_prior_invitations"] = target_by(df, s.N_PRIOR_INVITATIONS, clip=10)
    dup = df.duplicated([s.CLIENT_ID, s.INVITATION_DATE], keep=False)
    per_year = df.groupby([s.CLIENT_ID, s.INVITATION_YEAR]).size()
    out["checks"] = pd.DataFrame([
        {"check": "rows", "value": len(df)},
        {"check": "clients", "value": df[s.CLIENT_ID].nunique()},
        {"check": "duplicate (client, date) rows", "value": int(dup.sum())},
        {"check": "clients invited >1x in a year", "value": int((per_year > 1).sum())},
        {"check": "attendance overall", "value": round(float(df[s.ATTENDED].mean()), 4)},
        {"check": "date min", "value": str(df[s.INVITATION_DATE].min().date())},
        {"check": "date max", "value": str(df[s.INVITATION_DATE].max().date())},
    ])
    return out


def leakage_suspects(auc_table: pd.DataFrame, threshold: float) -> list[str]:
    return auc_table.loc[auc_table["auc"] > threshold, "feature"].tolist()

