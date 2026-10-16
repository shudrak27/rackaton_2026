"""Sample size for the A/B test: control = standard invitation, treatment = segment intervention.
Two-sided test of two proportions, primary outcome = screening within 12 months (ITT)."""

import math

import pandas as pd
from scipy.stats import norm


def n_per_group(p_control: float, mde: float, alpha: float = 0.05, power: float = 0.8,
                ratio: float = 1.0) -> int:
    """Clients needed in the control arm; treatment arm = ratio * control.

    p_control: attendance under the standard invitation, mde: absolute uplift (0.02 = +2 p.p.).
    """
    p_t = p_control + mde
    if not 0 < p_control < 1 or not 0 < p_t < 1:
        raise ValueError("probabilities must be in (0, 1)")
    z_a, z_b = norm.ppf(1 - alpha / 2), norm.ppf(power)
    var = p_control * (1 - p_control) + p_t * (1 - p_t) / ratio
    return math.ceil((z_a + z_b) ** 2 * var / mde ** 2)


def design_table(segment_report: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """For each segment: required n per arm for each MDE and whether the segment is big enough
    (segment size from the test year ~ one yearly invitation wave)."""
    ec = cfg["experiment"]
    rows = []
    for _, r in segment_report.iterrows():
        p0 = 1 - r["non_attendance"]
        for mde_pp in ec["mde_pp"]:
            mde = mde_pp / 100
            if not 0 < p0 + mde < 1 or p0 <= 0:
                continue
            n = n_per_group(p0, mde, ec["alpha"], ec["power"])
            rows.append({"segment": r["segment"], "baseline_attendance": p0, "mde_pp": mde_pp,
                         "n_per_arm": n, "segment_size": r["n"], "feasible": 2 * n <= r["n"]})
    return pd.DataFrame(rows)
