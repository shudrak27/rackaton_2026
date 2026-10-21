# React dashboard

Vite + React + Recharts. The dashboard reads **only aggregate data** from `reports/ui/data.json`.
It needs no Python environment, API server, raw medical records or trained model file.

## Run locally

Install Node.js 20+ and place the supplied JSON at `reports/ui/data.json` in the repository. Then:

```bash
cd ui
npm install
npm run dev                 # http://localhost:5173
```

`dev` and `build` copy `../reports/ui/data.json` into `public/`. If the file is missing, obtain the supplied
aggregate export or regenerate it using the [Python pipeline](../README.md#train-and-refresh-reports).
To refresh an already-running dashboard after replacing the export:

```bash
npm run data
```

Reload the browser. `npm run data` copies the JSON; it does not retrain the model or regenerate reports.

```bash
npm run build               # static site in dist/
npm run preview             # serve the build locally; open the printed address
npm test                    # dashboard data and calculation checks
```

`public/data.json`, `dist/` and `node_modules/` are not committed. The export suppresses groups smaller
than 20 and contains no client IDs or individual medical records.

## Views

- **Overview, Who to call and Drivers:** observed outcomes, suggested audiences and patterns behind risk.
- **Segments and Business actions:** operational groups, proposed support, use cases and A/B questions.
- **Experiment:** required sample sizes for a proposed attendance improvement.
- **[Model quality](http://localhost:5173/#model-quality):** model-versus-rule performance and ranking.
- **[Calibration](http://localhost:5173/#calibration):** predicted probabilities versus observed outcomes.
- **[Validation](http://localhost:5173/#validation):** data split, evaluation approach and limitations.

The model predicts non-attendance within 12 months. Each average-precision result identifies its positive
class; attendance and non-attendance produce different values and different random baselines.

## Proposed actions

`src/interventions.js` defines the playbooks. Business actions contains six proposals; the residual
`other` group receives no blanket intervention. Use case and A/B test dialogs explain what to try and
how to measure it. Calls and reminders have **not** been tested; high risk alone does not prove benefit.

The experiment planner starts with women last screened over two years ago. Contact availability and
eligibility must be checked before recruitment. Doctor-mediated trials may require randomization by
practice and a larger sample than the individual-level calculator shows. See the
[experiment design](../docs/experiment-design.md) for assumptions and analysis.
