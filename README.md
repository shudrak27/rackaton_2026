# Screening Insights — Rakathon 2026

An MVP built in **24 hours at Rakathon 2026**, a hackathon tackling cancer.
We help VZP predict missed mammography screening, propose support, and plan how to test it.
<img width="1800" height="700" alt="image" src="https://github.com/user-attachments/assets/406a4766-d938-4006-8f44-44ed1318e9ca" />


## Problem

Only **19.3%** of invitations in the supplied dataset were followed by screening within 12 months.
Data: **1,344,556 invitations to 508,527 unique women in 2020–2024**.
Target: **non-attendance within 12 months of an invitation**, not a missed appointment or cancer risk.


## Methodology

Current pipeline configuration (the supplied results below do not include a complete run manifest):

```text
VZP CSV → clean and map fields → features known when the invitation was sent
  → time split: earlier invitations with known outcomes / 2024 test invitations
  → FLAML compares model families + Optuna tunes LightGBM
  → compare both candidates on the same client-grouped folds → choose the winner
  → fit model + calibrate probabilities → evaluate on 2024
  → explain predictions → segments and proposed actions → A/B test plan → React dashboard
```

- A 12-month gap keeps training outcomes known by January 2024. Folds group by woman; test-year women
  may have earlier records. IDs and later outcomes are not inputs.
- FLAML seeds Optuna's LightGBM search, with early stopping and pruning. Cross-validation selects the
  winner; the final family is not hardcoded to LightGBM.
- Isotonic calibration uses the last six months of training, excluded from the final base-model fit.
  Model selection currently uses the broader training pool, including those months.
- SHAP (LightGBM) or permutation importance explains associations, not causes. MLflow logs training runs.

## Model results

Supplied report: **256,466 test invitations from 2024**.

| Measure | Model | Simple comparison rule |
|---|---:|---:|
| ROC-AUC | **0.836** | 0.785 |
| Average precision — non-attendance | **0.947** | 0.927 |
| Average precision — attendance | **0.571** | 0.425 |
| Attendance among the 10% ranked most likely to attend | **68%** | 51% |

Baseline: `previous invitations − 0.1 × screening procedure codes in the past 5 years` (higher = higher risk).
This is our comparison rule, not a verified VZP policy. Random AP: **0.808** for non-attendance, **0.192** for
attendance. Prediction quality does not measure the effect of calling women.

## Business questions and answers

| Question | What the MVP can answer |
|---|---|
| Who might need extra support? | Rank women by non-attendance risk, then check eligibility before choosing an outreach pilot. In the highest-risk tenth, **98.3% did not attend** in 2024. |
| Which histories matter? | Previous invitations, invitations since the last screening, preventive visits and contact with healthcare are leading model signals. |
| What could VZP try? | Seven operational segments connect to six proposed actions, including a reminder, booking help or a doctor recommendation. The residual group needs a specific hypothesis. |
| Can the mailing process improve? | **7,279 invitations per year**, on average, followed a screening recorded within six months. Review recent records and programme rules before suppressing any invitation. |
| How much could this save? | Costs and intervention effects in the config are assumptions. Savings require confirmed unnecessary invitations and actual costs; no financial benefit has been measured. |

## A/B tests

For women last screened over two years ago: standard invitation versus **invitation plus a day-14 reminder
and booking guidance**. SMS requires contacts, which are absent from the CSV.

At **33.36%** historical attendance, detecting **+2 percentage points** needs **8,848 women per group**
(80% power, two-sided 5% significance level). Randomize by woman; count everyone assigned, including
unreached women. Primary outcome: screening within 12 months. **The trial has not run.**
See [experiment design](docs/experiment-design.md) and [segment definitions](docs/segments-real-data.md).


## Repository map

- `src/screening/`: Python pipeline; `ui/`: React business and technical views.
- `configs/`, `tests/`, `notebooks/`: settings, Python tests and EDA; `docs/`, `scripts/`: experiment and pitch tools.
- `data/`, `reports/`, `models/`, `mlflow.db`: local, git-ignored inputs and outputs.
