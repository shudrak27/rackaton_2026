"""Metrics for a risk score where the positive class (non-attendance) is the MAJORITY (~81 %).

Because of that, lift on non-attendance is capped at ~1/0.81. The decile table (attendance
rate per risk decile) is the more telling view for choosing whom to target.
"""

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score


def _top_k_mask(score: np.ndarray, k: float) -> np.ndarray:
    n_top = max(int(round(len(score) * k)), 1)
    mask = np.zeros(len(score), dtype=bool)
    mask[np.argsort(-score, kind="stable")[:n_top]] = True
    return mask


def summary(y: np.ndarray, score: np.ndarray, top_k: list[float], is_proba: bool = True) -> dict:
    y = np.asarray(y)
    score = np.asarray(score, dtype=float)
    out = {"roc_auc": roc_auc_score(y, score), "average_precision": average_precision_score(y, score)}
    if is_proba:
        out["brier"] = brier_score_loss(y, score)
        out["log_loss"] = log_loss(y, np.clip(score, 1e-6, 1 - 1e-6))
    base = y.mean()
    for k in top_k:
        top = _top_k_mask(score, k)
        out[f"precision_top{int(k * 100)}"] = y[top].mean()
        out[f"lift_top{int(k * 100)}"] = y[top].mean() / base
        # share of all attendees we would "waste" an intervention on in the top-k
        out[f"attendance_top{int(k * 100)}"] = 1 - y[top].mean()
    return out


def decile_table(y: np.ndarray, score: np.ndarray, n_bins: int = 10) -> pd.DataFrame:
    df = pd.DataFrame({"y": np.asarray(y), "score": np.asarray(score, dtype=float)})
    df["decile"] = pd.qcut(df["score"].rank(method="first"), n_bins,
                           labels=range(1, n_bins + 1)).astype(int)
    t = df.groupby("decile").agg(n=("y", "size"), non_attendance=("y", "mean"),
                                 mean_score=("score", "mean"))
    t["attendance"] = 1 - t["non_attendance"]
    return t.reset_index()


def calibration_table(y: np.ndarray, proba: np.ndarray, n_bins: int = 10) -> pd.DataFrame:
    df = pd.DataFrame({"y": np.asarray(y), "p": np.asarray(proba, dtype=float)})
    df["bin"] = pd.cut(df["p"], np.linspace(0, 1, n_bins + 1), include_lowest=True)
    return (df.groupby("bin", observed=True)
              .agg(n=("y", "size"), predicted=("p", "mean"), observed=("y", "mean"))
              .reset_index().astype({"bin": str}))
