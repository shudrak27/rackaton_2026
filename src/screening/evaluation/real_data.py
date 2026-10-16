"""Reproducible descriptive analysis of the delivered VZP invitation cohort.

This module does not train models or change production segment rules. Exports contain
aggregates only. Historical associations and assumed mailing costs are not causal effects.
"""

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

from screening.data import vzp
from screening.experiment.power import n_per_group
from screening.features.build import add_derived
from screening.segments.rules import assign

FLAGS = ["FIRST_INVITATION", "GP_REGISTERED", "GYN_REGISTERED_FLAG",
         "NEVER_SCREENED_BEFORE_FLAG", "SCREENING_3M_FLAG", "SCREENING_6M_FLAG",
         "SCREENING_12M_FLAG"]
CATEGORIES = FLAGS + ["AGE_BAND", "VZP_TERRITORIAL_AREA",
                      "GP_REG_DURATION_BAND", "GYN_REG_DURATION_BAND"]
SEGMENT_ORDER = ["recently_screened", "first_invitation", "lapsed_regular",
                 "low_contact", "care_no_prevention", "repeated_nonresponder",
                 "regional", "other"]


def read_delivery(path: str | Path) -> pd.DataFrame:
    """Read source fields without discarding supplied flags or counter discrepancies."""
    types = dict.fromkeys(CATEGORIES, "category")
    types.update({"PERSON_ID": "string", "INVITATION_ID": "string"})
    df = pd.read_csv(path, dtype=types, encoding="utf-8", low_memory=False)
    for column in FLAGS:
        if not df[column].isin(["A", "N"]).all():
            raise ValueError(f"{column} must contain fully observed A/N flags")
    for column in ["PERSON_ID", "INVITATION_ID"]:
        if df[column].isna().any() or df[column].str.strip().eq("").any():
            raise ValueError(f"{column} must not be missing")
    df["date"] = pd.to_datetime(df["INVITATION_DATE"], format="%d.%m.%Y", errors="raise")
    if df["date"].isna().any():
        raise ValueError("invitation dates must not be missing")
    df["year"] = df["date"].dt.year
    if df["INVITATION_ID"].duplicated().any() or df.duplicated(["PERSON_ID", "year"]).any():
        raise ValueError("expected unique invitations and at most one invitation per person/year")
    for months in [3, 6, 12]:
        df[f"attended_{months}m"] = df[f"SCREENING_{months}M_FLAG"].eq("A").astype(int)
    if ((df.attended_3m > df.attended_6m) | (df.attended_6m > df.attended_12m)).any():
        raise ValueError("cumulative outcome flags must be nested: 3M <= 6M <= 12M")
    return df


def wilson_interval(successes, n, alpha: float = 0.05):
    """Wilson score intervals for independent binary units; also valid at 0/n and n/n."""
    successes, n = np.asarray(successes, dtype=float), np.asarray(n, dtype=float)
    if np.any(n <= 0) or np.any(successes < 0) or np.any(successes > n):
        raise ValueError("Wilson intervals require 0 <= successes <= n and n > 0")
    z = norm.ppf(1 - alpha / 2)
    p = successes / n
    denominator = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denominator
    radius = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return np.maximum(centre - radius, 0), np.minimum(centre + radius, 1)


