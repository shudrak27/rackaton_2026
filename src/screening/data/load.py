import pandas as pd

from screening.config import resolve
from screening.data import schema as s

_YES = {"1", "ano", "a", "yes", "y", "true"}


def load_raw(cfg: dict) -> pd.DataFrame:
    path = resolve(cfg["data"]["path"])
    if path.suffix == ".parquet":
        df = pd.read_parquet(path)
    else:
        df = pd.read_csv(path, sep=None, engine="python")
    return df.rename(columns=cfg.get("columns") or {})


def prepare(df: pd.DataFrame, cfg: dict, require_target: bool = True) -> pd.DataFrame:
    """Validate, normalise types, add the modelling target and drop invitations whose
    outcome window is not closed yet.

    require_target=False is for scoring new invitations, which have no outcome yet."""
    required = s.REQUIRED if require_target else [c for c in s.REQUIRED if c != s.ATTENDED]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns {missing}; fix `columns` mapping in config")

    df = df.copy()
    df[s.INVITATION_DATE] = pd.to_datetime(df[s.INVITATION_DATE])
    df[s.INVITATION_YEAR] = df[s.INVITATION_DATE].dt.year
    if s.ATTENDED not in df.columns:
        return df.reset_index(drop=True)
    if not pd.api.types.is_numeric_dtype(df[s.ATTENDED]):
        df[s.ATTENDED] = df[s.ATTENDED].astype(str).str.strip().str.lower().isin(_YES)
    df[s.ATTENDED] = df[s.ATTENDED].astype(int)
    df[s.TARGET] = 1 - df[s.ATTENDED]

    # Invitations younger than the outcome window have an incomplete (too optimistic) target.
    cutoff = cfg["data"].get("cutoff_date")
    if cutoff:
        window = pd.DateOffset(months=cfg["data"]["outcome_window_months"])
        df = df[df[s.INVITATION_DATE] + window <= pd.Timestamp(cutoff)]
    return df.reset_index(drop=True)


def load(cfg: dict) -> pd.DataFrame:
    return prepare(load_raw(cfg), cfg)
