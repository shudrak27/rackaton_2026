"""Demo dashboard (MVP) — Rakathon 2026 / VZP: who will not attend mammography screening.

    streamlit run app/dashboard.py

Reads only the aggregate file produced by `python -m screening export-ui`
(reports/ui/data.json): no row-level data, no model, no raw CSV needed at demo time.
"""

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from screening.experiment.power import n_per_group

DATA = Path(__file__).resolve().parents[1] / "reports" / "ui" / "data.json"

MODEL, BASE, GREY, GOOD = "#c8102e", "#8c8c8c", "#d9d9d9", "#2e7d32"

SEGMENTS = {
    "first_invitation": "First invitation",
    "lapsed_regular": "Screened before, now overdue",
    "other": "Other",
    "repeated_nonresponder": "Repeated non-responder",
    "care_no_prevention": "In care, no prevention",
    "low_contact": "Low contact with healthcare",
    "recently_screened": "Recently screened",
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
    "never_screened": "No screening in 5 years",
    "overdue": "More than 24 months since screening",
    "n_registrations": "Registrations (GP, GYN)",
    "preventive_share": "Share of preventive contacts",
    "screenings_per_invitation": "Screenings per invitation",
    "gp_prevention_24m": "GP check-ups (24 m)",
    "gyn_registration_band": "Gynaecologist registration length",
    "gp_registration_band": "GP registration length",
}
BREAKDOWNS = {
    "prior_invitations": "Previous invitations (10 = 10+)",
    "age_band": "Age band",
    "healthcare_contacts_12m": "Healthcare contacts in last 12 months",
    "gyn_prevention_24m": "Gynaecologist check-ups in last 24 months (3 = 3+)",
    "other_screening_36m": "Other cancer screenings in last 36 months (4 = 4+)",
    "months_since_last_screening": "Months since last screening",
    "year": "Invitation year",
}


def pct(x: float, digits: int = 1) -> str:
    return f"{x * 100:.{digits}f}%"


def num(x: float) -> str:
    return f"{x:,.0f}"


@st.cache_data
def load(path: str, mtime: float) -> dict:  # mtime: reload when the file is regenerated
    return json.loads(Path(path).read_text(encoding="utf-8"))


def metric(d: dict, name: str, col: str = "model") -> float:
    return next(r[col] for r in d["test_metrics"] if r["metric"] == name)


def rate_chart(rows: list[dict], title: str, color: str = MODEL, horizontal: bool = False):
    df = pd.DataFrame(rows)
    df["group"] = df["group"].astype(str)
    df["err_hi"] = df["ci_high"] - df["attendance"]
    df["err_lo"] = df["attendance"] - df["ci_low"]
    kw = dict(error_y="err_hi", error_y_minus="err_lo") if not horizontal else \
        dict(error_x="err_hi", error_x_minus="err_lo")
    fig = px.bar(df, x="attendance" if horizontal else "group", y="group" if horizontal else "attendance",
                 orientation="h" if horizontal else "v", custom_data=["n"], **kw,
                 color_discrete_sequence=[color])
    fig.update_traces(hovertemplate="%{x}<br>attendance %{y:.1%}<br>n = %{customdata[0]:,}" if not horizontal
                      else "%{y}<br>attendance %{x:.1%}<br>n = %{customdata[0]:,}")
    axis = dict(tickformat=".0%", title="Attendance within 12 months")
    fig.update_layout(title=title, margin=dict(t=50, b=10), height=380,
                      **({"xaxis": axis, "yaxis_title": None} if horizontal else {"yaxis": axis, "xaxis_title": None}))
    return fig


# --------------------------------------------------------------------------------------- pages

