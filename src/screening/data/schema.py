"""Canonical column names.

Based on the data overview in the challenge deck (slide 11). The real VZP column names are
mapped onto these via `columns` in configs/config.yaml. Every feature column is optional:
feature engineering and segmentation only use what is present.
"""

# Keys / time
CLIENT_ID = "client_id"
INVITATION_DATE = "invitation_date"
INVITATION_YEAR = "invitation_year"

# Target as delivered: screening done within 12 months after the invitation (ANO/NE -> 1/0)
ATTENDED = "attended_12m"
# Modelling target: what we predict is the risk of NON-attendance
TARGET = "non_attendance"

# Demographics
AGE = "age"
AGE_BAND = "age_band"
REGION = "region"

# Screening history
N_SCREENINGS_5Y = "n_screenings_5y"
MONTHS_SINCE_LAST = "months_since_last_screening"
NEVER_SCREENED = "never_screened"
N_PRIOR_INVITATIONS = "n_prior_invitations"

# Contact with the health system
HAS_GP = "has_gp"
HAS_GYN = "has_gyn"
GP_REG_YEARS = "gp_registration_years"
GYN_REG_YEARS = "gyn_registration_years"

# Preventive behaviour / utilisation
N_PREVENTIVE_VISITS = "n_preventive_visits"
CERVICAL_SCREENING = "cervical_screening"
COLORECTAL_SCREENING = "colorectal_screening"
N_HEALTHCARE_CONTACTS = "n_healthcare_contacts"

KEYS = [CLIENT_ID, INVITATION_DATE, INVITATION_YEAR]
TARGETS = [ATTENDED, TARGET]
CATEGORICAL = [REGION, AGE_BAND]
REQUIRED = [CLIENT_ID, INVITATION_DATE, ATTENDED]
