"""Build the English pitch deck from aggregate JSON and generated PNG figures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

RED = RGBColor(0xC8, 0x10, 0x2E)
GREY = RGBColor(0x8C, 0x8C, 0x8C)
DARK = RGBColor(0x20, 0x20, 0x20)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)


def _load(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("the UI export must be a JSON object")
    return payload


def _pct(value, digits=0) -> str:
    return "[TODO]" if value is None else f"{value:.{digits}%}"


def _num(value) -> str:
    return "[TODO]" if value is None else f"{value:,.0f}"


def _find(rows: list[dict], key: str, value):
    return next((row for row in rows if row.get(key) == value), None)


def _metric(payload: dict, name: str, column: str = "model"):
    row = _find(payload.get("test_metrics", []), "metric", name)
    return None if row is None else row.get(column)


def _facts(payload: dict) -> dict:
    meta = payload.get("meta", {})
    prior = payload.get("attendance_by", {}).get("prior_invitations", [])
    deciles = payload.get("deciles", [])
    t10 = next((row for row in payload.get("targeting", [])
                if abs(row.get("share", 0) - 0.1) < 1e-9), None)
    recent = payload.get("recently_screened_per_year", [])
    recent_n = sum(row["n"] for row in recent) / len(recent) if recent else None
    recent_attendance = (sum(row["attendance"] * row["n"] for row in recent)
                         / sum(row["n"] for row in recent)) if recent else None
    wasted_reduction = (1 - t10["top_wasted_model"] / t10["top_wasted_rule"]
                        if t10 and t10.get("top_wasted_rule") else None)
    return {
        "invitations": meta.get("n_invitations"),
        "clients": meta.get("n_clients"),
        "years": meta.get("years", []),
        "overall": meta.get("attendance_overall"),
        "test_year": meta.get("test_year"),
        "test_n": meta.get("n_test"),
        "auc": _metric(payload, "roc_auc"),
        "baseline_auc": _metric(payload, "roc_auc", "baseline"),
        "first_prior": prior[0].get("attendance") if prior else None,
        "last_prior": prior[-1].get("attendance") if prior else None,
        "low_decile": deciles[0].get("attendance") if deciles else None,
        "high_decile": deciles[-1].get("attendance") if deciles else None,
        "target_n": t10.get("n") if t10 else None,
        "letter_attendance_model": t10.get("bottom_attendance_model") if t10 else None,
        "letter_attendance_rule": t10.get("bottom_attendance_rule") if t10 else None,
        "wasted_model": t10.get("top_wasted_model") if t10 else None,
        "wasted_rule": t10.get("top_wasted_rule") if t10 else None,
        "wasted_reduction": wasted_reduction,
        "recent_n": recent_n,
        "recent_attendance": recent_attendance,
    }


def _set_background(slide) -> None:
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = WHITE


def _add_title(slide, title: str, number: int) -> None:
    box = slide.shapes.add_textbox(Inches(0.65), Inches(0.35), Inches(11.8), Inches(0.8))
    paragraph = box.text_frame.paragraphs[0]
    paragraph.text = title
    paragraph.font.name = "Aptos Display"
    paragraph.font.size = Pt(27)
    paragraph.font.bold = True
    paragraph.font.color.rgb = DARK
    marker = slide.shapes.add_textbox(Inches(12.3), Inches(0.42), Inches(0.45), Inches(0.35))
    p = marker.text_frame.paragraphs[0]
    p.text = f"{number:02d}"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = RED
    p.alignment = PP_ALIGN.RIGHT


def _add_bullets(slide, bullets: list[str], *, top=1.35, height=5.2, width=5.0) -> None:
    frame = slide.shapes.add_textbox(Inches(0.75), Inches(top), Inches(width), Inches(height)).text_frame
    frame.word_wrap = True
    frame.clear()
    for index, bullet in enumerate(bullets):
        p = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        p.text = bullet
        p.level = 0
        p.font.name = "Aptos"
        p.font.size = Pt(20)
        p.font.color.rgb = DARK
        p.space_after = Pt(18)
        p.text = f"•  {p.text}"


def _add_picture(slide, figures: Path, name: str) -> None:
    path = figures / f"{name}.png"
    if path.exists():
        slide.shapes.add_picture(str(path), Inches(5.75), Inches(1.25),
                                 width=Inches(7.0), height=Inches(3.94))
    else:
        box = slide.shapes.add_textbox(Inches(5.75), Inches(2.5), Inches(7), Inches(1))
        p = box.text_frame.paragraphs[0]
        p.text = f"[TODO: missing reports/figures/{name}.png]"
        p.font.size = Pt(20)
        p.font.color.rgb = GREY
        p.alignment = PP_ALIGN.CENTER


def _add_footer(slide, source: str) -> None:
    line = slide.shapes.add_shape(1, Inches(0.65), Inches(7.0), Inches(12.1), Inches(0.015))
    line.fill.solid()
    line.fill.fore_color.rgb = RED
    line.line.fill.background()
    box = slide.shapes.add_textbox(Inches(0.7), Inches(7.05), Inches(12), Inches(0.25))
    p = box.text_frame.paragraphs[0]
    p.text = f"Source: {source}"
    p.font.name = "Aptos"
    p.font.size = Pt(9)
    p.font.color.rgb = GREY


def _add_notes(slide, notes: str) -> None:
    try:
        slide.notes_slide.notes_text_frame.text = notes
    except (AttributeError, NotImplementedError):
        pass


def _content_slide(prs, number: int, title: str, bullets: list[str], figure: str,
                   source: str, notes: str, figures: Path) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_background(slide)
    _add_title(slide, title, number)
    _add_bullets(slide, bullets)
    _add_picture(slide, figures, figure)
    _add_footer(slide, source)
    _add_notes(slide, notes)


def build_deck(payload: dict, figures: Path, output: Path) -> Path:
    """Create a 12-slide, 16:9 presentation with values sourced from the payload."""
    facts = _facts(payload)
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_background(slide)
    accent = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(0.22), Inches(7.5))
    accent.fill.solid()
    accent.fill.fore_color.rgb = RED
    accent.line.fill.background()
    title = slide.shapes.add_textbox(Inches(1), Inches(1.35), Inches(11.3), Inches(2.1))
    p = title.text_frame.paragraphs[0]
    p.text = "Who will not attend\nmammography screening?"
    p.font.name = "Aptos Display"
    p.font.size = Pt(38)
    p.font.bold = True
    p.font.color.rgb = DARK
    subtitle = slide.shapes.add_textbox(Inches(1), Inches(4.0), Inches(10.5), Inches(1.3))
    sp = subtitle.text_frame.paragraphs[0]
    years = facts["years"]
    period = f"{min(years)}–{max(years)}" if years else "[TODO]"
    sp.text = (f"Risk ranking, actionable segments and an honest A/B plan\n"
               f"{_num(facts['invitations'])} invitations · {_num(facts['clients'])} women · {period}")
    sp.font.name = "Aptos"
    sp.font.size = Pt(22)
    sp.font.color.rgb = GREY
    _add_footer(slide, "reports/ui/data.json::meta")
    _add_notes(slide, "Open with the decision: use the same invitation budget more intelligently. "
               "We rank non-attendance risk, explain associations, define operational segments, "
               "and propose an experiment before claiming intervention effects.")

    _content_slide(prs, 2, "One letter for everyone meets very different behaviour", [
        f"Overall 12-month attendance is {_pct(facts['overall'], 1)}.",
        f"Attendance falls from {_pct(facts['first_prior'])} to {_pct(facts['last_prior'])} as invitations repeat.",
        "Invitation history is a strong signal, but it cannot tell us which support works.",
    ], "attendance_by_invitations", "data.json::meta.attendance_overall; "
       "attendance_by.prior_invitations", "The population is not homogeneous. Women on an early invitation "
       "behave very differently from repeated non-responders. This makes one universal contact strategy inefficient.", figures)

    _content_slide(prs, 3, "A data check can prevent about 7,300 mistimed invitations a year", [
        f"About {_num(facts['recent_n'])} annual invitations follow a screen recorded in the previous 0–6 months.",
        f"Only {_pct(facts['recent_attendance'], 1)} attend again within 12 months.",
        "Check fresh claims immediately before mailing; billing delay is a hypothesis to validate.",
    ], "months_since_screening", "data.json::recently_screened_per_year; "
       "attendance_by.months_since_last_screening", "This is the quickest operational opportunity. The pattern "
       "is descriptive: a reporting delay is plausible, but must be confirmed with the invitation process owner.", figures)

    _content_slide(prs, 4, "The 2024 holdout simulates the next invitation wave", [
        f"Training uses years before {facts['test_year'] or '[TODO]'}; the untouched test is {facts['test_year'] or '[TODO]'}.",
        f"The holdout contains {_num(facts['test_n'])} invitations.",
        "3- and 6-month outcomes are excluded from features because they occur after invitation.",
        "Repeated women stay realistic across years; client IDs are never model features.",
    ], "risk_deciles", "data.json::meta.test_year, meta.n_test, deciles; "
       "src/screening/data/schema.py", "A random split would leak future patterns into training. The temporal "
       "holdout asks the operational question: how would a model trained on history work on the next annual wave?", figures)

    _content_slide(prs, 5, "The model finds who needs only a letter—and where calls are wasted", [
        f"Model ROC-AUC: {facts['auc']:.3f}" if facts["auc"] is not None else "Model ROC-AUC: [TODO].",
        f"Rule ROC-AUC: {facts['baseline_auc']:.3f}" if facts["baseline_auc"] is not None else "Rule ROC-AUC: [TODO].",
        f"Lowest-risk 10% attendance: {_pct(facts['letter_attendance_model'])} model vs {_pct(facts['letter_attendance_rule'])} rule.",
        (f"Top-risk outreach: {_num(facts['wasted_model'])} vs {_num(facts['wasted_rule'])} needless contacts "
         f"({_pct(facts['wasted_reduction'])} fewer)."),
    ], "model_vs_rule", "data.json::test_metrics[roc_auc]; targeting[share=0.1]", "AUC confirms ranking quality, "
       "but the operational translation matters more. The low-risk group can receive a standard letter, while intensive "
       "outreach is reserved with fewer needless contacts.", figures)

    _content_slide(prs, 6, "The model learns behaviour and care history—not causes", [
        "SHAP ranks which recorded variables move model predictions most.",
        "Direction shows association with risk, not a causal intervention target.",
        "Only randomized outcomes can establish what changes attendance.",
    ], "top10_shap", "data.json::feature_importance", "Previous invitations, screening and prevention history "
       "summarize behaviour before the invitation. SHAP explains the prediction, but cannot say that changing a feature "
       "will change attendance.", figures)

    _content_slide(prs, 7, "Operational segments turn scores into testable hypotheses", [
        "Segments combine recognizable pre-invitation patterns with risk.",
        "Their sizes determine which pilots are feasible within one annual wave.",
        "Regional differences remain descriptive until access data are added.",
    ], "segment_map", "data.json::segments", "A score alone does not specify an action. These segments give teams "
       "a practical way to define eligibility and tailor a pilot, while keeping each intervention hypothesis testable.", figures)

    _content_slide(prs, 8, "Match support to the barrier, then measure its effect", [
        "Recent screen → postpone; lapsed regular → booking reminder.",
        "Care without prevention → involve GP or gynaecologist.",
        "Repeated non-response → different channel and navigation.",
        "High risk does not imply high intervention effect.",
    ], "response_timing_by_segment", "data.json::interventions; segment_response_speed", "The intervention map is a "
       "set of hypotheses. Timing helps decide when a reminder could still matter. We do not automatically spend the most "
       "on the highest-risk group.", figures)

    _content_slide(prs, 9, "Randomization tells us who the intervention actually helps", [
        "Randomize women within segment × risk-quintile strata.",
        "Compare standard invitation with one segment-specific treatment.",
        "Primary outcome: 12-month attendance, intention-to-treat; 3 months is an early signal.",
        "Measured effects later train an uplift model.",
    ], "ab_group_sizes", "data.json::experiment_design; docs/experiment-design.md", "The experiment preserves a "
       "clean control group and analyzes everyone as assigned. Sample sizes depend on baseline attendance and the minimum "
       "effect worth detecting, so each segment needs its own feasibility check.", figures)

    _content_slide(prs, 10, "Guardrails keep the ranking useful and fair", [
        "Monitor discrimination, calibration and selection rates by age and region.",
        "Recalibrate when the annual attendance baseline shifts.",
        "Territory is an administrative office, not a measured distance-to-care barrier.",
        "Only aggregate, small-cell-suppressed data enter the demo.",
    ], "risk_deciles", "data.json::calibration, fairness, meta.min_cell; "
       "docs/segments-real-data.md", "Performance can differ across groups even when the overall AUC is strong. "
       "We therefore audit error and selection patterns, and we avoid causal claims about regional access without external data.", figures)

    _content_slide(prs, 11, "Start with the quick win, then learn in controlled waves", [
        "1. Add a fresh-claims check before the next mailing wave.",
        "2. Score eligible women immediately before each wave.",
        "3. Pilot one intervention per priority segment with fixed eligibility and outcomes.",
        "4. Scale proven effects; retrain and recalibrate on new waves.",
    ], "segment_map", "data.json::segments; docs/experiment-design.md", "The rollout separates a low-risk process "
       "fix from causal experimentation. Each wave creates evidence for the next decision without freezing today’s assumptions "
       "into a permanent policy.", figures)

    _content_slide(prs, 12, "Use risk to focus attention—and experiments to prove impact", [
        f"{_num(facts['invitations'])} invitations reveal large, actionable differences.",
        f"Attendance spans {_pct(facts['low_decile'], 1)} to {_pct(facts['high_decile'], 1)} across model deciles.",
        "The next decision is a controlled pilot, not an untested national rollout.",
        "Questions?",
    ], "risk_deciles", "data.json::meta.n_invitations; deciles", "Close on the decision boundary: the model "
       "prioritizes, while the A/B test proves which action works. Invite questions on leakage, fairness, implementation, "
       "and experiment design.", figures)

    output.parent.mkdir(parents=True, exist_ok=True)
    prs.save(output)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("reports/ui/data.json"))
    parser.add_argument("--figures", type=Path, default=Path("reports/figures"))
    parser.add_argument("--output", type=Path, default=Path("reports/pitch/deck.pptx"))
    args = parser.parse_args()
    output = build_deck(_load(args.input), args.figures, args.output)
    print(output)


if __name__ == "__main__":
    main()
