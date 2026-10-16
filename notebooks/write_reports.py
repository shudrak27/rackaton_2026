"""Render the two checked-in planning documents from aggregate notebook outputs.

Run after 01_eda.ipynb: python notebooks/write_reports.py.
No individual records are read or written by this script.
"""

import json
from pathlib import Path

import pandas as pd

from screening.experiment.power import n_per_group

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "reports/eda"


def table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    lines.extend("| " + " | ".join(map(str, row)) + " |" for row in rows)
    return "\n".join(lines)


def count(value):
    return f"{int(value):,}"


def rate(value):
    return f"{value:.2%}"


def main():
    manifest = json.loads((TABLES / "manifest.json").read_text(encoding="utf-8"))
    def read(name):
        return pd.read_csv(TABLES / f"{name}.csv")

    overview = read("overview").iloc[0]
    first_year, last_year = int(overview.first_year), int(overview.last_year)
    period = f"{first_year}–{last_year}"
    pooled = read("hypotheses_all_years").set_index("segment")
    annual = read("hypotheses_reporting_year").set_index("segment")
    exclusive = read("segments_exclusive")
    sizes = read("experiment_sizes")
    reference = read("regional_reference")
    selected = reference.loc[reference.selected, "VZP_TERRITORIAL_AREA"].tolist()
    year = manifest["reporting_year"]
    c = manifest["segments"]
    ec = manifest["experiment"]
    reference_end = manifest["eda"]["regional_reference_end_year"]
    fraction = manifest["eda"]["regional_bottom_fraction"]
    definitions = {
        "lapsed_regular": f"PRIOR_SCREEN_COUNT_5Y ≥ {c['lapsed_min_screenings_5y']} and MONTHS_SINCE_LAST_SCREEN > {c['lapsed_min_months']}",
        "low_contact": f"HEALTHCARE_CONTACT_12M_CNT ≤ {c['low_contact_max_contacts']} OR both GP_REGISTERED and GYN_REGISTERED_FLAG = N",
        "care_no_prevention": f"HEALTHCARE_CONTACT_12M_CNT ≥ {c['care_min_contacts']} and GP_PREVENTION_24M_CNT + GYN_PREVENTION_24M_CNT = 0",
        "repeated_nonresponder": f"PRIOR_INVITATION_COUNT − 1 ≥ {c['repeated_min_invitations']} and PRIOR_SCREEN_COUNT_5Y = 0",
        "regional": f"VZP_TERRITORIAL_AREA is among the {fraction:.0%} of territories with the lowest attendance in {first_year}–{reference_end}",
    }
    definitions_table = table(["Segment", "Definition on delivered columns"], definitions.items())
    hypothesis_table = table(
        ["Hypothesis", f"Invitations {period}", f"Women {period}", f"Attendance {period}", f"Women {year}", f"Attendance {year}"],
        [[name, count(pooled.loc[name, "n"]), count(pooled.loc[name, "clients"]),
          rate(pooled.loc[name, "attendance"]), count(annual.loc[name, "clients"]),
          rate(annual.loc[name, "attendance"])] for name in definitions])
    exclusive_table = table(
        ["Segment", f"Unique women {year}", "Attendance", "95% Wilson CI"],
        [[r.segment, count(r.clients), rate(r.attendance), f"{rate(r.ci_low)}–{rate(r.ci_high)}"]
         for r in exclusive.itertuples()])
    recent = read("recent_screening_cost")
    recent_table = table(["Year", "Letters at 0–1 months", "Letters at 0–6 months", "Attendance 0–6 months", "Scenario cost 0–6 months, CZK"],
                          [[int(y), count(part.loc[part.months_max.eq(1), "n"].iloc[0]),
                            count(part.loc[part.months_max.eq(6), "n"].iloc[0]),
                            rate(part.loc[part.months_max.eq(6), "attendance"].iloc[0]),
                            count(part.loc[part.months_max.eq(6), "scenario_gross_cost_czk"].iloc[0])]
                           for y, part in recent.groupby("year")])
    segments_doc = f"""# Segments on real VZP data

Computed on the full delivered extract: {count(overview.n)} invitations, {count(overview.clients)} women,
{period}. One row is one invitation; one woman appears up to {int(overview.max_invitations_per_client)} times.
In {year} one row corresponds to one unique woman.

Limitation: the cohort was selected for continuous VZP insurance in 2015–2025; transferability to
other groups is untested. Outcome: SCREENING_12M_FLAG = A within 365 days. The 3M/6M/12M flags are
not used to define individual behavioural segments.

## Hypotheses for discussion with the programme owner

{definitions_table}

{hypothesis_table}

These five hypotheses **overlap**: rows and women must not be added up across them.
Five-year rates are weighted by invitations, not by unique women. In `hypotheses_all_years.csv`
the intervals account for clustering by PERSON_ID; yearly Wilson intervals are in
`hypotheses_reporting_year.csv`.

`lapsed_regular` means screening history plus a gap; it does not prove regularity. Procedure codes are
not divided by two. `care_no_prevention` means no GP/GYN check-ups in 24 months only; dental and other
screenings are not excluded by this definition. `repeated_nonresponder` is a proxy, not proof of a
refusal of every letter. Zero procedures in five years is not the same as never screened.

## Regional hypothesis

The list of {len(selected)} territories was chosen once on {first_year}–{reference_end} and then applied
to {year}. The {fraction:.0%} threshold is a research assumption, not a medical boundary.
Ties are ordered by territory name.

{'; '.join(selected)}.

These are VZP territorial offices, not exact places of residence and not a measure of accessibility.
A crude attendance ranking without adjustment for age and invitation history does not prove a regional
barrier. The full ranking of all 75 territories for {year} with counts and 95% Wilson CIs is saved in
`reports/eda/regions_reporting_year.csv`, the chart in `reports/figures/regions_ranking.png`.
Intervals are pointwise: no correction for 75 comparisons or rank uncertainty.
The selected territories are not redefined using {year} outcomes.

## Non-overlapping groups for A/B planning

The current production rule order is used:
`recently_screened → first_invitation → lapsed_regular → low_contact → care_no_prevention
→ repeated_nonresponder → other`. For planning only, the regional list is applied to the remaining
`other`, forming `regional`; the rules in `segments/rules.py` are unchanged.

{exclusive_table}

Total: {count(exclusive.clients.sum())} unique women. The regional residual group can have relatively
high attendance because the behavioural segments were already removed from it. Its name must not be read
as evidence of a low individual probability of attendance.

The core defines a first invitation as PRIOR_INVITATION_COUNT − 1 = 0. The EDA keeps the delivered
FIRST_INVITATION separately; the disagreement in {count(overview.first_flag_counter_disagreements)} rows of
the extract is not silently corrected. Thresholds come from the project config and were not tuned on the
test year. Yearly outcomes are used here for description and planning of a future experiment.

## Invitations shortly after a screening

{recent_table}

Cost per letter: **{manifest['eda']['letter_cost_czk']:g} CZK — placeholder** `eda.letter_cost_czk`, not a
confirmed VZP tariff. The 0–1 window is contained in 0–6; costs must not be added up. This is a gross
scenario cost of letters, not proven savings. Before cancelling or postponing invitations, the code
meaning, procedure date, current invitation criteria and the decision of the programme owner must be
checked. This analysis does not cancel any invitations.

## Reproduction

Run `notebooks/01_eda.ipynb`, then `python notebooks/write_reports.py`.
Computations: `screening.evaluation.real_data`. All CSVs and PNGs are local and excluded from Git.
The notebook is committed without outputs. SHA-256 of the source CSV: `{manifest['sha256']}`.
"""
    size_table = table(
        ["Segment", "Control attendance (reference)", "MDE, pp", "Per arm", "Total", "Yearly women (reference)", "Fits at 100% recruitment"],
        [[r.segment, rate(r.baseline_attendance), f"{r.mde_pp:g}", count(r.n_control),
          count(r.n_total), count(r.available_clients), "yes" if r.feasible_at_full_recruitment else "no"]
         for r in sizes.itertuples()])
    primary = sizes.loc[sizes.segment.eq("lapsed_regular") & sizes.mde_pp.eq(2)].iloc[0]
    adjusted = table(["Segment", "Per arm at MDE = 2 pp, alpha = 0.01"],
                     [[r.segment, count(n_per_group(r.baseline_attendance, 0.02, alpha=0.01, power=ec['power']))]
                      for r in sizes.loc[sizes.mde_pp.eq(2)].itertuples()])
    timing = read("response_timing").set_index("horizon")
    experiment_doc = f"""# A/B test design on real VZP segments

This is the design of a future experiment, not its results and not permission to send messages.
Baseline rates and recruitment references come from {year}: one row = one woman. The data cohort is
continuous VZP insurance in 2015–2025; whether these rates apply to future recruitment, including new
clients, must be checked.

## Proposed first pilot

One pre-specified primary experiment in `lapsed_regular`: standard invitation versus standard invitation
plus one additional reminder with a clear booking step. The planned reminder day is day 14 after the
invitation; this is a hypothesis, not an EDA finding about the best day. SMS is allowed only after the
availability of contacts is confirmed and the programme owner agrees. Our CSV contains no contacts.

The randomisation unit is the woman, with one index invitation date and one experiment_id.
A woman must never be included twice, in different arms, or in several pilots at once.
An existing participant keeps her original assignment; she is not re-randomised.
Current invitation criteria and segment membership are checked before inclusion.
`recently_screened` is not included in any pilot that intensifies invitations without a separate review.

For this pilot the baseline attendance is {rate(primary.baseline_attendance)} and the target detectable
absolute effect is +2 pp (not +2% relative). It requires **{count(primary.n_control)} women per arm**,
**{count(primary.n_total)}** in total. The yearly segment had {count(primary.available_clients)} women;
the required coverage is about {rate(primary.required_recruitment_share)}. This is not a promise that this
many eligible women with a usable contact will be available next year, nor a forecast of the SMS effect.

## Randomisation and pre-registration

1:1 allocation within `segment × risk_quintile`, implemented by `experiment.assign.assign_arms`.
Before randomisation, freeze the model, transformations, segment rules and quintile boundaries on an
agreed reference sample. Risk is the probability of NON-attendance; the outcome is ATTENDANCE.
Identical risks should not be split arbitrarily between quintiles: with tied boundaries use fewer groups.
Small strata are merged by a pre-specified rule over neighbouring risk levels, never by future outcomes.
With a single pilot the segment is fixed and only the quintile strata remain; with several segments the
full product is used.

The EDA has no predictions of the frozen model; quintiles and assignments are not invented.
After scoring, a verifiable list of unique client_id, segment, risk_quintile, invitation_date is needed.
Before sending, store the seed, input row order, model version, rule version and assigned arm. Rerunning
on a changed population must not change assignments already issued. Sequential recruitment needs
persistent randomisation blocks; the current function suits a wave fixed in advance.

Check balance on age groups, territories, invitation history and contacts with healthcare;
`balance_table` reports standardised mean differences. Imbalance is not a reason to try seeds until the
result looks convenient. The content of the intervention is fixed in advance.

## Outcomes and analysis

Primary outcome: SCREENING_12M_FLAG, i.e. a screening within 365 days of the index invitation.
Secondary: SCREENING_3M_FLAG within 90 days. 6M may be shown descriptively.
In the source data attendance at 90/180/365 days is {rate(timing.loc[3, 'attendance'])} /
{rate(timing.loc[6, 'attendance'])} / {rate(timing.loc[12, 'attendance'])}. Flags are cumulative; they do not
give the exact response date or the optimal reminder date.

The primary effect is the difference in attendance treatment − control in percentage points, with a
two-sided 95% CI and a test at alpha={ec['alpha']:g}. ITT analysis keeps all randomised women regardless of
SMS delivery, response or actual participation. A missing recorded screening may be treated as 0 only
under complete follow-up; loss of insurance or an incomplete extract is not automatically non-attendance.
Unknown outcomes need a documented strategy and a sensitivity analysis, not removal from the denominator.

`experiment.analysis.analyze` requires a unique non-empty client_id (or an explicit unit_col), rejects
repeated records and mixed experiment_ids. Its input is attendance 0/1, not `scored_test.y`, which means
non-attendance. Unreachable women and undelivered messages are not filtered out. The pooled ITT contrast
within one segment is primary; results by quintile are exploratory and do not mean each quintile is
powered on its own. The current Wald intervals and z-test are large-sample approximations; rare events,
zero cells and small subgroups need a separate robust method before interpretation.

## Group sizes and feasibility

Computed with `experiment.power.n_per_group`: power={ec['power']:.0%}, two-sided alpha={ec['alpha']:g}, two
independent arms 1:1, absolute MDE. This is a normal approximation for planning, without corrections for
incomplete follow-up or changing baseline attendance.

{size_table}

Groups come from the non-overlapping planning split in the [segment description](segments-real-data.md).
Overlapping hypothesis tables must not be used for the same women at the same time. The five segment rows
are alternatives / separate pilots, not one shared control for five comparisons. Selecting on a usable
channel and current conditions will reduce the available numbers. For an eligible share q the yearly
reference is q × available_clients; for an observed-outcome share r the initial recruitment target is
ceil(n / r) per arm. This correction does not remove bias from missing outcomes; r and the missingness
mechanism must be justified.

If five confirmatory effects are claimed as one family, a simple conservative option is Bonferroni:
alpha = 0.05 / 5 = 0.01 per comparison. For example:

{adjusted}

These larger sizes replace, not add to, the sizes at alpha = 0.05. The first pilot above has one primary
effect; the secondary 90-day analysis is not a standalone confirmatory claim without a multiplicity plan.

## Timeline and stopping rules

Recruitment for one wave: up to 12 months; each woman is followed for 365 days. The final analysis comes
after the window of the last participant closes plus the agreed claims reporting delay. For example, with
one year of recruitment and an assumed 90-day delay this is about 27 months from the start. The 90-day
delay is a calendar assumption to be confirmed by VZP. The early 90-day outcome likewise needs complete
follow-up and data arrival.

Recruitment ends when the pre-computed size or a pre-set date is reached; under-recruitment is recorded
as a power limitation. One final analysis of the primary outcome. Reading p-values daily and stopping at
the first p < 0.05 is not allowed. Early efficacy analysis is possible only with a separately
pre-specified sequential design. Operational reasons for a pause: assignment errors, unusable contacts,
outcome recording failures, complaints/adverse effects or the decision of the programme owner. Women
already assigned stay in the ITT analysis and remain followed. Safety rules are fixed before the start.

## Reproduction and limitations

Run `notebooks/01_eda.ipynb`, then `python notebooks/write_reports.py`.
Full table: `reports/eda/experiment_sizes.csv`; source and configuration are recorded in
`reports/eda/manifest.json`. This code does not send letters, SMS or calls.
Regional accessibility, channel effectiveness and individual uplift are not established yet.
"""
    (ROOT / "docs/segments-real-data.md").write_text(segments_doc, encoding="utf-8")
    (ROOT / "docs/experiment-design.md").write_text(experiment_doc, encoding="utf-8")
    print("Updated docs/segments-real-data.md and docs/experiment-design.md from aggregate tables")


if __name__ == "__main__":
    main()
