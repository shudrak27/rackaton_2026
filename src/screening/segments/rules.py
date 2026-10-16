"""Rule-based segments from the hypotheses on slide 8. They are HYPOTHESES to be checked
against the data (size, non-attendance rate, mean predicted risk), not final segments.

Segments are assigned in priority order; the first matching rule wins.
"""

import numpy as np
import pandas as pd

from screening.data import schema as s

INTERVENTIONS = {
    "recently_screened": "nezasílat / odložit pozvánku (screening proběhl nedávno)",
    "first_invitation": "standardní pozvánka (kontrolní skupina / nízká intenzita)",
    "repeated_nonresponder": "jiný kanál, telefonická navigace, pomoc s objednáním",
    "lapsed_regular": "jednoduché připomenutí + konkrétní objednací krok",
    "care_no_prevention": "zapojení praktika nebo gynekologa",
    "low_contact": "vícekanálové oslovení + screening je důležitý i bez příznaků",
    "other": "standardní pozvánka + SMS připomenutí",
}
# Regional barrier ("navigace na dostupná pracoviště") needs external data on screening
# centre locations; add it as a rule once a distance/accessibility column exists.


def _col(df: pd.DataFrame, name: str, default=np.nan) -> pd.Series:
    return df[name] if name in df.columns else pd.Series(default, index=df.index)


def assign(df: pd.DataFrame, cfg: dict) -> pd.Series:
    c = cfg["segments"]
    prior_inv = _col(df, s.N_PRIOR_INVITATIONS)
    screens = _col(df, s.N_SCREENINGS_5Y)
    months = _col(df, s.MONTHS_SINCE_LAST)
    contacts = _col(df, s.N_HEALTHCARE_CONTACTS)
    prevent = _col(df, s.N_PREVENTIVE_VISITS)
    # unknown registration stays unknown (NaN), it is not evidence of having no doctor
    regs = _col(df, s.HAS_GP).astype(float) + _col(df, s.HAS_GYN).astype(float)

    rules = [
        ("recently_screened", months <= c["recent_max_months"]),
        ("first_invitation", prior_inv == 0),
        ("lapsed_regular", (screens >= c["lapsed_min_screenings_5y"]) & (months > c["lapsed_min_months"])),
        # behavioural barriers before the generic "repeated" rule: they say WHY, not only THAT
        ("low_contact", (contacts <= c["low_contact_max_contacts"]) | (regs == 0)),
        ("care_no_prevention", (contacts >= c["care_min_contacts"]) & (prevent == 0)),
        ("repeated_nonresponder", (prior_inv >= c["repeated_min_invitations"]) & (screens == 0)),
    ]
    seg = pd.Series("other", index=df.index)
    assigned = pd.Series(False, index=df.index)
    for name, cond in rules:
        hit = cond.fillna(False).astype(bool) & ~assigned
        seg[hit] = name
        assigned |= hit
    return seg


def report(segment: pd.Series, y: np.ndarray, risk: np.ndarray) -> pd.DataFrame:
    df = pd.DataFrame({"segment": segment.to_numpy(), "y": np.asarray(y), "risk": np.asarray(risk)})
    t = df.groupby("segment").agg(n=("y", "size"), non_attendance=("y", "mean"),
                                  mean_predicted_risk=("risk", "mean"))
    t["share"] = t["n"] / t["n"].sum()
    t["intervention"] = t.index.map(INTERVENTIONS)
    return t.sort_values("non_attendance", ascending=False).reset_index()