def page_overview(d: dict) -> None:
    m = d["meta"]
    st.markdown("### One letter for everyone does not work equally well")
    c = st.columns(5)
    c[0].metric("Invitations 2020–2024", num(m["n_invitations"]))
    c[1].metric("Attendance within 12 months", pct(m["attendance_overall"]))
    t10 = next((r for r in d.get("targeting", []) if abs(r["share"] - 0.1) < 1e-9), None)
    if t10:
        c[2].metric("Lowest-risk 10%: attendance", pct(t10["bottom_attendance_model"], 0),
                    delta=f"rule: {pct(t10['bottom_attendance_rule'], 0)}", delta_color="off",
                    help="Women the model says need only a letter. Rule = number of previous invitations.")
        fewer = 1 - t10["top_wasted_model"] / t10["top_wasted_rule"]
        c[3].metric("Top-10% outreach: needless contacts", num(t10["top_wasted_model"]),
                    delta=f"-{fewer:.0%} vs. rule ({num(t10['top_wasted_rule'])})", delta_color="inverse",
                    help=f"Intensive outreach (e.g. phone) to the {num(t10['n'])} highest-risk women "
                         "in 2024: how many of them would have attended anyway.")
    recent = d["recently_screened_per_year"]
    c[4].metric("Wasted invitations / year", num(sum(r["n"] for r in recent) / len(recent)),
                help="Invitations sent to women screened 0–6 months before the invitation.")

    left, right = st.columns(2)
    left.plotly_chart(rate_chart(d["attendance_by"]["prior_invitations"],
                                 "Attendance drops with every further invitation"), width="stretch")
    dec = pd.DataFrame(d["deciles"])
    fig = px.bar(dec, x="decile", y="attendance", color_discrete_sequence=[MODEL],
                 labels={"decile": "Risk decile (1 = lowest, 10 = highest)", "attendance": "Attendance"})
    fig.update_layout(title="The model separates who needs only a letter from who needs more (test 2024)",
                      yaxis_tickformat=".0%", height=380, margin=dict(t=50, b=10))
    right.plotly_chart(fig, width="stretch")
    st.info("**Approach:** 01 WHO → non-attendance risk · 02 WHY → drivers · 03 WHAT → segments and "
            "interventions · 04 HOW TO VERIFY → A/B experiment. Data: VZP addressed invitations "
            "2020–2024; the model is tested on 2024, which it never saw during training.")


