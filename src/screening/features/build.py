"""Feature engineering. Every derived feature is built only if its source columns exist,
so the same code runs on synthetic data and on whatever subset VZP delivers.

All features must describe the client AS OF THE INVITATION DATE. Anything measured later
belongs in `features.exclude` in the config; excluded columns are also not used to derive
other features.
"""

import numpy as np
import pandas as pd

from screening.data import schema as s


def _has(df: pd.DataFrame, *cols: str) -> bool:
    return all(c in df.columns for c in cols)


def add_derived(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if _has(df, s.N_SCREENINGS_5Y) and s.NEVER_SCREENED not in df.columns:
        df[s.NEVER_SCREENED] = (df[s.N_SCREENINGS_5Y] == 0).astype(int)
    if _has(df, s.N_PRIOR_INVITATIONS):
        df["first_invitation"] = (df[s.N_PRIOR_INVITATIONS] == 0).astype(int)
    if _has(df, s.N_PRIOR_INVITATIONS, s.N_SCREENINGS_5Y):
        df["screenings_per_invitation"] = (
            df[s.N_SCREENINGS_5Y] / df[s.N_PRIOR_INVITATIONS].clip(lower=1))
    if _has(df, s.MONTHS_SINCE_LAST):
        df["overdue"] = (df[s.MONTHS_SINCE_LAST] > 24).astype(int)
        # VZP: ~2.7 % of invitations go to women screened 0-6 months earlier (attendance ~2 %)
        df["recently_screened"] = (df[s.MONTHS_SINCE_LAST] <= 6).astype(int)
    if _has(df, s.HAS_GP, s.HAS_GYN):
        # float: bool + bool would be a logical OR, and unknown must stay unknown
        df["n_registrations"] = df[s.HAS_GP].astype(float) + df[s.HAS_GYN].astype(float)
    if _has(df, s.GP_PREVENTION_24M, s.GYN_PREVENTION_24M) and s.N_PREVENTIVE_VISITS not in df.columns:
        df[s.N_PREVENTIVE_VISITS] = df[s.GP_PREVENTION_24M] + df[s.GYN_PREVENTION_24M]
    other = [c for c in (s.CERVICAL_SCREENING, s.COLORECTAL_SCREENING) if c in df.columns]
    if other:
        df["n_other_screenings"] = df[other].sum(axis=1)
    if _has(df, s.N_HEALTHCARE_CONTACTS, s.N_PREVENTIVE_VISITS):
        df["preventive_share"] = (
            df[s.N_PREVENTIVE_VISITS] / df[s.N_HEALTHCARE_CONTACTS].clip(lower=1))
    return df


def feature_columns(df: pd.DataFrame, cfg: dict) -> list[str]:
    excluded = set(s.KEYS) | set(s.TARGETS) | set(cfg["features"].get("exclude") or [])
    return [c for c in df.columns if c not in excluded]


def build(df: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, list[str]]:
    """Returns the frame with derived features and the list of model feature columns.

    Categoricals are cast on the full frame (before any split) so train and test share
    the same category codes.
    """
    excluded = [c for c in cfg["features"].get("exclude") or [] if c in df.columns]
    derived = add_derived(df.drop(columns=excluded))
    df = pd.concat([derived, df[excluded]], axis=1)
    cols = feature_columns(df, cfg)
    for c in cols:
        if df[c].dtype == bool:
            df[c] = df[c].astype(int)
        elif c in s.CATEGORICAL or not pd.api.types.is_numeric_dtype(df[c]):
            df[c] = df[c].astype(object).astype("category")
        elif isinstance(df[c].dtype, pd.api.extensions.ExtensionDtype):
            df[c] = df[c].astype("float64")  # nullable Int64 -> float with NaN for the models
    numeric = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
    df[numeric] = df[numeric].replace([np.inf, -np.inf], np.nan)
    return df, cols
