# One-minute dashboard demo

Open the React dashboard with `cd ui && npm run dev` (http://localhost:5173) and keep `reports/ui/data.json`
fixed for the presentation. Keep the generated deck and screenshots available as a backup.

| Time | Click | Say |
|---:|---|---|
| 0:00–0:12 | **Overview** | “Women respond differently to the same invitation. Among the 10% the model ranked most likely to attend, 68 in 100 came; the simple comparison rule selected a group where 51 in 100 came.” |
| 0:12–0:25 | **Who to call** | “A limited team needs a shortlist. The model finds women likely to miss screening; eligibility checks and a trial will tell us whom to contact and whether it helps.” |
| 0:25–0:35 | **Drivers** | “Invitation history and contact with healthcare help explain the ranking. These patterns do not establish why a particular woman did not attend.” |
| 0:35–0:47 | **Business actions** | “Each group has a proposed action. Recently screened women need an eligibility check before another invitation; repeated invitations suggest testing a different type of support.” |
| 0:47–1:00 | **Experiment** | “For women last screened over two years ago, compare the usual invitation with an added reminder. Detecting two extra screenings per 100 women needs 8,848 women per group. The trial has not run.” |

## Before the demo

- Place the supplied export at `reports/ui/data.json`, then start the React dashboard: `cd ui && npm run dev`.
  Regenerate it with `python -m screening export-ui` only when the matching raw data and training reports are available.
- Open every tab once so charts are cached.
- Set browser zoom so no key chart requires scrolling.
- Keep the exact JSON used for the deck; do not regenerate between pitch and demo.
- Turn off notifications and keep the terminal behind the browser.

## Backup if the live demo fails

Use the generated deck and open these static files in order:

1. `reports/figures/attendance_by_invitations.png` — Overview.
2. `reports/figures/model_vs_rule.png` — 01 WHO.
3. `reports/figures/top10_shap.png` — 02 WHY.
4. `reports/figures/segment_map.png` — 03 WHAT.
5. `reports/figures/ab_group_sizes.png` — 04 HOW TO VERIFY.

Before presenting, capture the views used in the demo in `reports/pitch/screenshots/`. These files remain
local because `reports/` is ignored. If the live dashboard fails, use the screenshots, generated deck
or static figures. Model quality, Calibration and Validation are available for technical follow-up.

