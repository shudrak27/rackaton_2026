"""CLI:  python -m screening <command>

    synth   generate synthetic data into data/raw/
    train   full pipeline (FLAML -> Optuna -> evaluation -> segments), logged to MLflow
    power   A/B sample size for a given baseline attendance and uplift
"""

import argparse
import logging
import sys

from screening.config import load_config, resolve


def main() -> None:
    p = argparse.ArgumentParser(prog="screening")
    p.add_argument("--config", default=None)
    sub = p.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("synth")
    ps.add_argument("--n-clients", type=int, default=80_000)
    ps.add_argument("--out", default="data/raw/synthetic.parquet")

    pt = sub.add_parser("train")
    pt.add_argument("--data", help="override data.path")
    pt.add_argument("--time-budget", type=int, help="override flaml.time_budget (s)")
    pt.add_argument("--n-trials", type=int, help="override optuna.n_trials")
    pt.add_argument("--no-flaml", action="store_true")

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
        print("attendance overall: %.3f" % df["attended_12m"].mean())
        print(df.groupby(df["n_prior_invitations"].clip(upper=5))["attended_12m"]
                .agg(["size", "mean"]).rename_axis("prior_invitations (5 = 5+)"))

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
        for name in ("model", "baseline"):
            print(name, {k: round(v, 4) for k, v in res[name].items() if "top" not in k})

    elif args.cmd == "power":
        from screening.experiment.power import n_per_group
        ec = cfg["experiment"]
        print(n_per_group(args.p, args.mde, ec["alpha"], ec["power"]), "clients per arm")


if __name__ == "__main__":
    main()
