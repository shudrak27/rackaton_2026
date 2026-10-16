"""Synthetic stand-in for the VZP dataset, used until the real data arrives.

Clients are simulated year by year so that history features (prior invitations, screenings in
the last 5 years, months since last screening) are consistent across a client's rows. The
intercept is tuned to roughly reproduce slide 4: ~19 % overall attendance, ~45 % for first
invitations, a few percent for clients invited many times.
"""

import numpy as np
import pandas as pd

from screening.data import schema as s

REGIONS = ["PHA", "STC", "JHC", "PLK", "KVK", "ULK", "LBK",
           "HKK", "PAK", "VYS", "JHM", "OLK", "ZLK", "MSK"]
HISTORY_YEARS = 5


def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def generate(n_clients: int = 80_000, first_year: int = 2019, last_year: int = 2024,
             burn_in: int = 8, seed: int = 42) -> pd.DataFrame:
    """Simulates `burn_in` unobserved years first so the output years are in a steady state
    (a mix of first-time and long-term invitees); only `first_year..last_year` are returned."""
    rng = np.random.default_rng(seed)
    n = n_clients

    latent = rng.normal(0, 1, n)  # unobserved "health engagement"
    start = first_year - burn_in
    # Younger clients turn 45 during the simulation -> a steady inflow of first invitations
    age = rng.integers(45 - (last_year - start), 75, n).astype(float)
    region_idx = rng.integers(0, len(REGIONS), n)
    region_effect = rng.normal(0, 0.3, len(REGIONS))[region_idx]

    has_gp = rng.random(n) < _sigmoid(1.8 + 0.6 * latent)
    has_gyn = rng.random(n) < _sigmoid(0.4 + 0.9 * latent)
    gp_years = np.where(has_gp, rng.gamma(2.0, 6.0, n), 0.0)
    gyn_years = np.where(has_gyn, rng.gamma(2.0, 5.0, n), 0.0)

    # screened[:, j] = screened in calendar year (first_year - HISTORY_YEARS + j)
    years = np.arange(start - HISTORY_YEARS, last_year + 1)
    screened = np.zeros((n, len(years)), dtype=bool)
    # Initial history: engaged clients aged 50+ screened every 2 years, random phase
    phase = rng.integers(0, 2, n)
    p_hist = _sigmoid(-0.8 + 1.2 * latent) * (age >= 50)
    for j in range(HISTORY_YEARS):
        screened[:, j] = (rng.random(n) < p_hist) & (j % 2 == phase)

    n_prior_inv = np.zeros(n, dtype=int)
    consecutive_noresp = np.zeros(n, dtype=int)
    invited_last_year = rng.random(n) < 0.5
    rows = []

    for y in range(start, last_year + 1):
        j = y - years[0]
        last5 = screened[:, j - HISTORY_YEARS:j]
        n_screen5 = last5.sum(axis=1)
        recent = screened[:, j - 2:j].any(axis=1)
        any_ever = screened[:, :j].any(axis=1)
        last_idx = np.where(any_ever, j - 1 - np.argmax(screened[:, :j][:, ::-1], axis=1), -1)
        months_since = np.where(any_ever, (j - last_idx) * 12 - rng.integers(0, 12, n), np.nan)

        # 2-year screening interval: invite if not screened and not invited in the last 2 years
        invited = (age >= 45) & ~recent & ~invited_last_year & (rng.random(n) < 0.9)
        n_contacts = rng.poisson(np.exp(1.2 + 0.3 * latent + 0.02 * (age - 55)))
        n_prev = rng.poisson(np.exp(-0.2 + 0.7 * latent))
        cervical = rng.random(n) < _sigmoid(-0.5 + 1.0 * latent + 0.8 * has_gyn)
        colorectal = rng.random(n) < _sigmoid(-1.5 + 0.8 * latent + 0.03 * (age - 50))

        logit = (-1.6 + 0.9 * latent
                 + 0.5 * has_gyn + 0.2 * has_gp
                 + 0.25 * n_screen5
                 + 0.15 * np.minimum(n_prev, 4)
                 + 0.3 * cervical
                 + region_effect
                 - 0.02 * (age - 55)
                 - 0.6 * np.minimum(consecutive_noresp, 4)
                 + 0.5 * (n_prior_inv == 0))
        attended = invited & (rng.random(n) < _sigmoid(logit))

        idx = np.flatnonzero(invited) if y >= first_year else np.array([], dtype=int)
        day = rng.integers(0, 365, idx.size)
        rows.append(pd.DataFrame({
            s.CLIENT_ID: idx,
            s.INVITATION_DATE: pd.Timestamp(f"{y}-01-01") + pd.to_timedelta(day, unit="D"),
            s.AGE: age[idx].astype(int),
            s.REGION: np.array(REGIONS)[region_idx[idx]],
            s.N_SCREENINGS_5Y: n_screen5[idx],
            s.MONTHS_SINCE_LAST: months_since[idx],
            s.N_PRIOR_INVITATIONS: n_prior_inv[idx],
            s.HAS_GP: has_gp[idx].astype(int),
            s.HAS_GYN: has_gyn[idx].astype(int),
            s.GP_REG_YEARS: gp_years[idx].round(1),
            s.GYN_REG_YEARS: gyn_years[idx].round(1),
            s.N_PREVENTIVE_VISITS: n_prev[idx],
            s.CERVICAL_SCREENING: cervical[idx].astype(int),
            s.COLORECTAL_SCREENING: colorectal[idx].astype(int),
            s.N_HEALTHCARE_CONTACTS: n_contacts[idx],
            s.ATTENDED: attended[idx].astype(int),
        }))

        # Advance state; attendees outside the programme (diagnostic mammography) are ignored
        screened[:, j] = attended
        n_prior_inv += invited
        invited_last_year = invited
        consecutive_noresp = np.where(attended, 0, consecutive_noresp + invited)
        age += 1
        gp_years += has_gp
        gyn_years += has_gyn

    df = pd.concat(rows, ignore_index=True)
    df[s.AGE_BAND] = pd.cut(df[s.AGE], [44, 49, 54, 59, 64, 69, 120],
                            labels=["45-49", "50-54", "55-59", "60-64", "65-69", "70+"]).astype(str)
    return df
