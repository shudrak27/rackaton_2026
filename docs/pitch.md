# Pitch: who will not attend mammography screening?

Target length: 5–7 minutes. All model results refer to the untouched 2024 test year. Values in the generated deck are read from `reports/ui/data.json`; `[TODO]` is shown when the export does not contain a required value.

## 1. Who will not attend mammography screening?

**Takeaway:** Use risk to focus attention, and experiments to prove impact.

- 1,344,556 invitations to 508,527 women in 2020–2024.
- We rank non-attendance risk, explain associations, define operational segments and propose a controlled test.

**Visual:** Clean title slide.

**Speaker notes:** We want to use the same invitation capacity more intelligently. The solution has four parts: identify who is unlikely to attend, understand the recorded patterns behind that risk, define actionable groups and test whether targeted support works.

**Sources:** `data.json::meta.n_invitations`, `meta.n_clients`, `meta.years`.

## 2. One letter for everyone meets very different behaviour

**Takeaway:** Attendance falls sharply as invitations repeat.

- Overall 12-month attendance is 19.3%.
- Attendance falls from about 51% to about 3% across invitation history.
- Invitation history is a strong signal, but it cannot tell us which support works.

**Visual:** `attendance_by_invitations.png`.

**Speaker notes:** Women do not respond to the standard letter in the same way. An early invitation reaches a group where roughly half attend, while attendance among repeatedly invited women is only a few percent. That gap motivates differentiated contact.

**Sources:** `data.json::meta.attendance_overall`, `attendance_by.prior_invitations`. The deck calculates the two endpoints from the first and last exported groups.

## 3. A data check can prevent about 7,300 mistimed invitations a year

**Takeaway:** Fix an operational gap before adding a complex intervention.

- About 7,300 invitations per year follow a screening recorded in the previous 0–6 months.
- Attendance after these invitations is about 2%.
- Check fresh claims immediately before mailing or postpone the repeat invitation.
- A claims-reporting delay is a hypothesis, not a demonstrated mechanism.

**Visual:** `months_since_screening.png`.

**Speaker notes:** This is the quickest opportunity. The invitation looks mistimed because a very recent screening is already recorded and almost nobody screens again. We should confirm the operational mechanism with the process owner before claiming savings.

**Sources:** `data.json::recently_screened_per_year`, `attendance_by.months_since_last_screening`; mechanism caveat in `docs/segments-real-data.md`.

## 4. The 2024 holdout simulates the next invitation wave

**Takeaway:** Evaluation follows time and excludes information created after invitation.

- Train on invitations before 2024 and test once on 2024.
- Never use the 3- or 6-month outcome flags as predictors.
- The same woman may occur in earlier years; her identifier is used for grouping, never as a feature.
- Every feature must be known at invitation time.

**Visual:** `risk_deciles.png`, with a small train-before-2024 / test-2024 annotation.

**Speaker notes:** A random row split would make future deployment look easier than it is. The temporal holdout asks the operational question: how does a model trained on past waves perform on the next wave? Outcome fields after invitation are explicitly excluded.

**Sources:** `data.json::meta.test_year`, `meta.n_test`, `deciles`; `src/screening/data/schema.py`; `configs/config.yaml::split`.

## 5. The model finds who needs only a letter—and where calls are wasted

**Takeaway:** Translate ranking quality into people and operational capacity.

- Calibrated LightGBM reaches ROC-AUC 0.836; the invitation-count rule reaches 0.785.
- In the lowest-risk 10%, model-selected attendance is 68% versus 51% for the rule.
- Intensive outreach to the highest-risk 10% reaches 25.6 thousand women.
- It needlessly contacts 450 likely attenders versus 779 for the rule: 42% fewer.

**Visual:** `model_vs_rule.png`, supported by `risk_deciles.png` (68% to 1.7% attendance).

**Speaker notes:** The rule is a credible baseline because invitation history is already powerful. The model adds value by combining more pre-invitation history. The decision value is clearer in people: a safer standard-letter group and fewer intensive contacts spent on women who attend anyway.

**Sources:** `data.json::test_metrics[metric=roc_auc]`, `targeting[share=0.1]`, `deciles`. The 42% reduction is `1 - top_wasted_model / top_wasted_rule`.

## 6. The model learns behaviour and care history—not causes

**Takeaway:** SHAP explains the risk score; it does not identify an effective intervention.

- Rank the ten most influential recorded features by mean absolute SHAP value.
- Show whether a higher numeric value is associated with higher or lower predicted risk.
- Treat categories and observed histories as associations.
- Establish causal effects only through randomized outcomes.