def page_who(d: dict) -> None:
    st.markdown("### 01 WHO — who is most likely not to attend")
    c = st.columns(4)
    dec = pd.DataFrame(d["deciles"])
    c[0].metric("Attendance, lowest-risk decile", pct(dec.iloc[0]["attendance"]))
    c[1].metric("Attendance, highest-risk decile", pct(dec.iloc[-1]["attendance"]))
    c[2].metric("ROC-AUC model", f"{metric(d, 'roc_auc'):.3f}",
                help="Random = 0.5. The rule is already strong because invitation history is VZP's best signal.")
    c[3].metric("ROC-AUC rule 'number of invitations'", f"{metric(d, 'roc_auc', 'baseline'):.3f}")

    if d.get("targeting"):
        tg = pd.DataFrame(d["targeting"])
        tg["Selected"] = tg["share"].map(lambda s: f"{s:.0%}") + " (" + tg["n"].map(num) + " women)"
        st.markdown("#### Model vs. rule in people (test 2024)")
        st.dataframe(pd.DataFrame({
            "Selected share": tg["Selected"],
            "Lowest risk → attendance, model": tg["bottom_attendance_model"],
            "Lowest risk → attendance, rule": tg["bottom_attendance_rule"],
            "Highest risk → needless contacts, model": tg["top_wasted_model"],
            "Highest risk → needless contacts, rule": tg["top_wasted_rule"],
        }), hide_index=True, width="stretch", column_config={
            "Lowest risk → attendance, model": st.column_config.NumberColumn(format="percent"),
            "Lowest risk → attendance, rule": st.column_config.NumberColumn(format="percent")})

    if d.get("ranking_quality"):
        rq = pd.DataFrame(d["ranking_quality"])
        rq["scorer"] = rq["scorer"].map({"random": "Random score", "rule": "Rule: number of invitations",
                                         "model": "Model (LightGBM)"})
        st.markdown("#### Ranking quality vs. a random score")
        st.dataframe(rq.rename(columns={"scorer": "Scorer", "roc_auc": "ROC-AUC",
                                        "ap_attendance": "Average precision (attendance)"}),
                     hide_index=True, width="stretch",
                     column_config={"ROC-AUC": st.column_config.NumberColumn(format="%.3f"),
                                    "Average precision (attendance)": st.column_config.NumberColumn(format="%.3f")})
        st.caption("Average precision is reported for attendance, the 19% minority class: a random score gets "
                   "the attendance rate. On non-attendance (81% of invitations) even a random score gets ~0.81.")

    left, right = st.columns(2)
    roc = go.Figure()
    for key, name, color in (("model", "Model (LightGBM)", MODEL), ("baseline", "Rule: number of invitations", BASE)):
        r = pd.DataFrame(d["roc"][key])
        roc.add_trace(go.Scatter(x=r["fpr"], y=r["tpr"], name=name, line=dict(color=color, width=3)))
    roc.add_trace(go.Scatter(x=[0, 1], y=[0, 1], name="Random", line=dict(color=GREY, dash="dot")))
    roc.update_layout(title="ROC curve — test year 2024", xaxis_title="False positive rate",
                      yaxis_title="Non-attenders captured", height=420, legend=dict(x=0.45, y=0.1))
    left.plotly_chart(roc, width="stretch")

    gain = go.Figure()
    for key, name, color in (("model", "Model", MODEL), ("baseline", "Rule", BASE)):
        g = pd.DataFrame(d["gain"][key])
        gain.add_trace(go.Scatter(x=g["top_share"], y=g["attendance_in_top"], name=name,
                                  mode="lines+markers", line=dict(color=color, width=3)))
    gain.update_layout(title="Attendance among selected women: lower = more precise targeting",
                       xaxis=dict(title="Share of highest-risk women selected", tickformat=".0%"),
                       yaxis=dict(title="Attendance in selected group", tickformat=".0%"), height=420)
    right.plotly_chart(gain, width="stretch")

    with st.expander("Probability calibration and fairness"):
        cal = pd.DataFrame(d["calibration"])
        fig = go.Figure([
            go.Scatter(x=cal["predicted"], y=cal["observed"], mode="markers+lines", name="Model",
                       marker=dict(size=8 + 20 * cal["n"] / cal["n"].max(), color=MODEL)),
            go.Scatter(x=[0, 1], y=[0, 1], name="Perfect calibration", line=dict(color=GREY, dash="dot")),
        ])
        fig.update_layout(xaxis_title="Predicted non-attendance", yaxis_title="Observed non-attendance", height=380)
        st.plotly_chart(fig, width="stretch")
        st.caption(f"Calibration: {d['meta']['calibration']} on the last 6 months of training data. "
                   "The remaining ~1 pp bias matches year-to-year variation in attendance.")
        fair = d["fairness"].get("age_band")
        if fair:
            f = pd.DataFrame(fair).rename(columns={"age_band": "Age band", "roc_auc": "ROC-AUC",
                                                   "non_attendance": "Non-attendance",
                                                   "selection_rate": "Selected into top 20%"})
            st.dataframe(f[["Age band", "n", "Non-attendance", "ROC-AUC", "Selected into top 20%"]],
                         hide_index=True, width="stretch")


