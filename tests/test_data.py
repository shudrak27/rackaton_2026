import pandas as pd
import pytest

from screening.data import schema as s
from screening.data.load import prepare
from screening.data.split import group_folds, temporal_split


def test_synthetic_resembles_slide_4(raw):
    assert 0.12 < raw[s.ATTENDED].mean() < 0.28
    first = raw.loc[raw[s.N_PRIOR_INVITATIONS] == 0, s.ATTENDED].mean()
    many = raw.loc[raw[s.N_PRIOR_INVITATIONS] >= 6, s.ATTENDED].mean()
    assert first > 0.35 and many < 0.10


def test_prepare_target_and_cutoff(raw, cfg):
    df = prepare(raw, cfg)
    assert (df[s.TARGET] == 1 - df[s.ATTENDED]).all()

    cut = {**cfg, "data": {**cfg["data"], "cutoff_date": "2024-06-30"}}
    df_cut = prepare(raw, cut)
    assert df_cut[s.INVITATION_DATE].max() <= pd.Timestamp("2023-06-30")


def test_prepare_accepts_ano_ne(raw, cfg):
    df = raw.head(10).copy()
    df[s.ATTENDED] = ["ANO", "NE"] * 5
    assert prepare(df, cfg)[s.ATTENDED].tolist() == [1, 0] * 5


def test_prepare_requires_columns(raw, cfg):
    with pytest.raises(ValueError):
        prepare(raw.drop(columns=[s.CLIENT_ID]), cfg)


def test_splits(prepared):
    train, test = temporal_split(prepared, 2024)
    assert train[s.INVITATION_YEAR].max() < 2024 <= test[s.INVITATION_YEAR].min()
    for tr, va in group_folds(train, 5):
        assert not set(train[s.CLIENT_ID].iloc[tr]) & set(train[s.CLIENT_ID].iloc[va])