**Visual:** `top10_shap.png`.

**Speaker notes:** Invitation, screening and prevention history summarize behaviour before the letter. SHAP helps us understand what the model uses, but changing a field does not necessarily change attendance. This is why the experiment remains essential.

**Source:** `data.json::feature_importance`.

## 7. Operational segments turn scores into testable hypotheses

**Takeaway:** Segment size and baseline attendance determine practical pilots.

- Recent screening, first invitation, lapsed regular, low contact, care without prevention, repeated non-response and other.
- Each invitation enters one exclusive operational segment.
- Segment definitions use only information available before invitation.
- Regional differences remain descriptive until access data are added.

**Visual:** `segment_map.png`.

**Speaker notes:** A probability alone does not specify an action. Segments translate familiar pre-invitation patterns into eligibility rules. They are operational hypotheses, not claims that each label captures the true barrier.

**Sources:** `data.json::segments`; `docs/segments-real-data.md`.

## 8. Match support to the barrier, then measure its effect

**Takeaway:** High risk does not imply high intervention effect.

- Recent screen → postpone; lapsed regular → booking reminder.
- Care without prevention → involve the GP or gynaecologist.
- Repeated non-response → use another channel and navigation.
- Response at 3, 6 and 12 months informs reminder timing.

**Visual:** `response_timing_by_segment.png` plus the intervention mapping.

**Speaker notes:** These interventions are proposals. We should not automatically spend the most on the highest-risk women because they may also be the hardest to influence. Randomization tells us where support creates additional screening.

**Sources:** `data.json::interventions`, `segment_response_speed`.

## 9. Randomization tells us who the intervention actually helps

**Takeaway:** Run a woman-level, stratified A/B test before scaling.

- Compare the standard invitation with one segment-specific treatment.
- Randomize within segment × risk-quintile strata.
- Primary outcome: 12-month attendance under intention-to-treat; 3 months is an early signal.
- Size each arm from baseline attendance and the minimum detectable effect.
- Use measured effects to train an uplift model later.

**Visual:** `ab_group_sizes.png`.

**Speaker notes:** Fixed eligibility and assignment make the result interpretable. We keep everyone in the arm to which they were assigned, including failed delivery or non-compliance. The chart shows why sample-size planning must be segment-specific.

**Sources:** `data.json::experiment_design`; `docs/experiment-design.md`.

## 10. Guardrails keep the ranking useful and fair

**Takeaway:** Monitor ranking, calibration and selection across every wave.

- Audit discrimination, error, calibration and selection rates by age and region.
- Recalibrate when the annual attendance baseline shifts; the current residual shift is about 1 percentage point.
- Territory identifies an administrative office, not measured travel access.
- The demo contains aggregates only and suppresses cells below 20.

**Visual:** Calibration and fairness table from the dashboard; use `[TODO]` if a slide-ready export is absent.

**Speaker notes:** A strong overall AUC can hide weaker behaviour in a subgroup. Monitoring must cover the decision produced by the model, not only one global metric. Regional associations need external access data before operational interpretation.

**Sources:** `data.json::calibration`, `fairness`, `meta.min_cell`; the 1 pp interpretation is documented in the dashboard and must be exported as a dedicated key before it is treated as a generated deck metric.

## 11. Start with the quick win, then learn in controlled waves

**Takeaway:** Separate a process fix from causal intervention pilots.

1. Add a fresh-claims check before the next mailing wave.
2. Score eligible women immediately before each wave.
3. Pilot one intervention per priority segment with fixed eligibility and outcomes.
4. Scale proven effects, then retrain and recalibrate on new waves.

**Visual:** A four-step rollout arrow; the generated deck reuses the segment map until this icon-only visual is added.

**Speaker notes:** The claims check can be validated quickly. Intervention changes require a controlled pilot. Each wave then provides both operational outcomes and new training evidence without treating current assumptions as permanent policy.

**Sources:** `docs/segments-real-data.md`; `docs/experiment-design.md`; `data.json::segments`.

## 12. Use risk to focus attention—and experiments to prove impact

**Takeaway:** The model prioritizes; the A/B test establishes impact.

- 1,344,556 invitations reveal large and actionable differences.
- Attendance runs from 68% to 1.7% across model risk deciles.
- The next decision is a controlled pilot, not an untested national rollout.
- Questions?

**Visual:** `risk_deciles.png`.

**Speaker notes:** Close on the distinction that protects the project from overclaiming. We already have an actionable ranking and one process hypothesis. We need randomized evidence before choosing expensive support or estimating return on investment.

**Sources:** `data.json::meta.n_invitations`, `deciles`.

