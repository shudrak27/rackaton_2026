"""Rule baseline the ML model has to beat.

Risk increases with previous invitations and decreases by 0.1 per recorded screening
procedure in the last five years. This is a ranking score, not a probability.
"""

import numpy as np
import pandas as pd

from screening.data import schema as s


def baseline_score(df: pd.DataFrame) -> np.ndarray:
    score = np.zeros(len(df))
    if s.N_PRIOR_INVITATIONS in df.columns:
        score += df[s.N_PRIOR_INVITATIONS].fillna(0).to_numpy(dtype=float)
    if s.N_SCREENINGS_5Y in df.columns:
        # tie-break: fewer recent screenings -> higher risk
        score -= 0.1 * df[s.N_SCREENINGS_5Y].fillna(0).to_numpy(dtype=float)
    return score
