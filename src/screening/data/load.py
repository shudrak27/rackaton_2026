import pandas as pd

from screening.config import resolve
from screening.data import schema as s
from screening.data import vzp

_YES = {"1", "ano", "a", "yes", "y", "true"}
_NO = {"0", "ne", "n", "no", "false"}


def load_raw(cfg: dict) -> pd.DataFrame:
    """Reads csv/parquet; the VZP export is detected by its column names and converted."""
    path = resolve(cfg["data"]["path"])
    if path.suffix == ".parquet":
        df = pd.read_parquet(path)
    else:
        df = pd.read_csv(path, sep=None, engine="python", nrows=5)
        if vzp.is_vzp(df):
            return vzp.read(path)
        df = pd.read_csv(path, sep=None, engine="python")
    if vzp.is_vzp(df):
        return vzp.to_canonical(df)
    return df.rename(columns=cfg.get("columns") or {})


def _binary_target(col: pd.Series) -> pd.Series:
    """0/1 or yes/no strings; anything else (missing, typos, 0.5, 2) is an error, not a 0."""
    if pd.api.types.is_numeric_dtype(col) and not pd.api.types.is_bool_dtype(col):
        ok = col.isin([0, 1])
        values = col
    else:
        text = col.astype("string").str.strip().str.lower()
        ok = text.isin(_YES | _NO) | col.isin([True, False])
        values = text.isin(_YES) | col.isin([True])
    if not ok.all():
        bad = col[~ok].astype(str).unique()[:5].tolist()
        raise ValueError(f"{col.name}: {int((~ok).sum())} invalid target values, e.g. {bad}")
    return values.astype(int)


def prepare(df: pd.DataFrame, cfg: dict, require_target: bool = True) -> pd.DataFrame:
    """Validate, normalise types, add the modelling target and drop invitations whose
    outcome window is not closed yet.

    require_target=False is for scoring new invitations: an outcome column is ignored and
    no rows are filtered."""
    required = s.REQUIRED if require_target else [c for c in s.REQUIRED if c != s.ATTENDED]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns {missing}; fix `columns` mapping in config")

    df = df.copy()
    df[s.INVITATION_DATE] = pd.to_datetime(df[s.INVITATION_DATE])
    df[s.INVITATION_YEAR] = df[s.INVITATION_DATE].dt.year
    if not require_target:
        return df.drop(columns=[c for c in s.TARGETS if c in df.columns]).reset_index(drop=True)

    df[s.ATTENDED] = _binary_target(df[s.ATTENDED])
    df[s.TARGET] = 1 - df[s.ATTENDED]

    # Invitations younger than the outcome window have an incomplete (too optimistic) target.
    cutoff = cfg["data"].get("cutoff_date")
    if cutoff:
        window = pd.DateOffset(months=cfg["data"]["outcome_window_months"])
        df = df[df[s.INVITATION_DATE] + window <= pd.Timestamp(cutoff)]
    return df.reset_index(drop=True)


def load(cfg: dict) -> pd.DataFrame:
    return prepare(load_raw(cfg), cfg)
