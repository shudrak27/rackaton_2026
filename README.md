# Rakathon 2026 — who will not attend mammography screening (VZP)

VZP sends addressed invitations to mammography screening. This project predicts the risk that an invited
woman will **not** be screened within 12 months, explains the drivers, groups women into actionable
segments with a proposed intervention each, and designs the A/B test that would prove the effect.

| Challenge block | What we deliver |
|---|---|
| **01 WHO** — predict risk | Calibrated LightGBM risk score, honest out-of-time test on 2024 |
| **02 WHY** — understand drivers | SHAP drivers, attendance breakdowns with confidence intervals, 75 regions |
| **03 WHAT** — propose support | 7 rule-based segments → intervention, "wasted invitations" finding, budget illustration |
| **04 HOW TO VERIFY** — measure effect | Stratified randomisation, ITT analysis, sample-size calculator, full A/B design |

## Key results (test year 2024, 256,466 invitations, never seen in training)

- Overall attendance within 12 months: **19.3%** (1,344,556 invitations, 508,527 women, 2020–2024).
- Model ROC-AUC **0.836** vs **0.785** for the rule "number of previous invitations" (random = 0.5).
- In people: the 10% lowest-risk women attend at **68%** (rule: 51%) — a standard letter is enough for them;
  phone outreach to the 10% highest-risk women wastes **42% fewer** contacts on women who would attend anyway.
- Attendance by risk decile: **68% → 1.7%**.
- **Quick win:** ~**7,300 invitations per year** go to women screened 0–6 months earlier (attendance ~2%).
  Most of them responded late to the previous year's letter; the yearly cycle likely does not yet see the
  fresh claim (reporting lag — a hypothesis to confirm with VZP).

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate               # Linux/macOS: source .venv/bin/activate
pip install -e ".[dev,ui]"
```

Put the VZP export at `data/raw/Rakhaton2026.csv` (git-ignored — **never commit data**), then:

```bash
python -m screening profile          # data overview + leakage check        -> reports/profile_*.csv
python -m screening train            # full pipeline, ~20 min                -> reports/, models/, MLflow
python -m screening export-ui        # aggregates for dashboards and slides  -> reports/ui/data.json
```

Demo dashboards (both read only `reports/ui/data.json` — aggregates, no row-level data):

```bash
cd ui && npm install && npm run dev  # React dashboard   -> http://localhost:5173  (Node.js 20+)
streamlit run app/dashboard.py       # Streamlit version -> http://localhost:8501
```

Other commands:

```bash
python -m screening score --input data/raw/new.csv   # risk + decile + segment + intervention per invitation
python -m screening power --p 0.10 --mde 0.02        # women per A/B arm
python -m screening synth                            # synthetic data (no real data needed)
mlflow ui --backend-store-uri sqlite:///mlflow.db    # experiment tracking, http://127.0.0.1:5000
python -m screening.viz.figures                      # English PNG charts from data.json -> reports/figures/
python scripts/build_deck.py                         # backup PPTX deck from data.json   -> reports/pitch/
pytest                                               # all tests (`-m "not slow"` skips the end-to-end run)
```

## Pipeline

```
VZP CSV ─► adapter (data/vzp.py) ─► features ─► out-of-time split
                                                  train: invitations with outcome known by 1 Jan 2024
                                                  test:  2024
   ├─► FLAML AutoML (grouped CV by woman) — picks the model family, warm-starts Optuna
   ├─► Optuna — tunes LightGBM (early stopping, pruning, 15 min budget)
   ├─► champion: FLAML best vs Optuna LightGBM on identical folds (test year never used)
   ├─► isotonic calibration on the last 6 months of train
   └─► test 2024 vs rule baseline ─► deciles, calibration, SHAP, segments, fairness,
                                     A/B sizes, budget plan, scored invitations
