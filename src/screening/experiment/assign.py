"""Reproducible allocation within strata and pairwise checks of pre-treatment balance."""

from itertools import combinations

import numpy as np
import pandas as pd


def assign_arms(df: pd.DataFrame, strata: list[str], arms: dict[str, float],
                seed: int) -> pd.Series:
    """Permute one allocation block per stratum; counts differ from n * share by < 1.

    The seed reproduces assignments for the same input row order. Missing stratum
    values form their own strata. Each row must be one randomization unit; when
    client_id is present, repeated or missing clients are rejected. Risk quantiles
    must be constructed by the caller before passing their column in strata.
    """
    if len(arms) < 2:
        raise ValueError("at least two arms are required")
    weights = np.asarray(list(arms.values()), dtype=float)
    if (not np.isfinite(weights).all() or (weights < 0).any()
            or not np.isclose(weights.sum(), 1, rtol=0, atol=1e-10)):
        raise ValueError("arm shares must be finite, nonnegative and sum to 1")
    if any(not isinstance(name, str) or not name for name in arms):
        raise ValueError("arm names must be nonempty strings")
    if len(set(strata)) != len(strata):
        raise ValueError("strata must contain unique column names")
    if "client_id" in df and (df["client_id"].isna().any() or df["client_id"].duplicated().any()):
        raise ValueError("randomize one row per nonmissing client_id")
    rng = np.random.default_rng(seed)
    names = np.asarray(list(arms), dtype=object)
    weights = weights / weights.sum()
    result = np.empty(len(df), dtype=object)
    groups = (df[strata].astype(object).groupby(strata, dropna=False, sort=False).indices.values()
              if strata else [np.arange(len(df))])
    for positions in groups:
        expected = len(positions) * weights
        counts = np.floor(expected).astype(int)
        remaining = len(positions) - counts.sum()
        # Random tie-breaking prevents the same arm from always winning tiny strata.
        order = rng.permutation(len(names))
        order = order[np.argsort(-(expected - counts)[order], kind="stable")]
        counts[order[:remaining]] += 1
        result[positions] = rng.permutation(np.repeat(names, counts))
    return pd.Series(result, index=df.index, name="arm", dtype="str")


def balance_table(df: pd.DataFrame, arm_col: str, covariates: list[str]) -> pd.DataFrame:
    """Compare every arm pair: means and signed standardized mean differences.

    Numeric missing values are omitted per covariate. Categorical covariates are
    expanded into indicators, including a missing level. The denominator is the
    square root of the mean of the two sample variances. A zero denominator gives
    SMD 0 for equal means and signed infinity otherwise; n < 2 gives NaN.
    """
    columns = ["covariate", "level", "arm", "reference", "n", "n_reference",
               "mean", "mean_reference", "smd"]
    if df[arm_col].isna().any():
        raise ValueError("arm assignments must not be missing")
    rows = []
    for covariate in covariates:
        values = df[covariate]
        if pd.api.types.is_numeric_dtype(values):
            numeric = values.astype(float)
            if np.isinf(numeric.to_numpy()).any():
                raise ValueError("covariates must not contain infinite values")
            indicators = [(None, numeric)]
        else:
            indicators = [(level, (values.isna() if pd.isna(level) else values.eq(level))
                           .fillna(False).astype(float)) for level in pd.unique(values)]
        for reference, arm in combinations(pd.unique(df[arm_col]), 2):
            for level, indicator in indicators:
                x = indicator.loc[df[arm_col].eq(arm)].dropna()
                ref = indicator.loc[df[arm_col].eq(reference)].dropna()
                mean, mean_ref = x.mean(), ref.mean()
                delta = mean - mean_ref
                denom = np.sqrt((x.var(ddof=1) + ref.var(ddof=1)) / 2)
                smd = (delta / denom if denom > 0 else
                       (0.0 if delta == 0 else np.copysign(np.inf, delta)))
                if len(x) < 2 or len(ref) < 2:
                    smd = np.nan
                rows.append({"covariate": covariate, "level": level, "arm": arm,
                             "reference": reference, "n": len(x), "n_reference": len(ref),
                             "mean": mean, "mean_reference": mean_ref, "smd": smd})
    return pd.DataFrame(rows, columns=columns)
