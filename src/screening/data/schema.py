"""Canonical column names.

The VZP dataset (Rakathon_Datove_rozhrani.pdf) is converted to these names by
`screening.data.vzp`; other sources can be mapped via `columns` in configs/config.yaml.
Every feature column is optional: feature engineering and segmentation only use what is present.
"""

# Keys / time
CLIENT_ID = "client_id"
INVITATION_ID = "invitation_id"
INVITATION_DATE = "invitation_date"
INVITATION_YEAR = "invitation_year"

# Target as delivered: screening done within 12 months after the invitation (ANO/NE -> 1/0)
ATTENDED = "attended_12m"
# Modelling target: what we predict is the risk of NON-attendance
TARGET = "non_attendance"
# Shorter outcome windows. Measured AFTER the invitation -> never model inputs.
ATTENDED_3M = "attended_3m"
ATTENDED_6M = "attended_6m"

# Demographics
AGE = "age"
AGE_BAND = "age_band"
REGION = "region"
INSURANCE_YEARS = "insurance_years"

# Screening history
N_SCREENINGS_5Y = "n_screenings_5y"  # VZP: count of screening procedure codes (~2 per screening)
MONTHS_SINCE_LAST = "months_since_last_screening"
NEVER_SCREENED = "never_screened"  # VZP: no screening within the 5-year window
N_PRIOR_INVITATIONS = "n_prior_invitations"  # invitations BEFORE this one (0 = first)
INVITATION_SEQUENCE = "invitation_sequence"  # VZP: resets after attendance
MONTHS_SINCE_LAST_INVITATION = "months_since_last_invitation"

# Contact with the health system
HAS_GP = "has_gp"
HAS_GYN = "has_gyn"
GP_REG_YEARS = "gp_registration_years"
GYN_REG_YEARS = "gyn_registration_years"
GP_REG_BAND = "gp_registration_band"
GYN_REG_BAND = "gyn_registration_band"

# Preventive behaviour / utilisation
N_PREVENTIVE_VISITS = "n_preventive_visits"
GP_PREVENTION_24M = "gp_prevention_24m"
GYN_PREVENTION_24M = "gyn_prevention_24m"
DENTAL_PREVENTION_24M = "dental_prevention_24m"
OTHER_SCREENING_36M = "other_screening_36m"
CERVICAL_SCREENING = "cervical_screening"
COLORECTAL_SCREENING = "colorectal_screening"
N_HEALTHCARE_CONTACTS = "n_healthcare_contacts"

KEYS = [CLIENT_ID, INVITATION_ID, INVITATION_DATE, INVITATION_YEAR]
TARGETS = [ATTENDED, TARGET, ATTENDED_3M, ATTENDED_6M]
CATEGORICAL = [REGION, AGE_BAND, GP_REG_BAND, GYN_REG_BAND]
REQUIRED = [CLIENT_ID, INVITATION_DATE, ATTENDED]