```

Everything is logged to MLflow (one parent run, nested runs for FLAML and each Optuna trial). Reports go to
`reports/`, the model bundle (model + features + category levels + decile thresholds) to `models/model.joblib`.
The modelling target is `non_attendance = 1 − attended_12m`.

## Data notes (VZP export, version 29 Sep 2026)

- Target: `SCREENING_12M_FLAG`. `SCREENING_3M/6M_FLAG` are measured **after** the invitation and are never
  model inputs (single-feature AUC 0.69 / 0.83 — a generic leakage detector would not catch them).
- `PRIOR_INVITATION_COUNT` includes the current invitation; the adapter subtracts 1 (0 = first invitation).
- `PRIOR_SCREEN_COUNT_5Y` counts procedure codes (~2 per screening); `NEVER_SCREENED_BEFORE_FLAG` means
  "no screening in the 5-year window".
- `INVITATION_SEQUENCE` resets after attendance (a streak of non-responses).
- The 12-month window is closed for all years (`cutoff_date: 2025-12-31`).
- Cohort: women continuously insured with VZP in 2015–2025. Results are evaluated on this group only.

## Project structure

```
rackaton_2026/
├── README.md
├── pyproject.toml                  package + extras: dev (tests, notebook, charts, pptx), ui (streamlit, plotly)
├── configs/config.yaml             single config: data, split, FLAML/Optuna, calibration, segments,
│                                   interventions (assumed effects), budget, fairness
├── src/screening/                  Python package
│   ├── __main__.py                 CLI: synth | profile | train | score | export-ui | power
│   ├── config.py, tracking.py      config loading, MLflow setup
│   ├── pipeline.py                 end-to-end training run
│   ├── scoring.py                  scoring of new invitations with the saved model bundle
│   ├── export_ui.py                aggregates-only JSON for dashboards and slides
│   ├── data/                       vzp.py (VZP adapter), schema.py, load.py, split.py,
│   │                               profile.py (leakage check), synthetic.py (test data)
│   ├── features/build.py           derived features
│   ├── models/                     baseline, flaml_search, optuna_tune, champion, calibration
│   ├── evaluation/                 metrics, explain (SHAP / permutation), fairness, real_data (EDA tables)
│   ├── segments/rules.py           segment rules + interventions
│   ├── experiment/                 power (sample size), assign (stratified randomisation), analysis (ITT)
│   ├── policy/budget.py            greedy budget allocation under assumed effects
│   └── viz/figures.py              English PNG charts from data.json
├── app/dashboard.py                Streamlit dashboard
├── ui/                             React dashboard (Vite + React + Recharts), see ui/README.md
├── notebooks/
│   ├── 01_eda.ipynb                exploratory analysis on the real data (committed without outputs)
│   └── write_reports.py            regenerates the two docs below from EDA tables
├── scripts/build_deck.py           backup pitch deck (PPTX) from data.json
├── docs/
│   ├── pitch.md                    pitch script with speaker notes
│   ├── demo-script.md              one-minute dashboard demo
│   ├── qa-prep.md                  expected jury questions and answers
│   ├── segments-real-data.md       segment definitions and sizes on real data
│   └── experiment-design.md        A/B test design
├── tests/                          pytest suite (unit, regression, end-to-end, dashboard)
└── data/, reports/, models/, mlflow.db   local only, git-ignored
```

## Caveats

- **High risk ≠ high effect.** The model ranks risk; only the experiment shows whom an intervention helps
  (next step: an uplift model trained on its results).
- SHAP shows associations, not causes. Regional differences are not adjusted for age or invitation history.
- Intervention costs and effects in the config (`interventions:`) are placeholders until the A/B test.
- One woman appears in several years, so random splits would inflate metrics; we use an out-of-time test.
- The Windows path of this repo contains non-ASCII characters; `threadpoolctl` breaks on such paths, so the
  code avoids sklearn/joblib parallelism and logs LightGBM boosters natively to MLflow.
