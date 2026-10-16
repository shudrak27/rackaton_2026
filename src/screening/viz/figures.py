"""Build English pitch figures from ``reports/ui/data.json`` only."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import PercentFormatter

MODEL = "#c8102e"
BASELINE = "#8c8c8c"
GOOD = "#2e7d32"
FIGURE_SIZE = (16, 9)
FIGURE_DPI = 100

SEGMENTS = {
    "first_invitation": "First invitation",
    "lapsed_regular": "Screened before, now overdue",
    "other": "Other",
    "repeated_nonresponder": "Repeated non-responder",
    "care_no_prevention": "In care, no prevention",
    "low_contact": "Low contact with healthcare",
    "recently_screened": "Recently screened",
    "regional": "Regional hypothesis",
}
FEATURES = {
    "n_prior_invitations": "Previous invitations",
    "invitation_sequence": "Invitations since last screening",
    "gyn_prevention_24m": "Gynaecologist check-ups (24 m)",
    "other_screening_36m": "Other cancer screenings (36 m)",
    "n_healthcare_contacts": "Healthcare contacts (12 m)",
    "dental_prevention_24m": "Dental check-ups (24 m)",
    "region": "VZP territorial office",
    "months_since_last_screening": "Months since last screening",
    "months_since_last_invitation": "Months since last invitation",
    "age_band": "Age band",
    "first_invitation": "First invitation",
    "recently_screened": "Screened in last 6 months",
    "has_gyn": "Registered with gynaecologist",
    "has_gp": "Registered with GP",
    "insurance_years": "Years insured with VZP",
    "n_preventive_visits": "GP + GYN check-ups (24 m)",
    "n_screenings_5y": "Screening procedures (5 y)",
    "never_screened": "No screening in five years",
    "overdue": "More than 24 months since screening",
}


def load_payload(path: str | Path) -> dict:
    """Load the aggregate export and reject anything other than a JSON object."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("the UI export must be a JSON object")
    return payload


def _style() -> None:
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 17,
        "axes.titlesize": 27,
        "axes.labelsize": 19,
        "xtick.labelsize": 15,
        "ytick.labelsize": 15,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    })


def _new(title: str):
    fig, ax = plt.subplots(figsize=FIGURE_SIZE, dpi=FIGURE_DPI, layout="constrained")
    ax.set_title(title, loc="left", weight="bold", pad=20)
    return fig, ax


def _todo(title: str, key: str):
    fig, ax = _new(title)
    ax.axis("off")
    ax.text(0.5, 0.5, f"[TODO: requested key {key}]", ha="center", va="center",
            fontsize=26, color=BASELINE, transform=ax.transAxes)
    return fig


def _save(fig, destination: Path, name: str) -> Path:
    path = destination / f"{name}.png"
    fig.savefig(path, dpi=FIGURE_DPI, facecolor="white")
    plt.close(fig)
    return path


def _attendance_by_invitations(payload: dict):
    rows = payload.get("attendance_by", {}).get("prior_invitations", [])
    title = "Attendance falls with every further invitation"
    if not rows:
        return _todo(title, "attendance_by.prior_invitations")
    fig, ax = _new(title)
    x = np.arange(len(rows))
    y = np.array([row["attendance"] for row in rows])
    labels = [str(row["group"]) for row in rows]
    ax.plot(x, y, marker="o", linewidth=4, markersize=10, color=MODEL)
    for pos, value in zip(x, y, strict=True):
        ax.annotate(f"{value:.0%}", (pos, value), xytext=(0, 12),
                    textcoords="offset points", ha="center", weight="bold")
    ax.set(xticks=x, xticklabels=labels, xlabel="Previous invitations (10 = 10+)",
           ylabel="Attendance within 12 months", ylim=(0, min(1, y.max() + 0.12)))
    ax.yaxis.set_major_formatter(PercentFormatter(1))
    ax.grid(axis="y", alpha=0.2)
    return fig


