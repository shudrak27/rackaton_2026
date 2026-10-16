"""Greedy outreach planning from ASSUMED effects; replace assumptions after A/B tests.

Risk does not identify causal benefit. Uplifts here are absolute attendance percentage
points by segment. The heuristic is deterministic but does not guarantee a globally
optimal allocation. Plans contain selected invitations only, at most one per client.
"""

from decimal import Decimal

import numpy as np
import pandas as pd

PLAN_COLUMNS = ["intervention", "cost_czk", "uplift_pp",
                "expected_additional_screenings", "efficiency_per_czk"]


def allocate(scored_df: pd.DataFrame, interventions_cfg: dict,
             budget_czk: float) -> pd.DataFrame:
    """Rank all eligible client-action pairs by expected additional screenings / CZK.

    Config is {action: {cost_czk: number, uplift_pp: {segment: percentage_points}}}.
    Unlisted segments are ineligible; nonpositive effects are skipped. If risk is
    supplied, expected uplift is capped by non-attendance risk (remaining headroom).
    Repeated invitations compete for the same client. Zero-cost positive actions
    rank first. Ties retain config order then input row order. Inputs are unchanged.
    """
    if not np.isfinite(budget_czk) or budget_czk < 0:
        raise ValueError("budget_czk must be finite and nonnegative")
    if scored_df["client_id"].isna().any():
        raise ValueError("client_id must not be missing")
    scored_df["segment"]  # required even for an empty configuration
    if set(PLAN_COLUMNS) & set(scored_df.columns):
        raise ValueError("input already contains allocation columns")
    risk = None
    if "risk_non_attendance" in scored_df:
        risk = scored_df["risk_non_attendance"].to_numpy(dtype=float)
        if not np.isfinite(risk).all() or ((risk < 0) | (risk > 1)).any():
            raise ValueError("risk_non_attendance must be in [0, 1]")
    candidates, costs = [], {}
    for action, settings in interventions_cfg.items():
        if not isinstance(action, str) or not action:
            raise ValueError("intervention names must be nonempty strings")
        cost = float(settings["cost_czk"])
        effects = settings["uplift_pp"]
        values = np.asarray(list(effects.values()), dtype=float)
        if not np.isfinite(cost) or cost < 0:
            raise ValueError("cost_czk must be finite and nonnegative")
        costs[action] = Decimal(str(cost))
        if not np.isfinite(values).all() or (np.abs(values) > 100).any():
            raise ValueError("uplift_pp must be finite percentage points in [-100, 100]")
        uplift = scored_df["segment"].astype(object).map(effects).fillna(0).to_numpy(dtype=float)
        additional = np.maximum(uplift / 100, 0)
        if risk is not None:
            additional = np.minimum(additional, risk)
        positions = np.flatnonzero(additional > 0)
        candidates.append(pd.DataFrame({
            "position": positions, "intervention": action, "cost_czk": cost,
            "uplift_pp": uplift[positions], "expected_additional_screenings": additional[positions],
            "efficiency_per_czk": additional[positions] / cost if cost else np.inf,
        }))
    empty = scored_df.iloc[:0].copy()
    for column in PLAN_COLUMNS:
        empty[column] = pd.Series(index=empty.index, dtype="str" if column == "intervention" else float)
    if not candidates:
        return empty
    ranked = pd.concat(candidates, ignore_index=True).sort_values("efficiency_per_czk", ascending=False,
                                                               kind="stable")
    selected, clients = [], set()
    spent, budget = Decimal(0), Decimal(str(budget_czk))
    client_ids = scored_df["client_id"].to_numpy()
    for row in ranked.itertuples():
        client = client_ids[row.position]
        cost = costs[row.intervention]
        if client in clients or spent + cost > budget:
            continue
        selected.append(row.Index)
        clients.add(client)
        spent += cost
    if not selected:
        return empty
    chosen = ranked.loc[selected]
    plan = scored_df.iloc[chosen["position"].to_numpy()].copy()
    for column in PLAN_COLUMNS:
        plan[column] = chosen[column].to_numpy()
    return plan


def summary(plan: pd.DataFrame) -> dict:
    """Totals and record-list breakdowns by segment and intervention; zero benefit costs None."""
    spent = float(sum((Decimal(str(cost)) for cost in plan["cost_czk"]), Decimal(0)))
    additional = float(plan["expected_additional_screenings"].sum())
    result = {"n_clients": len(plan), "budget_spent_czk": spent,
              "expected_additional_screenings": additional,
              "cost_per_additional_screening_czk": spent / additional if additional else None}
    for column in ("segment", "intervention"):
        records = []
        for key, group in plan.groupby(plan[column].astype(object), dropna=False, sort=False):
            cost = float(sum((Decimal(str(value)) for value in group["cost_czk"]), Decimal(0)))
            effect = float(group["expected_additional_screenings"].sum())
            records.append({column: key, "n_clients": len(group), "budget_spent_czk": cost,
                            "expected_additional_screenings": effect,
                            "cost_per_additional_screening_czk": cost / effect if effect else None})
        result[f"by_{column}"] = records
    return result
