import numpy as np
import pytest

from screening.data import schema as s
from screening.evaluation.metrics import decile_table, summary
from screening.experiment.power import n_per_group
from screening.features.build import build
from screening.segments.rules import INTERVENTIONS, assign


def test_no_target_or_keys_in_features(prepared, cfg):
    _, feats = build(prepared, cfg)
    assert not set(feats) & (set(s.KEYS) | set(s.TARGETS))


def test_exclude_from_config(prepared, cfg):
    c = {**cfg, "features": {"exclude": [s.REGION]}}
    _, feats = build(prepared, c)
    assert s.REGION not in feats


def test_metrics_perfect_score():
    y = np.array([0, 0, 1, 1, 1, 1, 1, 1, 1, 1])
    m = summary(y, y.astype(float), top_k=[0.2])
    assert m["roc_auc"] == 1.0 and m["precision_top20"] == 1.0
    assert decile_table(y, y.astype(float), n_bins=5)["n"].sum() == len(y)


def test_power_known_value():
    # p0=10 %, +2 p.p., alpha .05, power .8 -> ~3.8k per arm
    assert 3700 < n_per_group(0.10, 0.02) < 3900


def test_segments_cover_everyone(prepared, cfg):
    seg = assign(prepared, cfg)
    assert seg.notna().all() and set(seg) <= set(INTERVENTIONS)


@pytest.mark.slow
def test_pipeline_smoke(tmp_path, cfg, raw):
    from screening.pipeline import train

    data = tmp_path / "d.parquet"
    raw.to_parquet(data)
    c = {**cfg,
         "data": {**cfg["data"], "path": str(data)},
         "flaml": {**cfg["flaml"], "time_budget": 10, "estimator_list": ["lgbm"]},
         "optuna": {**cfg["optuna"], "n_trials": 2},
         "mlflow": {**cfg["mlflow"], "tracking_uri": f"sqlite:///{(tmp_path / 'm.db').as_posix()}"},
         "paths": {"reports": str(tmp_path / "reports"), "models": str(tmp_path / "models")}}
    res = train(c)
    assert res["model"]["roc_auc"] > 0.6
    assert res["champion"] in ("optuna_lgbm", "flaml_lgbm")
    assert (tmp_path / "models" / "model.joblib").exists()
