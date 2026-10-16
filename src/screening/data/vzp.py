"""Adapter for the VZP Rakathon 2026 export (Rakathon_Datove_rozhrani.pdf, version 29.9.2026).

One row = one addressed invitation (T0). Converts the raw CSV to the canonical schema:
renames columns, parses dd.mm.yyyy dates, turns A/N flags into 1/0 and shifts the invitation
count so that 0 means "first invitation" (VZP's PRIOR_INVITATION_COUNT includes the current one).

SCREENING_3M_FLAG / SCREENING_6M_FLAG are outcomes measured after T0; they are kept under
their own names for analysis but excluded from model inputs by the schema.
"""

import pandas as pd

from screening.data import schema as s

COLUMNS = {
    "INVITATION_ID": s.INVITATION_ID,
    "PERSON_ID": s.CLIENT_ID,
    "INVITATION_DATE": s.INVITATION_DATE,
    "AGE": s.AGE,
    "AGE_BAND": s.AGE_BAND,
    "VZP_TERRITORIAL_AREA": s.REGION,
    "PRIOR_INVITATION_COUNT": s.N_PRIOR_INVITATIONS,
    "INVITATION_SEQUENCE": s.INVITATION_SEQUENCE,
    "MONTHS_LAST_INVITATION": s.MONTHS_SINCE_LAST_INVITATION,
    "HEALTHCARE_CONTACT_12M_CNT": s.N_HEALTHCARE_CONTACTS,
    "INSURANCE_DURATION_YEARS": s.INSURANCE_YEARS,
    "GP_REGISTERED": s.HAS_GP,
    "GP_REG_DURATION_BAND": s.GP_REG_BAND,
    "GYN_REGISTERED_FLAG": s.HAS_GYN,
    "GYN_REG_DURATION_BAND": s.GYN_REG_BAND,
    "PRIOR_SCREEN_COUNT_5Y": s.N_SCREENINGS_5Y,
    "MONTHS_SINCE_LAST_SCREEN": s.MONTHS_SINCE_LAST,
    "NEVER_SCREENED_BEFORE_FLAG": s.NEVER_SCREENED,
    "GP_PREVENTION_24M_CNT": s.GP_PREVENTION_24M,
    "GYN_PREVENTION_24M_CNT": s.GYN_PREVENTION_24M,
    "OTHER_SCREENING_36M_CNT": s.OTHER_SCREENING_36M,
    "DENTAL_PREVENTION_24M_CNT": s.DENTAL_PREVENTION_24M,
    "SCREENING_3M_FLAG": s.ATTENDED_3M,
    "SCREENING_6M_FLAG": s.ATTENDED_6M,
    "SCREENING_12M_FLAG": s.ATTENDED,
}
FLAGS = [s.HAS_GP, s.HAS_GYN, s.NEVER_SCREENED, s.ATTENDED_3M, s.ATTENDED_6M, s.ATTENDED]
# Redundant with n_prior_invitations == 0 (differs in 58 of 1.34M rows)
DROP = ["FIRST_INVITATION"]
DATE_FORMAT = "%d.%m.%Y"


def _flag(col: pd.Series) -> pd.Series:
    values = col.astype("string").str.strip().str.upper()
    bad = values.notna() & ~values.isin(["A", "N"])
    if bad.any():
        raise ValueError(f"{col.name}: unexpected flag values {sorted(values[bad].unique())[:5]}")
    return values.map({"A": 1, "N": 0}).astype("Int64")


def is_vzp(df: pd.DataFrame) -> bool:
    return "PERSON_ID" in df.columns and "INVITATION_DATE" in df.columns


def to_canonical(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.drop(columns=[c for c in DROP if c in raw.columns]).rename(columns=COLUMNS)
    df[s.CLIENT_ID] = df[s.CLIENT_ID].astype(str)
    df[s.INVITATION_DATE] = pd.to_datetime(df[s.INVITATION_DATE], format=DATE_FORMAT)
    for c in FLAGS:
        if c in df.columns:
            df[c] = _flag(df[c])
    if s.N_PRIOR_INVITATIONS in df.columns:
        df[s.N_PRIOR_INVITATIONS] = df[s.N_PRIOR_INVITATIONS] - 1
    for c in (s.GP_REG_BAND, s.GYN_REG_BAND, s.AGE_BAND, s.REGION):
        if c in df.columns:
            df[c] = df[c].astype("string")
    return df


def read(path) -> pd.DataFrame:
    raw = pd.read_csv(path, dtype={"PERSON_ID": str, "INVITATION_ID": str}, encoding="utf-8")
    return to_canonical(raw)
