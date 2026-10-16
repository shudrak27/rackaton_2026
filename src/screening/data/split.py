import pandas as pd
from sklearn.model_selection import GroupKFold

from screening.data import schema as s


def temporal_split(df: pd.DataFrame, test_year: int,
                   purge_months: int = 0) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Out-of-time split: train on invitations before `test_year`, test on `test_year`.

    The same client can appear in both (that is the realistic deployment setting), but no
    information from the test year leaks into training rows. With purge_months = outcome
    window, train keeps only invitations whose outcome was already known on 1 January of the
    test year, i.e. exactly what a model trained at that moment could have used.
    """
    test_start = pd.Timestamp(f"{test_year}-01-01")
    known = df[s.INVITATION_DATE] + pd.DateOffset(months=purge_months) <= test_start
    train = df[(df[s.INVITATION_YEAR] < test_year) & known].reset_index(drop=True)
    test = df[df[s.INVITATION_YEAR] == test_year].reset_index(drop=True)
    if train.empty or test.empty:
        raise ValueError(f"Empty split for test_year={test_year}; "
                         f"years available: {sorted(df[s.INVITATION_YEAR].unique())}")
    return train, test


def group_folds(df: pd.DataFrame, n_folds: int) -> list[tuple]:
    """CV folds inside train; all rows of a client fall into the same fold."""
    return list(GroupKFold(n_splits=n_folds).split(df, groups=df[s.CLIENT_ID]))
