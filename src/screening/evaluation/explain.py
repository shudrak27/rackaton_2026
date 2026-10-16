"""Feature contributions via LightGBM's built-in TreeSHAP (pred_contrib), no extra dependency.

Contributions are associations learned by the model, not causal effects.
"""

import lightgbm as lgb
import numpy as np
import pandas as pd


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


def importance(model: lgb.LGBMClassifier, X: pd.DataFrame, sample: int = 50_000,
               seed: int = 0) -> pd.DataFrame:
    Xs = X.sample(min(sample, len(X)), random_state=seed)
    sv = shap_values(model, Xs)
    out = pd.DataFrame({
        "feature": sv.columns,
        "mean_abs_shap": sv.abs().mean().to_numpy(),
        "direction": [_direction(Xs[c], sv[c]) for c in sv.columns],
        "gain": model.booster_.feature_importance("gain"),
    })
    return out.sort_values("mean_abs_shap", ascending=False).reset_index(drop=True)
