"""Demo dashboard (MVP) — Rakathon 2026 / VZP: kdo nedorazí na mamografický screening.

    streamlit run app/dashboard.py

Reads only the aggregate file produced by `python -m screening export-ui`
(reports/ui/data.json): no row-level data, no model, no raw CSV needed at demo time.
UI texts are in Czech (the jury is VZP).
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
    "first_invitation": "První pozvánka",
    "lapsed_regular": "Dříve na screeningu, nyní v prodlení",
    "other": "Ostatní",
    "repeated_nonresponder": "Opakovaně nereagující",
    "care_no_prevention": "V péči, ale bez prevence",
    "low_contact": "Nízký kontakt se zdravotnictvím",
    "recently_screened": "Screening proběhl nedávno",
}
FEATURES = {
    "n_prior_invitations": "Počet předchozích pozvánek",
    "invitation_sequence": "Pozvánky od posledního screeningu",
    "gyn_prevention_24m": "Preventivní prohlídky u gynekologa (24 m)",
    "other_screening_36m": "Jiné screeningy (36 m)",
    "n_healthcare_contacts": "Kontakty se zdravotnictvím (12 m)",
    "dental_prevention_24m": "Preventivní prohlídky u zubaře (24 m)",
    "region": "Územní pracoviště VZP",
    "months_since_last_screening": "Měsíce od posledního screeningu",
    "months_since_last_invitation": "Měsíce od poslední pozvánky",
    "age_band": "Věková skupina",
    "first_invitation": "První pozvánka",
    "recently_screened": "Screening v posledních 6 měsících",
    "has_gyn": "Registrace u gynekologa",
    "has_gp": "Registrace u praktika",
    "insurance_years": "Délka pojištění u VZP",
    "n_preventive_visits": "Preventivní prohlídky GP + GYN (24 m)",
    "n_screenings_5y": "Screeningové výkony za 5 let",
    "never_screened": "Bez screeningu za 5 let",
    "overdue": "Více než 24 měsíců od screeningu",
    "n_registrations": "Počet registrací (GP, GYN)",
    "preventive_share": "Podíl preventivních kontaktů",
    "screenings_per_invitation": "Screeningy na pozvánku",
    "gp_prevention_24m": "Preventivní prohlídky u praktika (24 m)",
    "gyn_registration_band": "Délka registrace u gynekologa",
    "gp_registration_band": "Délka registrace u praktika",
}
BREAKDOWNS = {
    "prior_invitations": "Počet předchozích pozvánek (10 = 10+)",
    "age_band": "Věková skupina",
    "healthcare_contacts_12m": "Kontakty se zdravotnictvím za 12 měsíců",
    "gyn_prevention_24m": "Preventivní prohlídky u gynekologa za 24 měsíců (3 = 3+)",
    "other_screening_36m": "Jiné screeningy za 36 měsíců (4 = 4+)",
    "months_since_last_screening": "Měsíce od posledního screeningu",
    "year": "Rok pozvánky",
}


def pct(x: float, digits: int = 1) -> str:
    return f"{x * 100:.{digits}f} %".replace(".", ",")


def num(x: float) -> str:
    return f"{x:,.0f}".replace(",", " ")


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
    fig.update_traces(hovertemplate="%{x}<br>účast %{y:.1%}<br>n = %{customdata[0]:,}" if not horizontal
                      else "%{y}<br>účast %{x:.1%}<br>n = %{customdata[0]:,}")
    axis = dict(tickformat=".0%", title="Účast do 12 měsíců")
    fig.update_layout(title=title, margin=dict(t=50, b=10), height=380,
                      **({"xaxis": axis, "yaxis_title": None} if horizontal else {"yaxis": axis, "xaxis_title": None}))
    return fig


# --------------------------------------------------------------------------------------- pages

def page_overview(d: dict) -> None:
    m = d["meta"]
    st.markdown("### Stejný dopis pro všechny nefunguje stejně dobře")
    c = st.columns(5)
    c[0].metric("Pozvánek 2020–2024", num(m["n_invitations"]))
    c[1].metric("Klientek", num(m["n_clients"]))
    c[2].metric("Účast do 12 měsíců", pct(m["attendance_overall"]))
    c[3].metric("ROC-AUC modelu (2024)", f"{metric(d, 'roc_auc'):.3f}".replace(".", ","),
                delta=f"+{metric(d, 'roc_auc') - metric(d, 'roc_auc', 'baseline'):.3f} vs. pravidlo".replace(".", ","))
    recent = d["recently_screened_per_year"]
    c[4].metric("Zbytečné pozvánky / rok", num(sum(r["n"] for r in recent) / len(recent)),
                help="Pozvánky klientkám, které absolvovaly screening 0–6 měsíců před pozvánkou.")

    left, right = st.columns(2)
    left.plotly_chart(rate_chart(d["attendance_by"]["prior_invitations"],
                                 "Účast klesá s každou další pozvánkou"), width="stretch")
    dec = pd.DataFrame(d["deciles"])
    fig = px.bar(dec, x="decile", y="attendance", color_discrete_sequence=[MODEL],
                 labels={"decile": "Decil rizika (1 = nejnižší, 10 = nejvyšší)", "attendance": "Účast"})
    fig.update_layout(title="Model odliší, komu stačí dopis a komu ne (test 2024)",
                      yaxis_tickformat=".0%", height=380, margin=dict(t=50, b=10))
    right.plotly_chart(fig, width="stretch")
    st.info("**Postup:** 01 KDO → riziko neúčasti · 02 PROČ → faktory · 03 CO → segmenty a "
            "intervence · 04 JAK OVĚŘIT → A/B experiment. Data: adresné pozvánky VZP 2020–2024, "
            "model testován na roce 2024, který neviděl při trénování.")


def page_kdo(d: dict) -> None:
    st.markdown("### 01 KDO — kdo s nejvyšší pravděpodobností nepřijde")
    c = st.columns(4)
    c[0].metric("ROC-AUC model", f"{metric(d, 'roc_auc'):.3f}".replace(".", ","))
    c[1].metric("ROC-AUC pravidlo „počet pozvánek“", f"{metric(d, 'roc_auc', 'baseline'):.3f}".replace(".", ","))
    dec = pd.DataFrame(d["deciles"])
    c[2].metric("Účast v nejbezpečnějším decilu", pct(dec.iloc[0]["attendance"]))
    c[3].metric("Účast v nejrizikovějším decilu", pct(dec.iloc[-1]["attendance"]))

    left, right = st.columns(2)
    roc = go.Figure()
    for key, name, color in (("model", "Model (LightGBM)", MODEL), ("baseline", "Pravidlo: počet pozvánek", BASE)):
        r = pd.DataFrame(d["roc"][key])
        roc.add_trace(go.Scatter(x=r["fpr"], y=r["tpr"], name=name, line=dict(color=color, width=3)))
    roc.add_trace(go.Scatter(x=[0, 1], y=[0, 1], name="Náhoda", line=dict(color=GREY, dash="dot")))
    roc.update_layout(title="ROC křivka — test 2024", xaxis_title="Podíl falešně označených",
                      yaxis_title="Zachycené neúčastnice", height=420, legend=dict(x=0.45, y=0.1))
    left.plotly_chart(roc, width="stretch")

    gain = go.Figure()
    for key, name, color in (("model", "Model", MODEL), ("baseline", "Pravidlo", BASE)):
        g = pd.DataFrame(d["gain"][key])
        gain.add_trace(go.Scatter(x=g["top_share"], y=g["attendance_in_top"], name=name,
                                  mode="lines+markers", line=dict(color=color, width=3)))
    gain.update_layout(title="Účast mezi vybranými: čím níž, tím přesnější výběr",
                       xaxis=dict(title="Vybraný podíl klientek s nejvyšším rizikem", tickformat=".0%"),
                       yaxis=dict(title="Účast ve vybrané skupině", tickformat=".0%"), height=420)
    right.plotly_chart(gain, width="stretch")

    with st.expander("Kalibrace pravděpodobností a férovost"):
        cal = pd.DataFrame(d["calibration"])
        fig = go.Figure([
            go.Scatter(x=cal["predicted"], y=cal["observed"], mode="markers+lines", name="Model",
                       marker=dict(size=8 + 20 * cal["n"] / cal["n"].max(), color=MODEL)),
            go.Scatter(x=[0, 1], y=[0, 1], name="Ideální kalibrace", line=dict(color=GREY, dash="dot")),
        ])
        fig.update_layout(xaxis_title="Předpovězená neúčast", yaxis_title="Skutečná neúčast", height=380)
        st.plotly_chart(fig, width="stretch")
        st.caption(f"Kalibrace: {d['meta']['calibration']} na posledních 6 měsících trénovacích dat. "
                   "Zbytková odchylka ~1 p. b. odpovídá meziročnímu kolísání účasti.")
        fair = d["fairness"].get("age_band")
        if fair:
            f = pd.DataFrame(fair).rename(columns={"age_band": "Věková skupina", "n": "n", "roc_auc": "ROC-AUC",
                                                   "non_attendance": "Neúčast", "selection_rate": "Vybráno do top 20 %"})
            st.dataframe(f[["Věková skupina", "n", "Neúčast", "ROC-AUC", "Vybráno do top 20 %"]],
                         hide_index=True, width="stretch")


def page_proc(d: dict) -> None:
    st.markdown("### 02 PROČ — co s neúčastí souvisí")
    st.caption("Souvislosti naučené modelem (SHAP), ne příčiny. Kauzální efekt ukáže až experiment (04).")
    fi = pd.DataFrame(d["feature_importance"]).head(12)
    fi["label"] = fi["feature"].map(FEATURES).fillna(fi["feature"])
    fi["směr"] = fi["direction"].map({1.0: "vyšší hodnota → vyšší riziko",
                                      -1.0: "vyšší hodnota → nižší riziko"}).fillna("kategorie")
    fig = px.bar(fi.iloc[::-1], x="importance", y="label", color="směr", orientation="h",
                 color_discrete_map={"vyšší hodnota → vyšší riziko": MODEL,
                                     "vyšší hodnota → nižší riziko": GOOD, "kategorie": BASE})
    fig.update_layout(title="Nejdůležitější faktory", xaxis_title="Průměrný |SHAP|", yaxis_title=None,
                      height=460, legend=dict(orientation="h", y=-0.15, title=None))
    st.plotly_chart(fig, width="stretch")

    key = st.selectbox("Účast podle", list(BREAKDOWNS), format_func=BREAKDOWNS.get)
    st.plotly_chart(rate_chart(d["attendance_by"][key], BREAKDOWNS[key]), width="stretch")

    reg = pd.DataFrame(d["attendance_by"]["region"]).sort_values("attendance")
    n = st.slider("Územní pracoviště: zobrazit nejnižší a nejvyšší", 5, 20, 10)
    show = pd.concat([reg.head(n), reg.tail(n)])
    st.plotly_chart(rate_chart(show.to_dict("records"), f"Územní pracoviště VZP — {n} nejnižších a nejvyšších "
                               f"(z {len(reg)})", horizontal=True).update_layout(height=40 + 26 * len(show)),
                    width="stretch")
    st.caption("Rozdíly mezi pracovišti nejsou očištěny o věk ani historii pozvánek; "
               "nejsou důkazem regionální bariéry.")


def page_co(d: dict) -> None:
    st.markdown("### 03 CO — segmenty a cílená podpora")
    seg = pd.DataFrame(d["segments"])
    seg["Segment"] = seg["segment"].map(SEGMENTS).fillna(seg["segment"])
    seg["attendance"] = 1 - seg["non_attendance"]
    fig = px.scatter(seg, x="share", y="attendance", size="n", text="Segment", size_max=60,
                     color_discrete_sequence=[MODEL])
    fig.update_traces(textposition="top center")
    fig.update_layout(title="Segmenty (test 2024): velikost a účast",
                      xaxis=dict(title="Podíl pozvánek", tickformat=".0%"),
                      yaxis=dict(title="Účast do 12 měsíců", tickformat=".0%"), height=460)
    st.plotly_chart(fig, width="stretch")
    table = seg.sort_values("attendance")[["Segment", "n", "share", "attendance", "intervention"]]
    st.dataframe(table.rename(columns={"share": "Podíl", "attendance": "Účast", "intervention": "Navržená intervence"}),
                 hide_index=True, width="stretch",
                 column_config={"Podíl": st.column_config.NumberColumn(format="percent"),
                                "Účast": st.column_config.NumberColumn(format="percent")})
    st.warning("**Vysoké riziko ≠ vysoký efekt.** Nejdražší podporu (telefon, lékař) nedávat automaticky "
               "těm s nejvyšším rizikem, ale tam, kde ji experiment prokáže.")

    if d["segment_response_speed"]:
        sp = pd.DataFrame(d["segment_response_speed"]).melt("segment", var_name="okno", value_name="účast")
        sp["Segment"] = sp["segment"].map(SEGMENTS).fillna(sp["segment"])
        fig = px.line(sp, x="okno", y="účast", color="Segment", markers=True,
                      category_orders={"okno": ["3m", "6m", "12m"]})
        fig.update_layout(title="Jak rychle klientky reagují (3 / 6 / 12 měsíců) — kdy poslat připomínku",
                          yaxis_tickformat=".0%", xaxis_title=None, height=400)
        st.plotly_chart(fig, width="stretch")

    st.markdown("#### Rychlá výhra: pozvánky krátce po screeningu")
    left, right = st.columns([3, 2])
    since = [r for r in d["attendance_by"]["months_since_last_screening"] if r["group"] != "none_in_5y"]
    left.plotly_chart(rate_chart(since, "Účast podle měsíců od posledního screeningu"), width="stretch")
    recent = d["recently_screened_per_year"]
    right.metric("Pozvánek ročně 0–6 měsíců po screeningu", num(sum(r["n"] for r in recent) / len(recent)))
    right.markdown(
        "- účast těchto klientek je **~2 %**\n"
        "- polovina z nich dostala pozvánku před rokem a **94 % z nich na ni přišlo**, ale pozdě (po 11–12 měsících)\n"
        "- roční cyklus pozvánek pravděpodobně nevidí čerstvý výkon (zpoždění vykazování) — hypotéza\n"
        "- **návrh:** kontrola výkonů těsně před odesláním / posun opakované pozvánky")

    b = d.get("budget")
    if b:
        with st.expander("Ilustrace rozpočtu (efekty jsou PŘEDPOKLADY, ne výsledky)"):
            c = st.columns(3)
            c[0].metric("Využitý rozpočet", f"{num(b['budget_spent_czk'])} Kč")
            c[1].metric("Očekávané screeningy navíc", num(b["expected_additional_screenings"]))
            if b["cost_per_additional_screening_czk"]:
                c[2].metric("Cena za screening navíc", f"{num(b['cost_per_additional_screening_czk'])} Kč")
            st.caption("Hodnoty `uplift_pp` v konfiguraci jsou zástupné; po A/B testu se nahradí naměřenými.")


def page_overit(d: dict) -> None:
    st.markdown("### 04 JAK OVĚŘIT — randomizovaný experiment")
    st.markdown(
        "- **Kontrola:** standardní pozvánka · **Léčba:** intervence segmentu\n"
        "- **Randomizace:** klientka; strata = segment × kvintil rizika\n"
        "- **Primární metrika:** účast do 12 měsíců (ITT) · **časný signál:** 3 měsíce\n"
        "- Výsledky → uplift model: komu intervence skutečně pomáhá")

    seg = pd.DataFrame(d["segments"])
    seg["label"] = seg["segment"].map(SEGMENTS).fillna(seg["segment"])
    seg["attendance"] = 1 - seg["non_attendance"]
    st.markdown("#### Kalkulačka velikosti vzorku")
    c = st.columns(4)
    choice = c[0].selectbox("Segment", seg["label"].tolist(),
                            index=int((seg["segment"] == "repeated_nonresponder").idxmax()))
    row = seg[seg["label"] == choice].iloc[0]
    p0 = c[1].number_input("Výchozí účast", 0.001, 0.999, float(round(row["attendance"], 3)), 0.005, format="%.3f")
    mde = c[2].slider("Očekávaný efekt (p. b.)", 0.5, 10.0, 2.0, 0.5)
    power = c[3].select_slider("Síla testu", [0.7, 0.8, 0.9], 0.8)
    try:
        n = n_per_group(p0, mde / 100, 0.05, power)
        k = st.columns(3)
        k[0].metric("Klientek na skupinu", num(n))
        k[1].metric("Celkem (kontrola + léčba)", num(2 * n))
        k[2].metric("Velikost segmentu (rok 2024)", num(row["n"]),
                    delta="dostatečný" if 2 * n <= row["n"] else "nestačí jeden rok",
                    delta_color="normal" if 2 * n <= row["n"] else "inverse")
    except ValueError as e:
        st.error(f"Neplatné parametry: {e}")

    design = pd.DataFrame(d["experiment_design"])
    if not design.empty:
        design["Segment"] = design["segment"].map(SEGMENTS).fillna(design["segment"])
        pivot = design.pivot_table(index="Segment", columns="mde_pp", values="n_per_arm", aggfunc="first")
        pivot.columns = [f"efekt {c:g} p. b." for c in pivot.columns]
        st.markdown("#### Klientek na skupinu podle očekávaného efektu (α = 0,05, síla 0,8)")
        st.dataframe(pivot, width="stretch")


# --------------------------------------------------------------------------------------- app

def main() -> None:
    st.set_page_config(page_title="Kdo nedorazí na screening", page_icon="🎗️", layout="wide")
    st.title("Kdo nedorazí na mamografický screening")
    if not DATA.exists():
        st.error(f"Chybí {DATA}. Spusťte `python -m screening train` a `python -m screening export-ui`.")
        st.stop()
    d = load(str(DATA), DATA.stat().st_mtime)
    st.caption(f"Rakathon 2026 · data VZP {d['meta']['years'][0]}–{d['meta']['years'][-1]} · "
               f"pouze agregované údaje (skupiny < {d['meta']['min_cell']} skryty) · "
               f"vygenerováno {d['meta']['generated_at']}")
    tabs = st.tabs(["Přehled", "01 KDO", "02 PROČ", "03 CO", "04 JAK OVĚŘIT"])
    for tab, page in zip(tabs, (page_overview, page_kdo, page_proc, page_co, page_overit)):
        with tab:
            page(d)


main()
