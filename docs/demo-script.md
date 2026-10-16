# One-minute dashboard demo

Open with `streamlit run app/dashboard.py` and keep `reports/ui/data.json` fixed for the presentation.

| Time | Click | Say |
|---:|---|---|
| 0:00–0:12 | **Overview** | “One standard letter meets very different behaviour. Attendance falls with repeated invitations, and the model separates a low-risk group from women needing more support.” |
| 0:12–0:25 | **01 WHO** | “The 2024 holdout was never used for training. AUC is 0.836 versus 0.785 for a strong rule, but the useful view is people: at fixed capacity the model wastes fewer intensive contacts.” |
| 0:25–0:35 | **02 WHY** | “SHAP shows the pre-invitation history behind the ranking. These are associations, not causes; select invitation history in the breakdown to show the observed pattern.” |
| 0:35–0:47 | **03 WHAT** | “Segments convert scores into operational hypotheses. Point to recently screened women as the immediate process check, then repeated non-responders as a candidate for different support.” |
| 0:47–1:00 | **04 HOW TO VERIFY** | “Choose repeated non-responder and a two-percentage-point effect. The calculator gives the required group size. We randomize by woman, analyze intention-to-treat and use results for uplift later.” |

## Before the demo

- Run `python -m screening export-ui`, then start Streamlit from the repository root.
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

Before presenting, capture full-window screenshots of the five loaded tabs as `reports/pitch/screenshots/overview.png`, `who.png`, `why.png`, `what.png` and `verify.png`. These files remain local because `reports/` is ignored. If Streamlit fails, show the screenshots first; use the static figures if the screenshots are unavailable.

