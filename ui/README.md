# React dashboard (MVP)

Same 5 tabs as `app/dashboard.py`, built with Vite + React + Recharts. No backend: it reads only
`reports/ui/data.json` (aggregates; created by `python -m screening export-ui`).

```bash
cd ui
npm install
npm run dev      # copies ../reports/ui/data.json -> public/, opens http://localhost:5173
npm run build    # static site in ui/dist/ (open with any static server, e.g. `npm run preview`)
```

`public/data.json`, `dist/` and `node_modules/` are not committed.
