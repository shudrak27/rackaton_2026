"""Analyze attendance by randomized assignment (ITT), and simulate demonstration outcomes.

Never filter by delivery, response or compliance. Outcomes must be fully observed
binary attendance: 1 = screened. For scored_test.y, pass a new column 1 - y.
"""

import numpy as np
import pandas as pd
from scipy.stats import norm


def analyze(df: pd.DataFrame, arm_col: str, outcome_col: str,
            control: str = "control", by: str | None = None, *,
            unit_col: str = "client_id") -> pd.DataFrame:
    """Each treatment versus control: attendance, effect in pp, Wald 95% CI and z-test.

    relative_effect is the fractional increase (0.25 means +25%), undefined when
    control attendance is zero. CIs are unpooled Wald intervals clipped to [-100,
    100] pp; p-values use the pooled null variance and are not multiplicity-adjusted.
    Subgroups missing either comparison arm have NaN effects, not fabricated zeros.
    Missing outcomes raise: resolve follow-up before an ITT analysis.
    Supply one experiment and exactly one row per nonmissing randomization unit.
    Repeated units are rejected even across arms or subgroups, never deduplicated.
    If experiment_id is supplied, it must identify a single experiment.
    """
    columns = ([by] if by else []) + ["arm", "control", "n", "n_control",
               "attended", "attended_control", "attendance", "attendance_control",
               "difference_pp", "ci_low_pp", "ci_high_pp", "p_value", "relative_effect"]
    required = [unit_col, arm_col, outcome_col] + ([by] if by else [])
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"missing analysis columns: {missing}")
    units = df[unit_col]
    if (units.isna().any() or units.astype("string").str.strip().eq("").any()
            or units.duplicated().any()):
        raise ValueError(f"analyze one row per nonmissing, unique {unit_col}")
    if "experiment_id" in df:
        experiments = df["experiment_id"]
        if (experiments.isna().any() or experiments.astype("string").str.strip().eq("").any()
                or experiments.nunique() != 1):
            raise ValueError("analyze one experiment_id at a time")
    if df[arm_col].isna().any() or not df[outcome_col].isin([0, 1]).all():
        raise ValueError("arms and binary attendance outcomes must be fully observed")
    if control not in df[arm_col].to_numpy():
        raise ValueError("control arm is absent")
    treatments = [arm for arm in pd.unique(df[arm_col]) if arm != control]
    groups = (df.groupby(df[by].astype(object), dropna=False, sort=False)
              if by else [(None, df)])
    rows = []
    for key, group in groups:
        ref = group.loc[group[arm_col].eq(control), outcome_col]
        n0, s0 = len(ref), int(ref.sum())
        p0 = s0 / n0 if n0 else np.nan
        for arm in treatments:
            outcomes = group.loc[group[arm_col].eq(arm), outcome_col]
            n, s = len(outcomes), int(outcomes.sum())
            p = s / n if n else np.nan
            delta = lo = hi = p_value = relative = np.nan
            if n and n0:
                delta = p - p0
                se = np.sqrt(p * (1 - p) / n + p0 * (1 - p0) / n0)
                lo, hi = np.clip([delta - norm.ppf(0.975) * se,
                                  delta + norm.ppf(0.975) * se], -1, 1)
                pooled = (s + s0) / (n + n0)
                null_se = np.sqrt(pooled * (1 - pooled) * (1 / n + 1 / n0))
                p_value = float(2 * norm.sf(abs(delta / null_se))) if null_se else 1.0
                relative = delta / p0 if p0 else np.nan
            row = {"arm": arm, "control": control, "n": n, "n_control": n0,
                   "attended": s, "attended_control": s0, "attendance": p,
                   "attendance_control": p0, "difference_pp": 100 * delta,
                   "ci_low_pp": 100 * lo, "ci_high_pp": 100 * hi,
                   "p_value": p_value, "relative_effect": relative}
            if by:
                row[by] = key
            rows.append(row)
    return pd.DataFrame(rows, columns=columns)


def simulate_outcomes(df: pd.DataFrame, arm_col: str, base_p_col: str,
                      uplift_pp: dict[str, float], seed: int) -> pd.Series:
    """Draw attendance with p = baseline + arm uplift / 100, clipped to [0, 1].

    baseline is ATTENDANCE probability, not non-attendance risk. Every observed arm
    must have an explicit effect, including 0 for control. Effects are assumptions.
    """
    base = df[base_p_col].to_numpy(dtype=float)
    if not np.isfinite(base).all() or ((base < 0) | (base > 1)).any():
        raise ValueError("baseline attendance probabilities must be in [0, 1]")
    effects = np.asarray(list(uplift_pp.values()), dtype=float)
    if not np.isfinite(effects).all() or (np.abs(effects) > 100).any():
        raise ValueError("uplift_pp must be finite percentage points in [-100, 100]")
    uplift = df[arm_col].map(uplift_pp)
    if df[arm_col].isna().any() or uplift.isna().any():
        raise ValueError("an explicit uplift is required for every observed arm")
    probabilities = np.clip(base + uplift.to_numpy(dtype=float) / 100, 0, 1)
    return pd.Series(np.random.default_rng(seed).binomial(1, probabilities),
                     index=df.index, name="attended_12m")
