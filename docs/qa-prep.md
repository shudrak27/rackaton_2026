# Jury Q&A preparation

## 1. What exactly does the model predict?

It predicts the probability that an invited woman will **not** complete mammography screening within 12 months. The score ranks outreach priority; it does not predict an intervention effect.

## 2. Why is the 2024 test honest?

All model selection and fitting use earlier invitation waves. The untouched 2024 wave is evaluated once, so the test mirrors deployment on a future annual wave instead of mixing future and past records randomly.

## 3. Some women occur in training and test. Is that leakage?

No, if the task is to score future invitations for women already known to VZP. Client ID is excluded from features, and every feature is frozen at invitation time. Grouped cross-validation prevents the same woman from appearing on both sides of an internal fold.

## 4. Why exclude the 3- and 6-month screening flags?

They occur after the invitation and are partial versions of the 12-month target. Using them would reveal the answer at prediction time and inflate performance.

## 5. What does ROC-AUC 0.836 mean?

For a randomly chosen non-attender and attender from the test wave, the model assigns the non-attender a higher risk about 83.6% of the time. AUC measures ranking, not probability accuracy or causal impact.

## 6. Why compare against the number-of-invitations rule?

It is simple, deployable and already captures the strongest behavioural pattern, reaching AUC 0.785. Beating this strong baseline shows that the additional history adds useful ranking information.

## 7. Why present people instead of only AUC?

Operational teams allocate letters, SMS messages and calls to people. At a fixed 10% capacity, the current export identifies a 68% attendance low-risk group and reduces needless high-risk contacts from 779 to 450 compared with the rule.

## 8. Are the probabilities calibrated?

Calibration is fitted on the last six months of training data, outside model fitting. The residual shift is about one percentage point and matches normal year-to-year attendance variation, so calibration must be monitored and refreshed by wave.

## 9. Why not build an uplift model now?

Historical data contain invitations and outcomes but no randomized alternatives. Risk describes who does not attend; uplift needs outcomes under both standard and changed outreach. The proposed A/B tests create that evidence.

## 10. Does SHAP show why women do not attend?

It shows which recorded values push model predictions up or down. These are associations learned from claims and invitation history, not psychological explanations or causal effects.

## 11. How will you check fairness by age?

For every age band we monitor sample size, outcome rate, ROC-AUC and selection into intensive outreach. We also compare calibration, because the same score should represent a similar risk across monitored groups.

## 12. How will you check fairness by region?

We monitor the same performance and selection measures by territorial office. We do not interpret an office effect as distance or access: the data contain no screening-centre travel measure, and crude regional comparisons have different case mixes.

## 13. Why do recently screened women receive another invitation?

The data show about 7,300 invitations a year within six months of a recorded screen and only about 2% subsequent attendance. A claims-reporting delay or timing mismatch is plausible, but remains a hypothesis until the mailing workflow is checked.

## 14. Are those 7,300 invitations proven waste or savings?

They are a process-review opportunity, not proven net savings. The overlap is observable; avoidability, timing, print commitments and downstream effects must be validated before assigning a financial benefit.

## 15. Where do intervention costs and expected effects come from?

Current cost and uplift values are placeholders for scenario planning. Procurement supplies real unit costs; randomized pilots supply real effects. We do not present assumed ROI as an observed result.

## 16. How would VZP deploy this?

Before each invitation wave, build features using data available at that cutoff, score eligible women, apply approved capacity and policy rules, and record assignment. Outcomes return after fixed follow-up for monitoring, recalibration and experiment analysis.

## 17. What is the A/B primary analysis?

Woman-level randomization within segment × risk-quintile strata, with 12-month attendance analyzed by intention-to-treat. Three-month attendance is an early operational signal, not a replacement primary endpoint.

## 18. How do you protect privacy in the demo?

The dashboard, figures and deck read one aggregate JSON export. It contains no client or invitation IDs, and groups below 20 observations are suppressed. Raw and row-level scored data remain local and are excluded from Git.

## 19. What happens if behaviour changes next year?

We compare outcome prevalence, calibration, segment size and ranking performance with the previous wave. We recalibrate when the base rate shifts and retrain only after the new labels mature and the temporal evaluation is repeated.

## 20. What is the main limitation today?

We can rank risk but cannot yet claim that SMS, calls or clinician involvement increase attendance. We also lack direct access measures such as distance, capacity and appointment availability. Those gaps define the next data and experiment work.