def _risk_deciles(payload: dict):
    rows = payload.get("deciles", [])
    title = "Risk ranking separates 68% attendance from 1.7%"
    if not rows:
        return _todo(title, "deciles")
    fig, ax = _new(title)
    deciles = [row["decile"] for row in rows]
    attendance = [row["attendance"] for row in rows]
    ax.bar(deciles, attendance, color=MODEL, width=0.72)
    for x, value in zip(deciles, attendance, strict=True):
        ax.text(x, value + 0.015, f"{value:.1%}", ha="center", fontsize=14, weight="bold")
    ax.set(xlabel="Risk decile (1 = lowest risk, 10 = highest)",
           ylabel="Attendance within 12 months", xticks=deciles,
           ylim=(0, min(1, max(attendance) + 0.12)))
    ax.yaxis.set_major_formatter(PercentFormatter(1))
    ax.grid(axis="y", alpha=0.2)
    return fig


def _targeting(payload: dict):
    rows = payload.get("targeting", [])
    title = "The model allocates scarce outreach more precisely"
    row = next((item for item in rows if abs(item.get("share", 0) - 0.1) < 1e-9), None)
    if row is None:
        return _todo(title, "targeting[share=0.1]")
    fig, axes = plt.subplots(1, 2, figsize=FIGURE_SIZE, dpi=FIGURE_DPI, layout="constrained")
    fig.suptitle(title, x=0.02, ha="left", fontsize=27, weight="bold")
    model_values = [row["bottom_attendance_model"], row["top_wasted_model"]]
    rule_values = [row["bottom_attendance_rule"], row["top_wasted_rule"]]
    axes[0].bar(["Model", "Rule"], [100 * model_values[0], 100 * rule_values[0]],
                color=[MODEL, BASELINE])
    axes[0].set(title="Lowest-risk 10%", ylabel="Attendance (%)")
    axes[0].bar_label(axes[0].containers[0], fmt="%.0f%%", padding=5, weight="bold")
    axes[1].bar(["Model", "Rule"], [model_values[1], rule_values[1]], color=[MODEL, BASELINE])
    axes[1].set(title=f"Highest-risk 10% ({row['n']:,.0f} women)",
                ylabel="Needless intensive contacts")
    axes[1].bar_label(axes[1].containers[0], labels=[f"{value:,.0f}" for value in model_values[1:]
                                                    + rule_values[1:]],
                      padding=5, weight="bold")
    for ax in axes:
        ax.grid(axis="y", alpha=0.2)
    return fig


def _feature_importance(payload: dict):
    rows = payload.get("feature_importance", [])[:10]
    title = "Invitation and prevention history drive the ranking"
    if not rows:
        return _todo(title, "feature_importance")
    rows = list(reversed(rows))
    labels = [FEATURES.get(row["feature"], row["feature"].replace("_", " ").title()) for row in rows]
    values = [row["importance"] for row in rows]
    colors = [GOOD if row.get("direction") == -1 else MODEL if row.get("direction") == 1 else BASELINE
              for row in rows]
    fig, ax = _new(title)
    ax.barh(labels, values, color=colors)
    ax.set(xlabel="Mean absolute SHAP value")
    ax.grid(axis="x", alpha=0.2)
    ax.text(1, -0.11, "Association, not causation", transform=ax.transAxes,
            ha="right", color=BASELINE, fontsize=15)
    return fig


def _segments(payload: dict):
    rows = payload.get("segments", [])
    title = "Segments differ in both size and attendance"
    if not rows:
        return _todo(title, "segments")
    fig, ax = _new(title)
    shares = np.array([row["share"] for row in rows])
    attendance = np.array([1 - row["non_attendance"] for row in rows])
    sizes = np.array([row["n"] for row in rows])
    areas = 500 + 2500 * sizes / sizes.max()
    ax.scatter(shares, attendance, s=areas, color=MODEL, alpha=0.72,
               edgecolors="white", linewidth=2)
    for x, y, row in zip(shares, attendance, rows, strict=True):
        ax.annotate(SEGMENTS.get(row["segment"], row["segment"]), (x, y),
                    xytext=(7, 7), textcoords="offset points", fontsize=13)
    ax.set(xlabel="Share of 2024 invitations", ylabel="Attendance within 12 months")
    ax.xaxis.set_major_formatter(PercentFormatter(1))
    ax.yaxis.set_major_formatter(PercentFormatter(1))
    ax.grid(alpha=0.2)
    return fig


