# React dashboard

Six sections, including **Business actions**, built with Vite + React + Recharts. No backend: it reads only
`reports/ui/data.json` (aggregates; created by `python -m screening export-ui`).

```bash
cd ui
npm install
npm run dev      # copies ../reports/ui/data.json -> public/, opens http://localhost:5173
npm run build    # static site in ui/dist/ (open with any static server, e.g. `npm run preview`)
```

`public/data.json`, `dist/` and `node_modules/` are not committed.

## Intervention playbooks

`src/interventions.js` defines the proposed actions, operational prerequisites and A/B questions.
Separate **Use case** and **A/B test** buttons are available from Overview, Segments, Business actions and the
Experiment planner. They separate observed segment outcomes from
unverified intervention hypotheses. These playbooks replace legacy intervention wording in the UI;
the raw aggregate export remains unchanged. No messages are sent and no trial results are simulated.
Business actions contains exactly six segment actions; the residual `other` segment stays in
Segments & outreach and is not given a blanket intervention.

The planner lists the four defined outreach pilot candidates and starts with `lapsed_regular`.
Recently screened women need an eligibility review; first invitations and the residual group need
a specific intervention hypothesis before an outreach pilot. Default baseline calculations retain
the export's full precision. Doctor-mediated trials may need practice-level randomization and a
separate cluster-adjusted sample size. Exported individual-level sample sizes do not cover that case.

Use `/#business` to open the action plan directly. Design references: challenge slides 3, 6, 8–10,
`docs/segments-real-data.md` and `docs/experiment-design.md`. Effect and cost assumptions are not
measured results. The primary outcome is screening within 12 months, not appointment no-show.
