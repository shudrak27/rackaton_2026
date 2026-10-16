import lightgbm as lgb
import numpy as np

from screening.data import schema as s
from screening.data.profile import leakage_suspects, profile
from screening.evaluation.explain import importance
from screening.features.build import build
from screening.models.champion import choose
from screening.data.split import group_folds
from screening.scoring import make_bundle, score


def test_profile_flags_leaky_feature(prepared, cfg):
    df = prepared.copy()
    rng = np.random.default_rng(0)
    df["leaky"] = df[s.TARGET] + rng.normal(0, 0.01, len(df))
    df, feats = build(df, cfg)
    tables = profile(df, feats)
    assert leakage_suspects(tables["single_feature_auc"], 0.95) == ["leaky"]
    assert {"columns", "by_year", "checks", "by_prior_invitations"} <= set(tables)


def _fit_small(prepared, cfg):
    df, feats = build(prepared, cfg)
    model = lgb.LGBMClassifier(n_estimators=30, verbose=-1).fit(df[feats], df[s.TARGET])
    return df, feats, model


def test_score_new_invitations_without_target(raw, prepared, cfg):
    df, feats, model = _fit_small(prepared, cfg)
    bundle = make_bundle(model, df[feats], "lgbm")
    new = raw.drop(columns=[s.ATTENDED]).head(500).copy()
    new.loc[new.index[:3], s.REGION] = "UNSEEN"  # unseen category must not break scoring
    out = score(new, bundle, cfg)
    assert len(out) == 500 and out["risk_non_attendance"].between(0, 1).all()
    assert out["intervention"].notna().all()
    # same rows scored in training and scoring paths give the same risk
    ref = model.predict_proba(df[feats].head(500).iloc[3:])[:, 1]
    got = out.set_index(s.CLIENT_ID).loc[df[s.CLIENT_ID].head(500).iloc[3:], "risk_non_attendance"]
    assert np.allclose(np.sort(ref), np.sort(got.to_numpy()))


def test_champion_picks_better_model(prepared, cfg):
    df, feats = build(prepared, cfg)
    X, y = df[feats], df[s.TARGET]
    folds = group_folds(df, 3)
    good = lambda: lgb.LGBMClassifier(n_estimators=50, verbose=-1)
    weak = lambda: lgb.LGBMClassifier(n_estimators=1, num_leaves=2, verbose=-1)
    name, scores = choose({"good": good, "weak": weak}, X, y, folds, "roc_auc")
    assert name == "good" and scores["good"] > scores["weak"]


def test_importance_shap_and_permutation(prepared, cfg):
    df, feats, model = _fit_small(prepared, cfg)
    X, y = df[feats], df[s.TARGET]

    class Wrapped:  # non-LightGBM model -> permutation path
        def predict_proba(self, X):
            return model.predict_proba(X)

    shap_imp = importance(model, X, y, sample=2000)
    perm_imp = importance(Wrapped(), X, y, sample=2000)
    assert shap_imp["method"].iloc[0] == "mean_abs_shap"
    assert perm_imp["method"].iloc[0] == "permutation_auc_drop"
    assert set(shap_imp["feature"]) == set(feats) == set(perm_imp["feature"])


def test_flaml_warm_start_max_bin_is_valid():
    from screening.models.flaml_search import flaml_lgbm_to_optuna
    from screening.models.optuna_tune import MAX_BIN_CHOICES
    for log_max_bin in range(3, 11):
        assert flaml_lgbm_to_optuna({"log_max_bin": log_max_bin})["max_bin"] in MAX_BIN_CHOICES
