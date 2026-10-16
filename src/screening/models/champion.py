"""Final model choice: Optuna-tuned LightGBM vs FLAML's best model.

Both candidates are refit from scratch on the same grouped folds with a fixed configuration
(no early stopping on the validation fold), so their CV scores are directly comparable.
The test year is never used for the choice.
"""

from collections.abc import Callable

import numpy as np
import pandas as pd
from flaml import AutoML

from screening.models.optuna_tune import SCORERS


class FlamlModel:
    """FLAML's best estimator refit from scratch.

    FLAML imputes / encodes data at the AutoML level (`_transformer`), not inside the estimator
    wrapper, so the transformer fitted during the search is applied here as well.
    """

    def __init__(self, automl: AutoML):
        self.task = automl._state.task
        self.transformer = automl._transformer
        self.estimator = type(automl.model)(task="binary", **automl.best_config)

    def _prep(self, X: pd.DataFrame):
        return self.task.preprocess(X, self.transformer)

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "FlamlModel":
        self.estimator.fit(self._prep(X), y)
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        return self.estimator.predict_proba(self._prep(X))


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
