"""Feature importance of the final model.

LightGBM: TreeSHAP via the built-in `pred_contrib` (no extra dependency).
Any other model (FLAML champion): permutation importance = drop in ROC-AUC when a column is
shuffled. Implemented by hand on purpose: sklearn's version goes through joblib/threadpoolctl,
which breaks on non-ASCII paths on Windows.

Both are associations learned by the model, not causal effects.
"""

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score


def shap_values(model: lgb.LGBMClassifier, X: pd.DataFrame) -> pd.DataFrame:
    contrib = model.predict(X, pred_contrib=True)
    return pd.DataFrame(contrib[:, :-1], columns=X.columns, index=X.index)  # last col = bias


def _direction(values: pd.Series, contrib: pd.Series) -> float:
    """+1 if higher feature values push the risk of non-attendance up, -1 if down."""
    if isinstance(values.dtype, pd.CategoricalDtype):
        return np.nan  # no natural order
    v = values.astype(float)
    ok = v.notna()
    if ok.sum() < 2 or v[ok].std() == 0 or contrib[ok].std() == 0:
        return 0.0
    return float(np.sign(np.corrcoef(v[ok], contrib[ok])[0, 1]))


def _shap_importance(model: lgb.LGBMClassifier, X: pd.DataFrame) -> pd.DataFrame:
    sv = shap_values(model, X)
    return pd.DataFrame({
        "feature": sv.columns,
        "importance": sv.abs().mean().to_numpy(),
        "direction": [_direction(X[c], sv[c]) for c in sv.columns],
        "method": "mean_abs_shap",
    })


def _permutation_importance(model, X: pd.DataFrame, y: pd.Series, seed: int,
                            n_repeats: int = 3) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    base = roc_auc_score(y, model.predict_proba(X)[:, 1])
    drops = []
    for c in X.columns:
        d = []
        for _ in range(n_repeats):
            Xp = X.copy()
            Xp[c] = X[c].iloc[rng.permutation(len(X))].set_axis(X.index)  # keeps dtype
            d.append(base - roc_auc_score(y, model.predict_proba(Xp)[:, 1]))
        drops.append(np.mean(d))
    return pd.DataFrame({"feature": X.columns, "importance": drops,
                         "direction": np.nan, "method": "permutation_auc_drop"})


def importance(model, X: pd.DataFrame, y: pd.Series, sample: int = 50_000,
               seed: int = 0) -> pd.DataFrame:
    Xs = X.sample(min(sample, len(X)), random_state=seed)
    if isinstance(model, lgb.LGBMClassifier):
        out = _shap_importance(model, Xs)
    else:
        out = _permutation_importance(model, Xs.iloc[:20_000], y.loc[Xs.index[:20_000]], seed)
    return out.sort_values("importance", ascending=False).reset_index(drop=True)
