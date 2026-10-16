# Segments on real VZP data

Computed on the full delivered extract: 1,344,556 invitations, 508,527 women,
2020–2024. One row is one invitation; one woman appears up to 5 times.
In 2024 one row corresponds to one unique woman.

Limitation: the cohort was selected for continuous VZP insurance in 2015–2025; transferability to
other groups is untested. Outcome: SCREENING_12M_FLAG = A within 365 days. The 3M/6M/12M flags are
not used to define individual behavioural segments.

## Hypotheses for discussion with the programme owner

| Segment | Definition on delivered columns |
| --- | --- |
| lapsed_regular | PRIOR_SCREEN_COUNT_5Y ≥ 1 and MONTHS_SINCE_LAST_SCREEN > 24 |
| low_contact | HEALTHCARE_CONTACT_12M_CNT ≤ 2 OR both GP_REGISTERED and GYN_REGISTERED_FLAG = N |
| care_no_prevention | HEALTHCARE_CONTACT_12M_CNT ≥ 6 and GP_PREVENTION_24M_CNT + GYN_PREVENTION_24M_CNT = 0 |
| repeated_nonresponder | PRIOR_INVITATION_COUNT − 1 ≥ 3 and PRIOR_SCREEN_COUNT_5Y = 0 |
| regional | VZP_TERRITORIAL_AREA is among the 20% of territories with the lowest attendance in 2020–2022 |

| Hypothesis | Invitations 2020–2024 | Women 2020–2024 | Attendance 2020–2024 | Women 2024 | Attendance 2024 |
| --- | --- | --- | --- | --- | --- |
| lapsed_regular | 204,426 | 138,948 | 34.42% | 32,533 | 35.60% |
| low_contact | 195,408 | 94,656 | 6.17% | 41,668 | 6.62% |
| care_no_prevention | 300,113 | 160,907 | 10.98% | 48,262 | 10.40% |
| repeated_nonresponder | 764,026 | 230,325 | 6.99% | 155,178 | 7.64% |
| regional | 363,000 | 131,844 | 17.14% | 69,927 | 17.44% |

These five hypotheses **overlap**: rows and women must not be added up across them.
Five-year rates are weighted by invitations, not by unique women. In `hypotheses_all_years.csv`
the intervals account for clustering by PERSON_ID; yearly Wilson intervals are in
`hypotheses_reporting_year.csv`.

`lapsed_regular` means screening history plus a gap; it does not prove regularity. Procedure codes are
not divided by two. `care_no_prevention` means no GP/GYN check-ups in 24 months only; dental and other
screenings are not excluded by this definition. `repeated_nonresponder` is a proxy, not proof of a
refusal of every letter. Zero procedures in five years is not the same as never screened.

## Regional hypothesis

The list of 15 territories was chosen once on 2020–2022 and then applied
to 2024. The 20% threshold is a research assumption, not a medical boundary.
Ties are ordered by territory name.

KARVINÁ; OLOMOUC; OSTRAVA; CHEB; KLADNO; MĚLNÍK; ÚSTÍ NAD LABEM; MLADÁ BOLESLAV; ROKYCANY; PRACHATICE; JINDŘICHŮV HRADEC; PROSTĚJOV; ŠUMPERK; PRAHA-HL.MĚSTO; TRUTNOV.

These are VZP territorial offices, not exact places of residence and not a measure of accessibility.
A crude attendance ranking without adjustment for age and invitation history does not prove a regional
barrier. The full ranking of all 75 territories for 2024 with counts and 95% Wilson CIs is saved in
`reports/eda/regions_reporting_year.csv`, the chart in `reports/figures/regions_ranking.png`.
Intervals are pointwise: no correction for 75 comparisons or rank uncertainty.
The selected territories are not redefined using 2024 outcomes.

## Non-overlapping groups for A/B planning

The current production rule order is used:
`recently_screened → first_invitation → lapsed_regular → low_contact → care_no_prevention
→ repeated_nonresponder → other`. For planning only, the regional list is applied to the remaining
`other`, forming `regional`; the rules in `segments/rules.py` are unchanged.

| Segment | Unique women 2024 | Attendance | 95% Wilson CI |
| --- | --- | --- | --- |
| recently_screened | 7,590 | 2.37% | 2.05%–2.74% |
| first_invitation | 37,463 | 55.09% | 54.58%–55.59% |
| lapsed_regular | 27,888 | 33.36% | 32.81%–33.92% |
| low_contact | 36,257 | 4.51% | 4.30%–4.73% |
| care_no_prevention | 39,893 | 7.29% | 7.04%–7.55% |
| repeated_nonresponder | 87,453 | 9.61% | 9.41%–9.80% |
| regional | 5,566 | 31.69% | 30.48%–32.93% |
| other | 14,356 | 30.88% | 30.13%–31.64% |

Total: 256,466 unique women. The regional residual group can have relatively
high attendance because the behavioural segments were already removed from it. Its name must not be read
as evidence of a low individual probability of attendance.

The core defines a first invitation as PRIOR_INVITATION_COUNT − 1 = 0. The EDA keeps the delivered
FIRST_INVITATION separately; the disagreement in 58 rows of
the extract is not silently corrected. Thresholds come from the project config and were not tuned on the
test year. Yearly outcomes are used here for description and planning of a future experiment.

## Invitations shortly after a screening

| Year | Letters at 0–1 months | Letters at 0–6 months | Attendance 0–6 months | Scenario cost 0–6 months, CZK |
| --- | --- | --- | --- | --- |
| 2020 | 5,972 | 6,084 | 2.17% | 182,520 |
| 2021 | 8,111 | 8,413 | 2.31% | 252,390 |
| 2022 | 7,321 | 7,478 | 2.26% | 224,340 |
| 2023 | 6,766 | 6,830 | 2.62% | 204,900 |
| 2024 | 7,503 | 7,590 | 2.37% | 227,700 |

Cost per letter: **30 CZK — placeholder** `eda.letter_cost_czk`, not a
confirmed VZP tariff. The 0–1 window is contained in 0–6; costs must not be added up. This is a gross
scenario cost of letters, not proven savings. Before cancelling or postponing invitations, the code
meaning, procedure date, current invitation criteria and the decision of the programme owner must be
checked. This analysis does not cancel any invitations.

## Reproduction

Run `notebooks/01_eda.ipynb`, then `python notebooks/write_reports.py`.
Computations: `screening.evaluation.real_data`. All CSVs and PNGs are local and excluded from Git.
The notebook is committed without outputs. SHA-256 of the source CSV: `a75c5aa9f56d1d1526bf5ded005828c3c7318beee5ec89f477a7e24cda02033a`.
