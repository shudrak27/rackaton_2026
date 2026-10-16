"""Stage 1: FLAML AutoML picks the model family and gives a starting configuration."""

import mlflow
import pandas as pd
from flaml import AutoML

from screening.models.optuna_tune import MAX_BIN_CHOICES


def run_flaml(X: pd.DataFrame, y: pd.Series, groups: pd.Series, cfg: dict) -> AutoML:
    fc = cfg["flaml"]
    automl = AutoML()
    with mlflow.start_run(run_name="flaml", nested=True):
        automl.fit(
            X_train=X,
            y_train=y,
            task="classification",
            metric=fc["metric"],
            time_budget=fc["time_budget"],
            estimator_list=fc["estimator_list"],
            eval_method="cv",
            n_splits=cfg["split"]["n_folds"],
            split_type="group",
            groups=groups,
            seed=cfg["seed"],
            verbose=1,
            mlflow_logging=False,
        )
        mlflow.log_params({"best_estimator": automl.best_estimator,
                           **{f"best.{k}": v for k, v in automl.best_config.items()}})
        mlflow.log_metric(f"cv_{fc['metric']}", 1 - automl.best_loss)
        mlflow.log_dict({est: cfg_ for est, cfg_ in automl.best_config_per_estimator.items()},
                        "best_config_per_estimator.json")
    return automl


def flaml_lgbm_to_optuna(config: dict | None) -> dict | None:
    """Translate FLAML's best LightGBM config into the Optuna search-space parameter names,
    so the Optuna study can be warm-started from it."""
    if not config:
        return None
    out = {k: config[k] for k in ("num_leaves", "min_child_samples", "learning_rate",
                                  "colsample_bytree", "reg_alpha", "reg_lambda") if k in config}
    if "log_max_bin" in config:
        # categorical in Optuna: an enqueued value outside the choices would crash the trial
        max_bin = 2 ** int(config["log_max_bin"]) - 1
        out["max_bin"] = min(MAX_BIN_CHOICES, key=lambda b: abs(b - max_bin))
    return out
