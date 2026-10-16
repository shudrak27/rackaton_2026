// Human-readable labels; keep in sync with app/dashboard.py.

export const SEGMENTS = {
  first_invitation: "First invitation",
  lapsed_regular: "Last screening over 2 years ago",
  other: "Other",
  repeated_nonresponder: "Repeated non-responder",
  care_no_prevention: "In care, no prevention",
  low_contact: "Low contact with healthcare",
  recently_screened: "Recently screened",
};

export const FEATURES = {
  n_prior_invitations: "Previous invitations",
  invitation_sequence: "Invitations since last screening",
  gyn_prevention_24m: "Gynaecologist check-ups (24 m)",
  other_screening_36m: "Other cancer screenings (36 m)",
  n_healthcare_contacts: "Healthcare contacts (12 m)",
  dental_prevention_24m: "Dental check-ups (24 m)",
  region: "VZP territorial office",
  months_since_last_screening: "Months since last screening",
  months_since_last_invitation: "Months since last invitation",
  age_band: "Age band",
  first_invitation: "First invitation",
  recently_screened: "Screened in last 6 months",
  has_gyn: "Registered with gynaecologist",
  has_gp: "Registered with general practitioner",
  insurance_years: "Years insured with VZP",
  n_preventive_visits: "General practitioner and gynaecologist check-ups (24 m)",
};

export const BREAKDOWNS = {
  prior_invitations: "Previous invitations",
  age_band: "Age band",
  healthcare_contacts_12m: "Healthcare contacts in last 12 months",
  gyn_prevention_24m: "Gynaecologist check-ups in last 24 months",
  other_screening_36m: "Other cancer screenings in last 36 months",
  months_since_last_screening: "Months since last screening",
  year: "Invitation year",
};

export const pct = (x, d = 1) => (x == null ? "–" : `${(x * 100).toFixed(d)}%`);
export const num = (x) => (x == null ? "–" : Math.round(x).toLocaleString("en-US"));
