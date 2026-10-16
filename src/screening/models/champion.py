"""Final model choice: Optuna-tuned LightGBM vs FLAML's best model.

Both candidates are refit from scratch on the same grouped folds with a fixed configuration
(no early stopping on the validation fold), so their CV scores are directly comparable.
The test year is never used for the choice.
"""

from collections.abc import Callable

import numpy as np
import pandas as pd
from flaml import AutoML
from flaml.automl.data import DataTransformer

from screening.models.optuna_tune import SCORERS


class FlamlModel:
    """FLAML's best estimator refit from scratch.

    FLAML imputes / encodes data at the AutoML level (DataTransformer), not inside the
    estimator wrapper. A fresh transformer is fitted on every `fit`, so imputation statistics
    never come from the validation fold.
    """

    def __init__(self, automl: AutoML):
        self.task = automl._state.task
        self.estimator_cls = type(automl.model)
        self.config = dict(automl.best_config)

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "FlamlModel":
        self.transformer = DataTransformer()
        Xt, yt = self.transformer.fit_transform(X, y, self.task)
        self.estimator = self.estimator_cls(task="binary", **self.config)
        self.estimator.fit(Xt, yt)
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        return self.estimator.predict_proba(self.task.preprocess(X, self.transformer))


def flaml_factory(automl: AutoML) -> Callable:
    return lambda: FlamlModel(automl)


def cv_score(make_model: Callable, X: pd.DataFrame, y: pd.Series, folds: list[tuple],
             metric: str) -> float:
    score_fn = SCORERS[metric]
    scores = []
    for tr, va in folds:
        model = make_model()
        model.fit(X.iloc[tr], y.iloc[tr])
        scores.append(score_fn(y.iloc[va], model.predict_proba(X.iloc[va])[:, 1]))
    return float(np.mean(scores))


def choose(candidates: dict[str, Callable], X: pd.DataFrame, y: pd.Series, folds: list[tuple],
           metric: str) -> tuple[str, dict[str, float]]:
    scores = {name: cv_score(make, X, y, folds, metric) for name, make in candidates.items()}
    return max(scores, key=scores.get), scores
