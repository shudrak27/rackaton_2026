"""Rule baseline the ML model has to beat.

Slide 4 shows attendance falls from 44.5 % (first invitation) to 3.2 % (invited for many
years), so "how many times was she invited already" alone is a strong risk score.
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