def _months_since_screening(payload: dict):
    rows = [row for row in payload.get("attendance_by", {}).get(
        "months_since_last_screening", []) if row.get("group") != "none_in_5y"]
    title = "A recent screen reveals a preventable invitation gap"
    if not rows:
        return _todo(title, "attendance_by.months_since_last_screening")
    fig, ax = _new(title)
    labels = [str(row["group"]) for row in rows]
    values = [row["attendance"] for row in rows]
    colors = [MODEL if label in {"0", "1", "2-6"} else BASELINE for label in labels]
    bars = ax.bar(labels, values, color=colors)
    ax.bar_label(bars, labels=[f"{value:.1%}" for value in values], padding=5, fontsize=14)
    ax.set(xlabel="Months since last recorded screening", ylabel="Attendance within 12 months",
           ylim=(0, min(1, max(values) + 0.12)))
    ax.yaxis.set_major_formatter(PercentFormatter(1))
    ax.grid(axis="y", alpha=0.2)
    return fig


def _response_speed(payload: dict):
    rows = payload.get("segment_response_speed", [])
    title = "Response timing shows when reminders can still help"
    if not rows:
        return _todo(title, "segment_response_speed")
    fig, ax = _new(title)
    for row in rows:
        values = [row.get("3m"), row.get("6m"), row.get("12m")]
        if any(value is None for value in values):
            continue
        ax.plot([3, 6, 12], values, marker="o", linewidth=2.5,
                label=SEGMENTS.get(row["segment"], row["segment"]))
    ax.set(xticks=[3, 6, 12], xlabel="Months after invitation",
           ylabel="Cumulative attendance")
    ax.yaxis.set_major_formatter(PercentFormatter(1))
    ax.grid(alpha=0.2)
    ax.legend(fontsize=12, ncols=2, frameon=False)
    return fig


def _experiment_sizes(payload: dict):
    rows = payload.get("experiment_design", [])
    title = "A/B sample size depends strongly on the effect we seek"
    if not rows:
        return _todo(title, "experiment_design")
    mdes = sorted({row["mde_pp"] for row in rows})
    chosen_mde = 2 if 2 in mdes else mdes[0]
    selected = [row for row in rows if row["mde_pp"] == chosen_mde]
    selected.sort(key=lambda row: row["n_per_arm"])
    fig, ax = _new(title)
    labels = [SEGMENTS.get(row["segment"], row["segment"]) for row in selected]
    values = [row["n_per_arm"] for row in selected]
    colors = [MODEL if row.get("feasible") else BASELINE for row in selected]
    bars = ax.barh(labels, values, color=colors)
    ax.bar_label(bars, labels=[f"{value:,.0f}" for value in values], padding=6, fontsize=13)
    ax.set(xlabel=f"Women per arm for a +{chosen_mde:g} percentage-point effect")
    ax.grid(axis="x", alpha=0.2)
    return fig


BUILDERS = {
    "attendance_by_invitations": _attendance_by_invitations,
    "risk_deciles": _risk_deciles,
    "model_vs_rule": _targeting,
    "top10_shap": _feature_importance,
    "segment_map": _segments,
    "months_since_screening": _months_since_screening,
    "response_timing_by_segment": _response_speed,
    "ab_group_sizes": _experiment_sizes,
}


def make_figures(payload: dict, destination: str | Path) -> list[Path]:
    """Create the complete slide figure set, including explicit TODO cards."""
    _style()
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    return [_save(builder(payload), destination, name) for name, builder in BUILDERS.items()]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("reports/ui/data.json"))
    parser.add_argument("--output", type=Path, default=Path("reports/figures"))
    args = parser.parse_args()
    for path in make_figures(load_payload(args.input), args.output):
        print(path)


if __name__ == "__main__":
    main()
