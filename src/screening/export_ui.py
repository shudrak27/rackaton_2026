"""Aggregates for the demo UI / slides in one JSON file (reports/ui/data.json).

Only aggregates leave this module: no client ids, no row-level data. Groups smaller than
MIN_CELL are suppressed. Reads the training reports (`python -m screening train` first) and
the raw data for descriptive breakdowns.
"""

import json
import math
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, roc_curve

from screening.config import resolve
from screening.data import load, split
from screening.data import schema as s
from screening.evaluation.metrics import ap_attendance
from screening.features.build import build
from screening.models.baseline import baseline_score
from screening.segments import rules

MIN_CELL = 20
Z95 = 1.959964


def wilson(k: float, n: float) -> tuple[float, float]:
    """95 % Wilson interval for a proportion."""
    if n == 0:
        return (math.nan, math.nan)
    p = k / n
    centre = (p + Z95 ** 2 / (2 * n)) / (1 + Z95 ** 2 / n)
    half = Z95 * math.sqrt(p * (1 - p) / n + Z95 ** 2 / (4 * n ** 2)) / (1 + Z95 ** 2 / n)
    return (centre - half, centre + half)


def rate_table(df: pd.DataFrame, by, outcome: str = s.ATTENDED) -> list[dict]:
    """Attendance per group with Wilson CI; small groups suppressed."""
    g = df.groupby(by, observed=True, dropna=False)[outcome].agg(["size", "sum"])
    rows = []
    for key, r in g.iterrows():
        if r["size"] < MIN_CELL:
            continue
        lo, hi = wilson(r["sum"], r["size"])
        rows.append({"group": None if pd.isna(key) else key,
                     "n": int(r["size"]), "attendance": r["sum"] / r["size"],
                     "ci_low": lo, "ci_high": hi})
    return rows


def _curve(y: np.ndarray, score: np.ndarray, points: int = 101) -> list[dict]:
    """ROC downsampled to ~`points` points (y = 1 means non-attendance)."""
    fpr, tpr, _ = roc_curve(y, score)
    idx = np.unique(np.linspace(0, len(fpr) - 1, points).round().astype(int))
    return [{"fpr": float(fpr[i]), "tpr": float(tpr[i])} for i in idx]


def _gain(y: np.ndarray, score: np.ndarray, steps: int = 20) -> list[dict]:
    """Share of all non-attenders captured when targeting the top-k % by score."""
    order = np.argsort(-score, kind="stable")
    captured = np.cumsum(y[order]) / y.sum()
    out = []
    for k in np.linspace(1 / steps, 1, steps):
        n = max(int(round(k * len(y))), 1)
        out.append({"top_share": float(k), "captured": float(captured[n - 1]),
                    "attendance_in_top": float(1 - y[order][:n].mean())})
    return out


def targeting_comparison(y: np.ndarray, model: np.ndarray, rule: np.ndarray,
                         shares=(0.1, 0.2, 0.3), seed: int = 0) -> list[dict]:
    """Model vs rule in people, not AUC (y = 1 means non-attendance).

    top: intensive outreach to the highest-risk share -> attenders contacted needlessly.
    bottom: lowest-risk share ("a letter is enough") -> their attendance.
    The rule has few distinct values; ties are broken randomly (fixed seed), not by row order."""
    rule = rule + np.random.default_rng(seed).random(len(rule)) * 1e-6
    att = 1 - y
    rows = []
    for share in shares:
        m = max(int(share * len(y)), 1)
        top_m, top_r = np.argsort(-model)[:m], np.argsort(-rule)[:m]
        bot_m, bot_r = np.argsort(model)[:m], np.argsort(rule)[:m]
        rows.append({"share": share, "n": m,
                     "top_wasted_model": int(att[top_m].sum()), "top_wasted_rule": int(att[top_r].sum()),
                     "bottom_attendance_model": float(att[bot_m].mean()),
                     "bottom_attendance_rule": float(att[bot_r].mean())})
    return rows


def ranking_quality(y: np.ndarray, model: np.ndarray, rule: np.ndarray) -> list[dict]:
    """ROC-AUC and average precision for attendance (the 19 % minority class) vs a random score.

    AP on non-attendance is not shown: with ~81 % positives even a random score gets ~0.81."""
    rows = [{"scorer": "random", "roc_auc": 0.5, "ap_attendance": float(1 - y.mean())}]
    for name, score in (("rule", rule), ("model", model)):
        rows.append({"scorer": name, "roc_auc": float(roc_auc_score(y, score)),
                     "ap_attendance": float(ap_attendance(y, score))})
    return rows


def _records(path) -> list[dict]:
    return pd.read_csv(path).replace({np.nan: None}).to_dict("records") if path.exists() else []