def group_rates(df: pd.DataFrame, column: str, outcome: str = "attended_12m") -> pd.DataFrame:
    """Invitation-weighted rates, with repeated invitations clustered by PERSON_ID.

    Unique-person groups use Wilson intervals. Repeated-person groups use a normal
    interval with person-cluster sandwich variance G/(G-1) * sum((s_i-p*n_i)^2)/N^2.
    These are descriptive pointwise intervals, not simultaneous territory comparisons.
    """
    if df.empty:
        return pd.DataFrame(columns=[column, "n", "attended", "clients", "attendance",
                                     "ci_low", "ci_high", "ci_method"])
    units = df.groupby([column, "PERSON_ID"], observed=True, dropna=False)[outcome].agg(
        unit_n="size", unit_success="sum")
    grouped = units.groupby(level=0, observed=True, dropna=False)
    result = grouped.agg(n=("unit_n", "sum"), attended=("unit_success", "sum"),
                         clients=("unit_n", "size"))
    result["attendance"] = result.attended / result.n
    p = result.attendance.reindex(units.index.get_level_values(0)).to_numpy()
    residual_sq = (units.unit_success - p * units.unit_n) ** 2
    sums = residual_sq.groupby(level=0, observed=True, dropna=False).sum()
    variance = result.clients / (result.clients - 1) * sums / result.n ** 2
    radius = norm.ppf(0.975) * np.sqrt(variance)
    result["ci_low"] = (result.attendance - radius).clip(0, 1)
    result["ci_high"] = (result.attendance + radius).clip(0, 1)
    result["ci_method"] = "person_cluster_normal"
    independent = result.n.eq(result.clients)
    low, high = wilson_interval(result.loc[independent, "attended"], result.loc[independent, "n"])
    result.loc[independent, "ci_low"] = low
    result.loc[independent, "ci_high"] = high
    result.loc[independent, "ci_method"] = "wilson"
    return result.reset_index()


