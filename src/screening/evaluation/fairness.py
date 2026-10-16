"""Audit risk quality and representation in a GLOBAL outreach shortlist by group."""

import numpy as np
import pandas as pd
from scipy.stats import rankdata


def group_metrics(df: pd.DataFrame, y_col: str, score_col: str,
                  group_col: str, top_k: float = 0.2) -> pd.DataFrame:
    """y=1 means non-attendance; higher score means greater non-attendance risk.

    population_share = group size / all rows; top_k_share = selected in group /
    all selected; selection_rate = selected in group / group size. The shortlist
    uses max(1, round(n * top_k)) rows, stable input-order tie-breaking. Missing
    group labels are retained. AUC uses average ranks (half credit for ties), and
    is NaN for single-class groups. No sklearn or parallel runtime is needed.
    """
    columns = [group_col, "n", "non_attendance", "mean_risk", "roc_auc",
               "n_top_k", "top_k_share", "population_share", "selection_rate"]
    if not np.isfinite(top_k) or not 0 < top_k <= 1:
        raise ValueError("top_k must be in (0, 1]")
    if not df[y_col].isin([0, 1]).all():
        raise ValueError("non-attendance outcomes must be fully observed binary values")
    scores = df[score_col].to_numpy(dtype=float)
    if not np.isfinite(scores).all() or ((scores < 0) | (scores > 1)).any():
        raise ValueError("risk scores must be finite probabilities in [0, 1]")
    selected = np.zeros(len(df), dtype=bool)
    n_top = max(1, round(len(df) * top_k)) if len(df) else 0
    selected[np.argsort(-scores, kind="stable")[:n_top]] = True
    rows = []
    groups = df.groupby(df[group_col].astype(object), dropna=False, sort=False)
    for key, positions in groups.indices.items():
        y = df[y_col].iloc[positions].to_numpy(dtype=float)
        group_scores = scores[positions]
        n = len(positions)
        positives = int(y.sum())
        negatives = n - positives
        auc = np.nan
        if positives and negatives:
            ranks = rankdata(group_scores, method="average")
            auc = float((ranks[y == 1].sum() - positives * (positives + 1) / 2)
                        / (positives * negatives))
        count = int(selected[positions].sum())
        rows.append({group_col: key, "n": n, "non_attendance": float(y.mean()),
                     "mean_risk": float(group_scores.mean()), "roc_auc": auc,
                     "n_top_k": count, "top_k_share": count / n_top,
                     "population_share": n / len(df), "selection_rate": count / n})
    return pd.DataFrame(rows, columns=columns)