def page_why(d: dict) -> None:
    st.markdown("### 02 WHY — what non-attendance is associated with")
    st.caption("Associations learned by the model (SHAP), not causes. Causal effects come from the experiment (04).")
    fi = pd.DataFrame(d["feature_importance"]).head(12)
    fi["label"] = fi["feature"].map(FEATURES).fillna(fi["feature"])
    fi["direction"] = fi["direction"].map({1.0: "higher value → higher risk",
                                           -1.0: "higher value → lower risk"}).fillna("categorical")
    fig = px.bar(fi.iloc[::-1], x="importance", y="label", color="direction", orientation="h",
                 color_discrete_map={"higher value → higher risk": MODEL,
                                     "higher value → lower risk": GOOD, "categorical": BASE})
    fig.update_layout(title="Most important drivers", xaxis_title="Mean |SHAP|", yaxis_title=None,
                      height=460, legend=dict(orientation="h", y=-0.15, title=None))
    st.plotly_chart(fig, width="stretch")

    key = st.selectbox("Attendance by", list(BREAKDOWNS), format_func=BREAKDOWNS.get)
    st.plotly_chart(rate_chart(d["attendance_by"][key], BREAKDOWNS[key]), width="stretch")

    reg = pd.DataFrame(d["attendance_by"]["region"]).sort_values("attendance")
    n = st.slider("VZP territorial offices: show lowest and highest", 5, 20, 10)
    show = pd.concat([reg.head(n), reg.tail(n)])
    st.plotly_chart(rate_chart(show.to_dict("records"), f"VZP territorial offices — {n} lowest and highest "
                               f"(of {len(reg)})", horizontal=True).update_layout(height=40 + 26 * len(show)),
                    width="stretch")
    st.caption("Differences between offices are not adjusted for age or invitation history; "
               "they are not proof of a regional barrier.")


def page_what(d: dict) -> None:
    st.markdown("### 03 WHAT — segments and targeted support")
    seg = pd.DataFrame(d["segments"])
    seg["Segment"] = seg["segment"].map(SEGMENTS).fillna(seg["segment"])
    seg["Intervention"] = seg["intervention"]
    seg["attendance"] = 1 - seg["non_attendance"]
    fig = px.scatter(seg, x="share", y="attendance", size="n", text="Segment", size_max=60,
                     color_discrete_sequence=[MODEL])
    fig.update_traces(textposition="top center")
    fig.update_layout(title="Segments (test 2024): size and attendance",
                      xaxis=dict(title="Share of invitations", tickformat=".0%"),
                      yaxis=dict(title="Attendance within 12 months", tickformat=".0%"), height=460)
    st.plotly_chart(fig, width="stretch")
    table = seg.sort_values("attendance")[["Segment", "n", "share", "attendance", "Intervention"]]
    st.dataframe(table.rename(columns={"share": "Share", "attendance": "Attendance",
                                       "Intervention": "Proposed intervention"}),
                 hide_index=True, width="stretch",
                 column_config={"Share": st.column_config.NumberColumn(format="percent"),
                                "Attendance": st.column_config.NumberColumn(format="percent")})
    st.warning("**High risk ≠ high effect.** Do not automatically give the most expensive support "
               "(phone call, physician) to the highest-risk women, but where the experiment proves it works.")

    if d["segment_response_speed"]:
        sp = pd.DataFrame(d["segment_response_speed"]).melt("segment", var_name="window", value_name="attendance")
        sp["Segment"] = sp["segment"].map(SEGMENTS).fillna(sp["segment"])
        fig = px.line(sp, x="window", y="attendance", color="Segment", markers=True,
                      category_orders={"window": ["3m", "6m", "12m"]})
        fig.update_layout(title="How fast women respond (3 / 6 / 12 months) — when to send a reminder",
                          yaxis_tickformat=".0%", xaxis_title=None, height=400)
        st.plotly_chart(fig, width="stretch")

    st.markdown("#### Quick win: invitations shortly after a screening")
    left, right = st.columns([3, 2])
    since = [r for r in d["attendance_by"]["months_since_last_screening"] if r["group"] != "none_in_5y"]
    left.plotly_chart(rate_chart(since, "Attendance by months since last screening"), width="stretch")
    recent = d["recently_screened_per_year"]
    right.metric("Invitations per year 0–6 months after a screening", num(sum(r["n"] for r in recent) / len(recent)))
    right.markdown(
        "- their attendance is **~2%**\n"
        "- half of them were invited a year earlier and **94% of those attended**, but late (after 11–12 months)\n"
        "- the yearly invitation cycle probably does not see the fresh screening yet "
        "(claims reporting lag) — hypothesis\n"
        "- **proposal:** check claims right before sending / postpone the repeat invitation")

    b = d.get("budget")
    if b:
        with st.expander("Budget illustration (effects are ASSUMPTIONS, not results)"):
            c = st.columns(3)
            c[0].metric("Budget used", f"{num(b['budget_spent_czk'])} CZK")
            c[1].metric("Expected additional screenings", num(b["expected_additional_screenings"]))
            if b["cost_per_additional_screening_czk"]:
                c[2].metric("Cost per additional screening", f"{num(b['cost_per_additional_screening_czk'])} CZK")
            st.caption("The `uplift_pp` values in the config are placeholders; they are replaced by measured "
                       "effects after the A/B test.")


