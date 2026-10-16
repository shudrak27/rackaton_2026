# A/B test design on real VZP segments

This is the design of a future experiment, not its results and not permission to send messages.
Baseline rates and recruitment references come from 2024: one row = one woman. The data cohort is
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

For this pilot the baseline attendance is 33.36% and the target detectable
absolute effect is +2 pp (not +2% relative). It requires **8,848 women per arm**,
**17,696** in total. The yearly segment had 27,888 women;
the required coverage is about 63.45%. This is not a promise that this
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
In the source data attendance at 90/180/365 days is 7.12% /
12.54% / 19.30%. Flags are cumulative; they do not
give the exact response date or the optimal reminder date.

The primary effect is the difference in attendance treatment − control in percentage points, with a
two-sided 95% CI and a test at alpha=0.05. ITT analysis keeps all randomised women regardless of
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

Computed with `experiment.power.n_per_group`: power=80%, two-sided alpha=0.05, two
independent arms 1:1, absolute MDE. This is a normal approximation for planning, without corrections for
incomplete follow-up or changing baseline attendance.

| Segment | Control attendance (reference) | MDE, pp | Per arm | Total | Yearly women (reference) | Fits at 100% recruitment |
| --- | --- | --- | --- | --- | --- | --- |
| lapsed_regular | 33.36% | 1 | 35,153 | 70,306 | 27,888 | no |
| lapsed_regular | 33.36% | 2 | 8,848 | 17,696 | 27,888 | yes |
| lapsed_regular | 33.36% | 3 | 3,957 | 7,914 | 27,888 | yes |
| lapsed_regular | 33.36% | 5 | 1,441 | 2,882 | 27,888 | yes |
| low_contact | 4.51% | 1 | 7,470 | 14,940 | 36,257 | yes |
| low_contact | 4.51% | 2 | 2,041 | 4,082 | 36,257 | yes |
| low_contact | 4.51% | 3 | 982 | 1,964 | 36,257 | yes |
| low_contact | 4.51% | 5 | 406 | 812 | 36,257 | yes |
| care_no_prevention | 7.29% | 1 | 11,279 | 22,558 | 39,893 | yes |
| care_no_prevention | 7.29% | 2 | 2,982 | 5,964 | 39,893 | yes |
| care_no_prevention | 7.29% | 3 | 1,396 | 2,792 | 39,893 | yes |
| care_no_prevention | 7.29% | 5 | 551 | 1,102 | 39,893 | yes |
| repeated_nonresponder | 9.61% | 1 | 14,256 | 28,512 | 87,453 | yes |
| repeated_nonresponder | 9.61% | 2 | 3,717 | 7,434 | 87,453 | yes |
| repeated_nonresponder | 9.61% | 3 | 1,718 | 3,436 | 87,453 | yes |
| repeated_nonresponder | 9.61% | 5 | 665 | 1,330 | 87,453 | yes |
| regional | 31.69% | 1 | 34,263 | 68,526 | 5,566 | no |
| regional | 31.69% | 2 | 8,632 | 17,264 | 5,566 | no |
| regional | 31.69% | 3 | 3,864 | 7,728 | 5,566 | no |
| regional | 31.69% | 5 | 1,409 | 2,818 | 5,566 | yes |

Groups come from the non-overlapping planning split in the [segment description](segments-real-data.md).
Overlapping hypothesis tables must not be used for the same women at the same time. The five segment rows
are alternatives / separate pilots, not one shared control for five comparisons. Selecting on a usable
channel and current conditions will reduce the available numbers. For an eligible share q the yearly
reference is q × available_clients; for an observed-outcome share r the initial recruitment target is
ceil(n / r) per arm. This correction does not remove bias from missing outcomes; r and the missingness
mechanism must be justified.

If five confirmatory effects are claimed as one family, a simple conservative option is Bonferroni:
alpha = 0.05 / 5 = 0.01 per comparison. For example:

| Segment | Per arm at MDE = 2 pp, alpha = 0.01 |
| --- | --- |
| lapsed_regular | 13,165 |
| low_contact | 3,036 |
| care_no_prevention | 4,436 |
| repeated_nonresponder | 5,531 |
| regional | 12,844 |

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