def build_payload(cfg: dict) -> dict:
    reports = resolve(cfg["paths"]["reports"])
    df, _ = build(load.load(cfg), cfg)
    _, test_df = split.temporal_split(df, cfg["split"]["test_year"],
                                      cfg["split"].get("purge_months", 0))

    scored = pd.read_parquet(reports / "scored_test.parquet")
    same = (len(scored) == len(test_df)
            and (scored[s.CLIENT_ID].astype(str).to_numpy() == test_df[s.CLIENT_ID].astype(str).to_numpy()).all())
    if not same:
        raise ValueError("reports/scored_test.parquet does not match the current data/config; rerun train")
    y = scored["y"].to_numpy()
    risk = scored["risk_non_attendance"].to_numpy()
    base = baseline_score(test_df)
    test_df = test_df.assign(segment=scored["segment"].to_numpy())

    breakdowns = {"year": df[s.INVITATION_YEAR]}
    if s.N_PRIOR_INVITATIONS in df:
        breakdowns["prior_invitations"] = df[s.N_PRIOR_INVITATIONS].clip(upper=10)
    if s.AGE_BAND in df:
        breakdowns["age_band"] = df[s.AGE_BAND]
    if s.N_HEALTHCARE_CONTACTS in df:
        breakdowns["healthcare_contacts_12m"] = pd.cut(
            df[s.N_HEALTHCARE_CONTACTS], [-1, 0, 2, 5, 11, 22, 10_000],
            labels=["0", "1-2", "3-5", "6-11", "12-22", "23+"])
    for col, cap in ((s.GYN_PREVENTION_24M, 3), (s.OTHER_SCREENING_36M, 4)):
        if col in df:
            breakdowns[col] = df[col].clip(upper=cap)
    if s.MONTHS_SINCE_LAST in df:
        since = pd.cut(df[s.MONTHS_SINCE_LAST], [-1, 0, 1, 6, 24, 36, 48, 60, 1000],
                       labels=["0", "1", "2-6", "7-24", "25-36", "37-48", "49-60", "61+ (window edge)"])
        breakdowns["months_since_last_screening"] = (
            since.cat.add_categories("none_in_5y").fillna("none_in_5y"))

    speed = (test_df.groupby("segment")[[s.ATTENDED_3M, s.ATTENDED_6M, s.ATTENDED]].mean()
             .rename(columns={s.ATTENDED_3M: "3m", s.ATTENDED_6M: "6m", s.ATTENDED: "12m"})
             .reset_index().to_dict("records")) if s.ATTENDED_3M in test_df else []

    region = rate_table(df, s.REGION) if s.REGION in df else []
    risk_by_region = scored.groupby(s.REGION)["risk_non_attendance"].mean() if s.REGION in scored else {}
    for r in region:
        r["mean_predicted_risk_test"] = float(risk_by_region.get(r["group"], np.nan))

    budget_path = reports / "budget_summary.json"
    return {
        "meta": {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "n_invitations": int(len(df)), "n_clients": int(df[s.CLIENT_ID].nunique()),
            "years": sorted(int(v) for v in df[s.INVITATION_YEAR].unique()),
            "attendance_overall": float(df[s.ATTENDED].mean()),
            "test_year": cfg["split"]["test_year"], "n_test": int(len(test_df)),
            "calibration": (cfg.get("calibration") or {}).get("method"),
            "min_cell": MIN_CELL,
        },
        "test_metrics": _records(reports / "test_metrics.csv"),
        "roc": {"model": _curve(y, risk), "baseline": _curve(y, base)},
        "gain": {"model": _gain(y, risk), "baseline": _gain(y, base)},
        "targeting": targeting_comparison(y, risk, base),
        "ranking_quality": ranking_quality(y, risk, base),
        "deciles": _records(reports / "decile_table.csv"),
        "calibration": _records(reports / "calibration.csv"),
        "feature_importance": _records(reports / "feature_importance.csv")[:15],
        "segments": _records(reports / "segments.csv"),
        "segment_response_speed": speed,
        "interventions": rules.INTERVENTIONS,
        "experiment_design": _records(reports / "experiment_design.csv"),
        "budget": json.loads(budget_path.read_text(encoding="utf-8")) if budget_path.exists() else None,
        "fairness": {c: _records(reports / f"fairness_{c}.csv")
                     for c in (cfg.get("fairness") or {}).get("group_columns", [])},
        "attendance_by": {**{k: rate_table(df, v) for k, v in breakdowns.items()},
                          "region": region},
        "recently_screened_per_year": rate_table(
            df[df[s.MONTHS_SINCE_LAST] <= cfg["segments"]["recent_max_months"]], s.INVITATION_YEAR),
    }


def _clean(obj):
    """JSON-safe: numpy scalars -> python, NaN -> null."""
    if isinstance(obj, dict):
        return {str(k): _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        return None if math.isnan(obj) else float(obj)
    if isinstance(obj, (pd.Timestamp, datetime)):
        return obj.isoformat()
    return obj


def export(cfg: dict, out=None):
    out = resolve(out or f"{cfg['paths']['reports']}/ui/data.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(_clean(build_payload(cfg)), ensure_ascii=False, indent=1), encoding="utf-8")
    return out
