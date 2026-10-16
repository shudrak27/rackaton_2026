"""CLI:  python -m screening <command>

    synth    generate synthetic data into data/raw/
    profile  first look at the data + leakage check (run this first on new data)
    train    full pipeline (FLAML -> Optuna -> champion -> evaluation -> segments), logged to MLflow
    score    risk + segment + intervention for new invitations, using models/model.joblib
    power    A/B sample size for a given baseline attendance and uplift
    export-ui aggregates for the demo UI / slides -> reports/ui/data.json (run after train)
"""

import argparse
import logging
import sys

import pandas as pd

from screening.config import load_config, resolve


def main() -> None:
    p = argparse.ArgumentParser(prog="screening")
    p.add_argument("--config", default=None)
    sub = p.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("synth")
    ps.add_argument("--n-clients", type=int, default=80_000)
    ps.add_argument("--out", default="data/raw/synthetic.parquet")

    pr = sub.add_parser("profile")
    pr.add_argument("--data", help="override data.path")

    pt = sub.add_parser("train")
    pt.add_argument("--data", help="override data.path")
    pt.add_argument("--time-budget", type=int, help="override flaml.time_budget (s)")
    pt.add_argument("--n-trials", type=int, help="override optuna.n_trials")
    pt.add_argument("--no-flaml", action="store_true")

    pc = sub.add_parser("score")
    pc.add_argument("--input", required=True, help="csv/parquet with new invitations")
    pc.add_argument("--model", default="models/model.joblib")
    pc.add_argument("--out", default="reports/scored.csv")

    sub.add_parser("export-ui")

    pp = sub.add_parser("power")
    pp.add_argument("--p", type=float, required=True, help="baseline attendance, e.g. 0.10")
    pp.add_argument("--mde", type=float, required=True, help="absolute uplift, e.g. 0.02")

    args = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Cyrillic paths on Windows consoles
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cfg = load_config(args.config)

    if args.cmd == "synth":
        from screening.data.synthetic import generate
        out = resolve(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        df = generate(n_clients=args.n_clients, seed=cfg["seed"])
        df.to_parquet(out, index=False)
        print(f"{len(df)} rows -> {out}")
        print(f"attendance overall: {df['attended_12m'].mean():.3f}")
        print(df.groupby(df["n_prior_invitations"].clip(upper=5))["attended_12m"]
                .agg(["size", "mean"]).rename_axis("prior_invitations (5 = 5+)"))

    elif args.cmd == "profile":
        from screening.data import load
        from screening.data.profile import leakage_suspects, profile
        from screening.features.build import build
        if args.data:
            cfg["data"]["path"] = args.data
        df, feats = build(load.load(cfg), cfg)
        reports = resolve(cfg["paths"]["reports"])
        reports.mkdir(parents=True, exist_ok=True)
        for name, table in profile(df, feats).items():
            table.to_csv(reports / f"profile_{name}.csv", index=False)
            print(f"\n== {name} ==\n{table.head(25).to_string(index=False)}")
        threshold = cfg["features"]["leakage_auc_warn"]
        suspects = leakage_suspects(pd.read_csv(reports / "profile_single_feature_auc.csv"), threshold)
        if suspects:
            print(f"\n!! LEAKAGE SUSPECTS (single-feature AUC > {threshold}): {suspects}"
                  "\n!! check they are known at the invitation date, else add to features.exclude")
        print(f"\nprofile_*.csv -> {reports}")

    elif args.cmd == "score":
        from screening.data.load import load_raw
        from screening.scoring import load_bundle, score
        cfg["data"]["path"] = args.input
        scored = score(load_raw(cfg), load_bundle(resolve(args.model)), cfg)
        out = resolve(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        scored.to_csv(out, index=False)
        print(f"{len(scored)} invitations scored -> {out}")
        print(scored.groupby("segment")["risk_non_attendance"].agg(["size", "mean"]).round(3))

    elif args.cmd == "train":
        from screening.pipeline import train
        if args.data:
            cfg["data"]["path"] = args.data
        if args.time_budget is not None:
            cfg["flaml"]["time_budget"] = args.time_budget
        if args.n_trials is not None:
            cfg["optuna"]["n_trials"] = args.n_trials
        if args.no_flaml:
            cfg["flaml"]["enabled"] = False
        res = train(cfg)
        print("champion:", res["champion"])
        for name in ("model", "baseline"):
            print(name, {k: round(v, 4) for k, v in res[name].items() if "top" not in k})

    elif args.cmd == "export-ui":
        from screening.export_ui import export
        print(f"UI data -> {export(cfg)}")

    elif args.cmd == "power":
        from screening.experiment.power import n_per_group
        ec = cfg["experiment"]
        print(n_per_group(args.p, args.mde, ec["alpha"], ec["power"]), "clients per arm")


if __name__ == "__main__":
    main()
