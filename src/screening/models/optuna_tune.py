"""Stage 2: Optuna fine-tunes LightGBM with grouped CV; every trial is a nested MLflow run."""

import lightgbm as lgb
import mlflow
import numpy as np
import optuna
import pandas as pd
from sklearn.metrics import average_precision_score, log_loss, roc_auc_score

MAX_BIN_CHOICES = [63, 127, 255]

SCORERS = {
    "roc_auc": roc_auc_score,
    "average_precision": average_precision_score,
    "neg_log_loss": lambda y, p: -log_loss(y, p),
}


def _suggest(trial: optuna.Trial) -> dict:
    return {
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
        "num_leaves": trial.suggest_int("num_leaves", 4, 256, log=True),
        "min_child_samples": trial.suggest_int("min_child_samples", 10, 500, log=True),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.4, 1.0),
        "subsample": trial.suggest_float("subsample", 0.5, 1.0),
        "subsample_freq": 1,
        "reg_alpha": trial.suggest_float("reg_alpha", 1e-4, 10.0, log=True),
        "reg_lambda": trial.suggest_float("reg_lambda", 1e-4, 10.0, log=True),
        "max_bin": trial.suggest_categorical("max_bin", MAX_BIN_CHOICES),
    }


def tune_lgbm(X: pd.DataFrame, y: pd.Series, folds: list[tuple], cfg: dict,
              warm_start: dict | None = None) -> optuna.Study:
    oc = cfg["optuna"]
    score_fn = SCORERS[oc["metric"]]

    def objective(trial: optuna.Trial) -> float:
        params = _suggest(trial)
        scores, best_iters = [], []
        for i, (tr, va) in enumerate(folds):
            model = lgb.LGBMClassifier(n_estimators=oc["max_estimators"], random_state=cfg["seed"],
                                       verbose=-1, **params)
            model.fit(X.iloc[tr], y.iloc[tr], eval_set=[(X.iloc[va], y.iloc[va])],
                      callbacks=[lgb.early_stopping(oc["early_stopping_rounds"], verbose=False)])
            scores.append(score_fn(y.iloc[va], model.predict_proba(X.iloc[va])[:, 1]))
            best_iters.append(model.best_iteration_)
            trial.report(float(np.mean(scores)), i)
            if trial.should_prune():
                raise optuna.TrialPruned()

        cv = float(np.mean(scores))
        n_estimators = int(np.mean(best_iters))
        trial.set_user_attr("n_estimators", n_estimators)
        with mlflow.start_run(run_name=f"optuna_trial_{trial.number}", nested=True):
            mlflow.log_params({**params, "n_estimators": n_estimators})
            mlflow.log_metrics({f"cv_{oc['metric']}": cv, f"cv_{oc['metric']}_std": float(np.std(scores))})
        return cv

    study = optuna.create_study(
        direction="maximize",
        sampler=optuna.samplers.TPESampler(seed=cfg["seed"]),
        pruner=optuna.pruners.MedianPruner(n_startup_trials=5, n_warmup_steps=1),
    )
    if warm_start:
        study.enqueue_trial(warm_start, skip_if_exists=True)
    study.optimize(objective, n_trials=oc["n_trials"], timeout=oc.get("timeout"))
    return study


def make_best(study: optuna.Study, cfg: dict) -> lgb.LGBMClassifier:
    """Unfitted LightGBM with the best params and the CV-averaged number of trees."""
    best = study.best_trial
    return lgb.LGBMClassifier(n_estimators=max(best.user_attrs["n_estimators"], 1),
                              random_state=cfg["seed"], verbose=-1,
                              **{**best.params, "subsample_freq": 1})