def page_verify(d: dict) -> None:
    st.markdown("### 04 HOW TO VERIFY — randomised experiment")
    st.markdown(
        "- **Control:** standard invitation · **Treatment:** the segment's intervention\n"
        "- **Randomisation unit:** the woman; strata = segment × risk quintile\n"
        "- **Primary metric:** attendance within 12 months (intention-to-treat) · **early signal:** 3 months\n"
        "- Results → uplift model: who the intervention actually helps")

    seg = pd.DataFrame(d["segments"])
    seg["label"] = seg["segment"].map(SEGMENTS).fillna(seg["segment"])
    seg["attendance"] = 1 - seg["non_attendance"]
    st.markdown("#### Sample size calculator")
    c = st.columns(4)
    choice = c[0].selectbox("Segment", seg["label"].tolist(),
                            index=int((seg["segment"] == "repeated_nonresponder").idxmax()))
    row = seg[seg["label"] == choice].iloc[0]
    p0 = c[1].number_input("Baseline attendance", 0.001, 0.999, float(round(row["attendance"], 3)), 0.005,
                           format="%.3f")
    mde = c[2].slider("Expected effect (pp)", 0.5, 10.0, 2.0, 0.5)
    power = c[3].select_slider("Statistical power", [0.7, 0.8, 0.9], 0.8)
    try:
        n = n_per_group(p0, mde / 100, 0.05, power)
        k = st.columns(3)
        k[0].metric("Women per arm", num(n))
        k[1].metric("Total (control + treatment)", num(2 * n))
        k[2].metric("Segment size (2024)", num(row["n"]),
                    delta="enough" if 2 * n <= row["n"] else "one year is not enough",
                    delta_color="normal" if 2 * n <= row["n"] else "inverse")
    except ValueError as e:
        st.error(f"Invalid parameters: {e}")

    design = pd.DataFrame(d["experiment_design"])
    if not design.empty:
        design["Segment"] = design["segment"].map(SEGMENTS).fillna(design["segment"])
        pivot = design.pivot_table(index="Segment", columns="mde_pp", values="n_per_arm", aggfunc="first")
        pivot.columns = [f"effect {c:g} pp" for c in pivot.columns]
        st.markdown("#### Women per arm by expected effect (α = 0.05, power 0.8)")
        st.dataframe(pivot, width="stretch")


# --------------------------------------------------------------------------------------- app

def main() -> None:
    st.set_page_config(page_title="Who skips screening", page_icon="🎗️", layout="wide")
    st.title("Who will not attend mammography screening")
    if not DATA.exists():
        st.error(f"Missing {DATA}. Run `python -m screening train` and `python -m screening export-ui`.")
        st.stop()
    d = load(str(DATA), DATA.stat().st_mtime)
    st.caption(f"Rakathon 2026 · VZP data {d['meta']['years'][0]}–{d['meta']['years'][-1]} · "
               f"aggregates only (groups < {d['meta']['min_cell']} hidden) · "
               f"generated {d['meta']['generated_at']}")
    tabs = st.tabs(["Overview", "01 WHO", "02 WHY", "03 WHAT", "04 HOW TO VERIFY"])
    for tab, page in zip(tabs, (page_overview, page_who, page_why, page_what, page_verify), strict=True):
        with tab:
            page(d)


main()