def regional_shortlist(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Freeze an exploratory low-attendance territory list using development years only."""
    ec = cfg["eda"]
    end = ec["regional_reference_end_year"]
    if end >= cfg["split"]["test_year"]:
        raise ValueError("regional reference years must precede the reporting/test year")
    fraction = ec["regional_bottom_fraction"]
    if not 0 < fraction <= 1:
        raise ValueError("regional_bottom_fraction must be in (0, 1]")
    table = group_rates(df.loc[df.year <= end], "VZP_TERRITORIAL_AREA")
    if table.empty:
        raise ValueError("no regional reference observations")
    table = table.sort_values(["attendance", "VZP_TERRITORIAL_AREA"]).reset_index(drop=True)
    table["reference_rank"] = np.arange(1, len(table) + 1)
    table["selected"] = table.reference_rank <= math.ceil(len(table) * fraction)
    return table


def hypothesis_masks(df: pd.DataFrame, cfg: dict, territories: list[str]) -> dict:
    """Overlapping, pre-invitation hypotheses; counts remain source procedure counts."""
    c = cfg["segments"]
    screens, months = df.PRIOR_SCREEN_COUNT_5Y, df.MONTHS_SINCE_LAST_SCREEN
    contacts = df.HEALTHCARE_CONTACT_12M_CNT
    return {
        "lapsed_regular": (screens >= c["lapsed_min_screenings_5y"]) & (months > c["lapsed_min_months"]),
        "low_contact": (contacts <= c["low_contact_max_contacts"]) | (
            df.GP_REGISTERED.eq("N") & df.GYN_REGISTERED_FLAG.eq("N")),
        "care_no_prevention": (contacts >= c["care_min_contacts"]) & (
            df.GP_PREVENTION_24M_CNT.add(df.GYN_PREVENTION_24M_CNT).eq(0)),
        "repeated_nonresponder": (df.PRIOR_INVITATION_COUNT - 1 >= c["repeated_min_invitations"]) & screens.eq(0),
        "regional": df.VZP_TERRITORIAL_AREA.isin(territories),
    }


def exclusive_planning_segments(df: pd.DataFrame, cfg: dict, territories: list[str]) -> pd.Series:
    """Keep production priority; add regional only among remaining 'other' invitations.

    This planning overlay does not modify production rules. The production adapter
    uses count - 1 for first invitation; the supplied flag is preserved in raw EDA.
    """
    source_columns = [c for c in df.columns if c in vzp.COLUMNS or c == "FIRST_INVITATION"]
    canonical = add_derived(vzp.to_canonical(df[source_columns]))
    segment = assign(canonical, cfg)
    segment.loc[segment.eq("other") & df.VZP_TERRITORIAL_AREA.isin(territories)] = "regional"
    return segment


def segment_summary(df: pd.DataFrame, masks: dict) -> pd.DataFrame:
    rows = []
    for name, mask in masks.items():
        subset = df.loc[mask].assign(segment=name)
        if subset.empty:
            rows.append({"segment": name, "n": 0, "clients": 0, "attended": 0,
                         "attendance": np.nan, "ci_low": np.nan, "ci_high": np.nan})
        else:
            rows.extend(group_rates(subset, "segment").to_dict("records"))
    return pd.DataFrame(rows)


def experiment_sizes(segments: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Separate 1:1 two-arm trials; annual unique clients are an upper recruitment bound."""
    rows = []
    eligible = segments.loc[~segments.segment.isin(["recently_screened", "first_invitation", "other"])]
    for row in eligible.itertuples():
        for mde_pp in cfg["experiment"]["mde_pp"]:
            p = row.attendance
            if not np.isfinite(p) or not 0 < p < p + mde_pp / 100 < 1:
                continue
            n = n_per_group(p, mde_pp / 100, cfg["experiment"]["alpha"], cfg["experiment"]["power"])
            rows.append({"segment": row.segment, "baseline_attendance": p,
                         "available_clients": row.clients, "mde_pp": mde_pp,
                         "n_control": n, "n_treatment": n, "n_total": 2 * n,
                         "feasible_at_full_recruitment": 2 * n <= row.clients,
                         "required_recruitment_share": 2 * n / row.clients})
    return pd.DataFrame(rows)


def build_tables(df: pd.DataFrame, cfg: dict) -> dict[str, pd.DataFrame]:
    """Create aggregate tables for every requested plot, segment hypothesis and A/B design."""
    year = cfg["split"]["test_year"]
    annual = df.loc[df.year.eq(year)].copy()
    if annual.empty:
        raise ValueError(f"no rows for reporting year {year}")
    if annual.PERSON_ID.duplicated().any():
        raise ValueError("A/B planning requires one annual row per client")
    tables = {}
    tables["overview"] = pd.DataFrame([{
        "n": len(df), "clients": df.PERSON_ID.nunique(),
        "first_year": int(df.year.min()), "last_year": int(df.year.max()),
        "max_invitations_per_client": int(df.groupby("PERSON_ID").size().max()),
        "first_flag_counter_disagreements": int(
            (df.FIRST_INVITATION.eq("A") != df.PRIOR_INVITATION_COUNT.eq(1)).sum()),
    }])
    columns = {"invitations": "PRIOR_INVITATION_COUNT", "age": "AGE_BAND",
               "first_invitation": "FIRST_INVITATION"}
    for name, column in columns.items():
        tables[name] = group_rates(df, column)
    for name, column, bins, labels in [
        ("contacts", "HEALTHCARE_CONTACT_12M_CNT", [-1, 0, 2, 5, 10, 20, np.inf],
         ["0", "1-2", "3-5", "6-10", "11-20", "21+"]),
        ("gyn_prevention", "GYN_PREVENTION_24M_CNT", [-1, 0, 1, np.inf], ["0", "1", "2+"]),
        ("other_screening", "OTHER_SCREENING_36M_CNT", [-1, 0, 1, np.inf], ["0", "1", "2+"]),
    ]:
        grouped = df.assign(group=pd.cut(df[column], bins, labels=labels))
        tables[name] = group_rates(grouped, "group")
    tables["by_year"] = group_rates(df, "year")
    tables["regions_all_years"] = group_rates(df, "VZP_TERRITORIAL_AREA").sort_values("attendance")
    regions = group_rates(annual, "VZP_TERRITORIAL_AREA").sort_values(
        ["attendance", "VZP_TERRITORIAL_AREA"]).reset_index(drop=True)
    regions.insert(0, "rank", np.arange(1, len(regions) + 1))
    tables["regions_reporting_year"] = regions
    reference = regional_shortlist(df, cfg)
    tables["regional_reference"] = reference
    territories = reference.loc[reference.selected, "VZP_TERRITORIAL_AREA"].tolist()
    for scope, part in [("all_years", df), ("reporting_year", annual)]:
        tables[f"hypotheses_{scope}"] = segment_summary(part, hypothesis_masks(part, cfg, territories))
    annual["segment"] = exclusive_planning_segments(annual, cfg, territories)
    tables["segments_exclusive"] = group_rates(annual, "segment")
    tables["segments_exclusive"] = tables["segments_exclusive"].set_index("segment").reindex(
        [name for name in SEGMENT_ORDER if name in set(annual.segment)]).reset_index()
    tables["experiment_sizes"] = experiment_sizes(tables["segments_exclusive"], cfg)
    timing = []
    for months, days in [(3, 90), (6, 180), (12, 365)]:
        overall = group_rates(df.assign(horizon=months), "horizon", f"attended_{months}m")
        overall["days"] = days
        timing.append(overall)
    tables["response_timing"] = pd.concat(timing, ignore_index=True)
    cost = cfg["eda"]["letter_cost_czk"]
    if isinstance(cost, bool) or not np.isfinite(cost) or cost < 0:
        raise ValueError("letter_cost_czk must be a finite nonnegative assumption")
    recent = []
    for cutoff in [1, 6]:
        for invitation_year, part in df.groupby("year"):
            hit = part.loc[part.MONTHS_SINCE_LAST_SCREEN.between(0, cutoff)]
            recent.append({"year": invitation_year, "months_max": cutoff,
                           "n": len(hit), "clients": hit.PERSON_ID.nunique(),
                           "share": len(hit) / len(part), "attended": int(hit.attended_12m.sum()),
                           "attendance": hit.attended_12m.mean(), "letter_cost_czk": cost,
                           "scenario_gross_cost_czk": len(hit) * cost})
    tables["recent_screening_cost"] = pd.DataFrame(recent)
    return tables


def save_tables(tables: dict, destination: Path, source: Path, cfg: dict) -> None:
    """Write aggregate CSVs plus source fingerprint and assumptions for reproducibility."""
    destination.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        table.to_csv(destination / f"{name}.csv", index=False)
    digest = hashlib.sha256()
    with source.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    manifest = {"source_file": source.name, "source_bytes": source.stat().st_size,
                "sha256": digest.hexdigest(), "reporting_year": cfg["split"]["test_year"],
                "cohort": "continuous VZP insurance 2015-2025, per delivery specification",
                "segments": cfg["segments"], "eda": cfg["eda"], "experiment": cfg["experiment"],
                "regional_selection": "development years only; descriptive, not a proven access barrier",
                "figures": "pooled CIs cluster by person; annual CIs use Wilson; pointwise 95%"}
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def make_figures(tables: dict, destination: Path, year: int) -> list[Path]:
    """Save presentation PNGs; matplotlib is part of the project's dev dependencies."""
    import matplotlib.pyplot as plt
    from matplotlib.ticker import PercentFormatter

    destination.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "figure.facecolor": "white", "axes.facecolor": "white"})
    outputs = []
    years = tables["by_year"].year
    period = f"{int(years.min())}-{int(years.max())}"

    def save(fig, name):
        path = destination / f"{name}.png"
        fig.savefig(path, dpi=180, bbox_inches="tight")
        plt.close(fig)
        outputs.append(path)

    for key, column, title, xlabel in [
        ("invitations", "PRIOR_INVITATION_COUNT", "Attendance falls with repeated invitations", "Delivered invitation count (includes current invitation)"),
        ("age", "AGE_BAND", "Attendance by age band", "Age band"),
        ("contacts", "group", "Attendance by healthcare contact", "Provider/day contacts in the preceding 12 months"),
        ("gyn_prevention", "group", "Attendance by gynecology prevention", "Preventive visits in the preceding 24 months"),
        ("other_screening", "group", "Attendance by other screening", "Other screening procedures in the preceding 36 months"),
    ]:
        table = tables[key]
        fig, ax = plt.subplots(figsize=(10, 5.5), layout="constrained")
        x = np.arange(len(table))
        errors = np.vstack([table.attendance - table.ci_low, table.ci_high - table.attendance])
        ax.errorbar(x, table.attendance, yerr=errors, fmt="o-", color="#176B87", capsize=4)
        for pos, row in zip(x, table.itertuples(), strict=True):
            ax.annotate(f"{row.attendance:.1%}", (pos, row.attendance), xytext=(0, 10),
                        textcoords="offset points", ha="center")
        ax.set(xticks=x, xticklabels=table[column].astype(str), xlabel=xlabel,
               ylabel="Screened within 365 days", title=title, ylim=(0, min(1, table.ci_high.max() + 0.12)))
        ax.yaxis.set_major_formatter(PercentFormatter(1))
        ax.grid(axis="y", alpha=0.2)
        fig.supxlabel(f"{period} invitations; 95% CIs account for repeated clients. Associations, not causal effects.", fontsize=9)
        save(fig, key)

    table = tables["regions_reporting_year"]
    fig, ax = plt.subplots(figsize=(12, max(8, len(table) * 0.25)), layout="constrained")
    positions = np.arange(len(table))
    ax.errorbar(table.attendance, positions,
                xerr=np.vstack([table.attendance - table.ci_low, table.ci_high - table.attendance]),
                fmt="o", markersize=3, color="#176B87", capsize=2)
    labels = [f"{r.VZP_TERRITORIAL_AREA}  (n={r.n:,})" for r in table.itertuples()]
    ax.set(yticks=positions, yticklabels=labels, xlabel="Screened within 365 days",
           title=f"VZP territories: {year} attendance and pointwise 95% Wilson intervals")
    ax.invert_yaxis()
    ax.xaxis.set_major_formatter(PercentFormatter(1))
    overall = tables["by_year"].set_index("year").loc[year, "attendance"]
    ax.axvline(overall, color="#C76D38", linestyle="--", label="Overall annual attendance")
    ax.legend(loc="lower right")
    ax.tick_params(axis="y", labelsize=9)
    fig.supxlabel("Crude descriptive ranking; not adjusted for case mix or 75 comparisons. Territory is not an access measure.", fontsize=9)
    save(fig, "regions_ranking")

    table = tables["response_timing"]
    fig, ax = plt.subplots(figsize=(9, 5), layout="constrained")
    ax.plot(table.days, table.attendance, "o-", color="#176B87")
    for row in table.itertuples():
        ax.annotate(f"{row.attendance:.2%}", (row.days, row.attendance), xytext=(0, 10),
                    textcoords="offset points", ha="center")
    ax.set(xticks=table.days, xlabel="Days since invitation", ylabel="Cumulative attendance",
           title="Observed attendance by follow-up horizon", ylim=(0, 0.26))
    ax.yaxis.set_major_formatter(PercentFormatter(1))
    fig.supxlabel(f"{period}; cumulative outcomes, not appointment dates or causal effects of reminders.", fontsize=9)
    save(fig, "response_timing")

    recent = tables["recent_screening_cost"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), layout="constrained")
    for cutoff, colour in [(1, "#176B87"), (6, "#C76D38")]:
        part = recent.loc[recent.months_max.eq(cutoff)]
        axes[0].plot(part.year, part.n, "o-", label=f"0-{cutoff} months", color=colour)
        axes[1].plot(part.year, part.scenario_gross_cost_czk / 1000, "o-",
                     label=f"0-{cutoff} months", color=colour)
    axes[0].set(title="Invitations after a recent recorded screen", ylabel="Invitations")
    axes[1].set(title="Illustrative gross mailing expenditure", ylabel="CZK thousands")
    for ax in axes:
        ax.set_xticks(sorted(recent.year.unique()))
        ax.legend()
        ax.grid(axis="y", alpha=0.2)
    cost = recent.letter_cost_czk.iloc[0]
    fig.supxlabel(f"ASSUMPTION: {cost:g} CZK/letter. Windows overlap; do not add them. Expenditure is not proven avoidable savings.", fontsize=9)
    save(fig, "recent_screening_cost")
    return outputs
