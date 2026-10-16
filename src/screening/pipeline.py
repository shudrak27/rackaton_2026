"""End-to-end training run:

    load -> features -> out-of-time split -> FLAML (model family) -> Optuna (LightGBM tuning)
    -> champion choice on the same CV folds -> final fit -> test evaluation vs rule baseline
    -> feature importance -> segments -> A/B sample sizes

Everything is logged into one parent MLflow run; FLAML and every Optuna trial are nested runs.
"""

import logging

import joblib
import mlflow
import mlflow.lightgbm
import numpy as np
import pandas as pd
import lightgbm as lgb

from screening.config import resolve
from screening.data import load, schema as s, split
from screening.evaluation import explain, metrics
from screening.experiment import power
from screening.features import build
from screening.models import baseline, champion, flaml_search, optuna_tune
from screening.scoring import make_bundle
from screening.segments import rules
from screening.tracking import log_df, setup_mlflow

log = logging.getLogger(__name__)


def _save(df: pd.DataFrame, name: str, reports_dir) -> None:
    df.to_csv(reports_dir / f"{name}.csv", index=False)
    log_df(df, name)


def _tuning_subset(train_df: pd.DataFrame, n_clients: int | None, seed: int) -> pd.DataFrame:
    """All rows of a random subset of clients; keeps tuning fast on the full 1.3M rows."""
    clients = train_df[s.CLIENT_ID].unique()
    if not n_clients or n_clients >= len(clients):
        return train_df
    keep = np.random.default_rng(seed).choice(clients, n_clients, replace=False)
    return train_df[train_df[s.CLIENT_ID].isin(keep)].reset_index(drop=True)


def train(cfg: dict) -> dict:
    setup_mlflow(cfg)
    reports_dir = resolve(cfg["paths"]["reports"])
    models_dir = resolve(cfg["paths"]["models"])
    reports_dir.mkdir(parents=True, exist_ok=True)
    models_dir.mkdir(parents=True, exist_ok=True)
    top_k = cfg["evaluation"]["top_k"]
    metric = cfg["optuna"]["metric"]

    df = load.load(cfg)
    df, feats = build.build(df, cfg)
    train_df, test_df = split.temporal_split(df, cfg["split"]["test_year"])
    tune_df = _tuning_subset(train_df, cfg["optuna"].get("tune_sample_clients"), cfg["seed"])
    folds = split.group_folds(tune_df, cfg["split"]["n_folds"])
    X_tr, y_tr = train_df[feats], train_df[s.TARGET]
    X_tu, y_tu = tune_df[feats], tune_df[s.TARGET]
    X_te, y_te = test_df[feats], test_df[s.TARGET]
    log.info("train %d rows (tuning on %d), test %d rows, %d features",
             len(X_tr), len(X_tu), len(X_te), len(feats))

    with mlflow.start_run(run_name="train") as run:
        mlflow.log_dict(cfg, "config.json")
        mlflow.log_params({"n_train": len(X_tr), "n_tune": len(X_tu), "n_test": len(X_te),
                           "n_features": len(feats), "test_year": cfg["split"]["test_year"],
                           "train_non_attendance": round(float(y_tr.mean()), 4)})
        mlflow.log_text("\n".join(feats), "features.txt")

        # Stage 1: FLAML
        candidates = {}
        warm_start = None
        if cfg["flaml"]["enabled"]:
            automl = flaml_search.run_flaml(X_tu, y_tu, tune_df[s.CLIENT_ID], cfg)
            warm_start = flaml_search.flaml_lgbm_to_optuna(
                automl.best_config_per_estimator.get("lgbm"))
            mlflow.set_tag("flaml_best_estimator", automl.best_estimator)
            candidates[f"flaml_{automl.best_estimator}"] = champion.flaml_factory(automl)

        # Stage 2: Optuna on LightGBM
        study = optuna_tune.tune_lgbm(X_tu, y_tu, folds, cfg, warm_start=warm_start)
        mlflow.log_params({f"best.{k}": v for k, v in study.best_params.items()})
        mlflow.log_metric(f"cv_optuna_{metric}", study.best_value)
        log_df(study.trials_dataframe(), "optuna_trials")
        candidates["optuna_lgbm"] = lambda: optuna_tune.make_best(study, cfg)

        # Stage 3: champion on identical folds, then refit on the full train set
        if len(candidates) > 1:
            name, scores = champion.choose(candidates, X_tu, y_tu, folds, metric)
            mlflow.log_metrics({f"champion_cv_{k}": v for k, v in scores.items()})
            log.info("champion %s, CV %s", name, {k: round(v, 4) for k, v in scores.items()})
        else:
            name = "optuna_lgbm"
        mlflow.set_tag("champion", name)
        model = candidates[name]()
        model.fit(X_tr, y_tr)
        proba = model.predict_proba(X_te)[:, 1]

        # Evaluation on the out-of-time test year, model vs rule baseline
        model_m = metrics.summary(y_te, proba, top_k)
        base_m = metrics.summary(y_te, baseline.baseline_score(test_df), top_k, is_proba=False)
        mlflow.log_metrics({f"test_{k}": v for k, v in model_m.items()})
        mlflow.log_metrics({f"test_baseline_{k}": v for k, v in base_m.items()})
        comparison = pd.DataFrame({"model": model_m, "baseline": base_m}).reset_index(names="metric")
        _save(comparison, "test_metrics", reports_dir)
        _save(metrics.decile_table(y_te, proba), "decile_table", reports_dir)
        _save(metrics.calibration_table(y_te, proba), "calibration", reports_dir)

        # PROČ: drivers
        _save(explain.importance(model, X_te, y_te, seed=cfg["seed"]), "feature_importance", reports_dir)

        # CO + JAK OVĚŘIT: segments and experiment sizing
        seg = rules.assign(test_df, cfg)
        seg_report = rules.report(seg, y_te, proba)
        _save(seg_report, "segments", reports_dir)
        _save(power.design_table(seg_report, cfg), "experiment_design", reports_dir)

        keep = [c for c in (s.CLIENT_ID, s.INVITATION_DATE, s.REGION, s.AGE_BAND, s.AGE)
                if c in test_df.columns]
        scored = test_df[keep].assign(risk_non_attendance=proba, segment=seg.to_numpy(),
                                      y=y_te.to_numpy())
        scored.to_parquet(reports_dir / "scored_test.parquet", index=False)

        joblib.dump(make_bundle(model, X_tr, name), models_dir / "model.joblib")
        mlflow.log_artifact(str(models_dir / "model.joblib"))
        if isinstance(model, lgb.LGBMClassifier):
            # Native booster (text format): logging the sklearn wrapper goes through skops ->
            # threadpoolctl, which breaks on non-ASCII paths on Windows.
            mlflow.lightgbm.log_model(model.booster_, name="model")
        log.info("MLflow run %s", run.info.run_id)

    return {"model": model_m, "baseline": base_m, "champion": name, "run_id": run.info.run_id}
