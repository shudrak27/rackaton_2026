import React, { useMemo, useState } from "react";
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, ErrorBar, Legend, Line, LineChart,
  ReferenceLine, Tooltip, XAxis, YAxis,
} from "recharts";
import { BREAKDOWNS, FEATURES, SEGMENTS, num, pct } from "./labels.js";
import { nPerGroup } from "./power.js";
import { Badge, Chart, ChartTooltip, Icon, Kpi, LegendItem, Notice, Panel, Table } from "./components.jsx";
import { InterventionActions } from "./intervention-info.jsx";
import { PLAYBOOKS, PILOT_SEGMENTS } from "./interventions.js";

const INDIGO = "#626cf0", TEAL = "#55bca8", CORAL = "#ec858b", GREY = "#b4bbcf";
const SEGMENT_COLORS = {
  repeated_nonresponder: INDIGO, care_no_prevention: TEAL, first_invitation: CORAL,
  low_contact: "#e7b85c", lapsed_regular: "#9f8bdb", other: "#7ab6da", recently_screened: GREY,
};
const segmentColor = (id) => SEGMENT_COLORS[id] || GREY;
const AXIS = { axisLine: false, tickLine: false, tick: { fontSize: 11 }, tickMargin: 10 };
const GRID = { stroke: "#eef0f6", strokeDasharray: "4 4", vertical: false };
const pctTick = (v) => `${Math.round(v * 100)}%`;
export const metric = (d, name, col = "model") => d.test_metrics.find((r) => r.metric === name)?.[col];
const fixed = (v, digits = 3) => v == null ? "–" : v.toFixed(digits);
const period = (d) => `${d.meta.years[0]}–${d.meta.years.at(-1)}`;
const recentAverage = (d) => d.recently_screened_per_year.length
  ? d.recently_screened_per_year.reduce((s, r) => s + r.n, 0) / d.recently_screened_per_year.length : null;
const segmentRows = (d) => d.segments.map((r) => ({ ...r, attendance: 1 - r.non_attendance, label: SEGMENTS[r.segment] || r.segment }));

// Short axis labels: long ones make Recharts hide neighbouring ticks.
const GROUP_LABELS = { none_in_5y: "No screen in 5y", "61+ (window edge)": "61+*" };
const CAPPED_GROUP_LABELS = {
  prior_invitations: { "10": "10+" },
  gyn_prevention_24m: { "3": "3+" },
  other_screening_36m: { "4": "4+" },
};
// Groups that are "no information" rather than a value range: drawn in grey.
const NO_DATA_GROUPS = new Set(["none_in_5y"]);
const BREAKDOWN_NOTES = {
  months_since_last_screening: "Grey: no screening recorded in the 5-year history window (82% of invitations, no date to count from). " +
    "* 61+: edge of that window in the VZP data (193 invitations).",
  prior_invitations: "0 = first invitation; 10+ = ten or more previous invitations.",
};

export function RateBars({ rows = [], color = INDIGO, horizontal = false, groupLabels = {}, width, height }) {
  const data = rows.map((r) => ({ ...r, key: String(r.group), group: groupLabels[r.group] ?? GROUP_LABELS[r.group] ?? String(r.group),
    err: [Math.max(0, r.attendance - r.ci_low), Math.max(0, r.ci_high - r.attendance)] }));
  return <BarChart width={width} height={height} data={data} layout={horizontal ? "vertical" : "horizontal"}
    margin={{ top: 8, right: 18, left: horizontal ? 20 : -12, bottom: 8 }} barCategoryGap="30%">
    <CartesianGrid {...GRID} vertical={horizontal} horizontal={!horizontal} />
    {horizontal ? <><XAxis {...AXIS} type="number" tickFormatter={pctTick} /><YAxis {...AXIS} type="category" dataKey="group" width={170} /></>
      : <><XAxis {...AXIS} dataKey="group" interval={0} /><YAxis {...AXIS} tickFormatter={pctTick} width={58} /></>}
    <Tooltip cursor={{ fill: "#f4f5ff" }} content={<ChartTooltip showCount />} />
    <Bar dataKey="attendance" name="Attendance" fill={color} radius={horizontal ? [0, 3, 3, 0] : [4, 4, 0, 0]} maxBarSize={42} isAnimationActive={false}>
      {data.map((r) => <Cell key={r.key} fill={NO_DATA_GROUPS.has(r.key) ? GREY : color} />)}
      <ErrorBar dataKey="err" width={3} stroke="#a6adc4" direction={horizontal ? "x" : "y"} />
    </Bar>
  </BarChart>;
}

function DecileChart({ d, width, height }) {
  return <BarChart width={width} height={height} data={d.deciles} margin={{ top: 8, right: 12, left: -12, bottom: 8 }} barCategoryGap="25%">
    <CartesianGrid {...GRID} /><XAxis {...AXIS} dataKey="decile" /><YAxis {...AXIS} tickFormatter={pctTick} width={58} />
    <Tooltip cursor={{ fill: "#f4f5ff" }} content={<ChartTooltip labelFormat={(v) => `Risk decile ${v}`} />} />
    <Bar dataKey="attendance" name="Observed attendance" radius={[4, 4, 0, 0]} maxBarSize={40} isAnimationActive={false}>
      {d.deciles.map((r) => <Cell key={r.decile} fill={r.decile <= 2 ? TEAL : INDIGO} />)}
    </Bar>
  </BarChart>;
}

function SegmentTable({ d, compact = false }) {
  const rows = segmentRows(d).sort((a, b) => b.n - a.n);
  return <Table label="Screening segments">
    <thead><tr><th>Segment</th><th className="n">Women</th><th>Share</th><th className="n">Attendance</th><th>{compact ? "Outreach approach" : "Proposed intervention"}</th></tr></thead>
    <tbody>{rows.map((r) => <tr key={r.segment}>
      <td><strong>{r.label}</strong></td>
      <td className="n">{num(r.n)}</td><td><div className="table-progress"><div className="progress-track"><i className="progress-fill" style={{ width: `${r.share * 100}%` }} /></div>{pct(r.share)}</div></td>
      <td className="n"><Badge tone={r.attendance >= d.meta.attendance_overall ? "teal" : "neutral"}>{pct(r.attendance)}</Badge></td>
      <td className="intervention-cell">{PLAYBOOKS[r.segment]?.title || r.intervention}</td>
    </tr>)}</tbody>
  </Table>;
}

export function Overview({ d, navigate }) {
  const t10 = d.targeting?.find((r) => Math.abs(r.share - .1) < 1e-9);
  const reduction = t10?.top_wasted_rule ? 1 - t10.top_wasted_model / t10.top_wasted_rule : null;
  const first = d.deciles[0], last = d.deciles.at(-1);
  return <>
    <div className="kpis">
      <Kpi label="Unique women" value={num(d.meta.n_clients)} detail={`${num(d.meta.n_invitations)} invitations · ${period(d)}`} tone="amber" icon="people" />
      <Kpi label="Overall attendance rate" value={pct(d.meta.attendance_overall)} detail="within 12 months of invitation" tone="coral" icon="calendar" />
      <Kpi label="Lowest-risk 10% · attendance" value={pct(t10?.bottom_attendance_model, 0)} detail={`Baseline: ${pct(t10?.bottom_attendance_rule, 0)} · observed in ${d.meta.test_year}`} tone="teal" icon="people" highlight />
      <Kpi label="Model ROC-AUC" value={fixed(metric(d, "roc_auc"))} detail={`Baseline: ${fixed(metric(d, "roc_auc", "baseline"))} · random: 0.500`} icon="chart" />
    </div>
    <div className="overview-grid">
      <Panel title="A clearer picture of risk" subtitle="Attendance by model risk decile" className="risk-highlight" action={<Badge>TEST {d.meta.test_year}</Badge>}>
        <div className="risk-range"><div><strong>{pct(first?.attendance)}</strong><small>Lowest-risk decile</small></div><Icon name="arrow" /><div><strong>{pct(last?.attendance)}</strong><small>Highest-risk decile</small></div></div>
        <Chart height={122} label="Attendance decreases across model risk deciles">
          <AreaChart data={d.deciles} margin={{ top: 12, right: 0, left: 0, bottom: 0 }}>
            <defs><linearGradient id="riskFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={INDIGO} stopOpacity={.22} /><stop offset="100%" stopColor={INDIGO} stopOpacity={0} /></linearGradient></defs>
            <Tooltip content={<ChartTooltip labelFormat={(v) => `Risk decile ${d.deciles[v]?.decile ?? v}`} />} />
            <Area type="monotone" dataKey="attendance" name="Observed attendance" stroke={INDIGO} strokeWidth={2} fill="url(#riskFill)" isAnimationActive={false} />
          </AreaChart>
        </Chart>
      </Panel>
      <Panel title="Outreach targeting" subtitle="Highest-risk 10% selected for extra contact" action={<Icon name="target" size={18} />}>
        <div className="precision-body"><div className="precision-summary"><div className="precision-value">{pct(reduction, 0)} fewer</div>
          <p className="precision-description">observed attenders in the contact list; outreach effect not measured</p></div>
          {[{ name: "Model", value: t10?.top_wasted_model, color: INDIGO }, { name: "Baseline", value: t10?.top_wasted_rule, color: GREY }].map((r) => <div className="progress-row" key={r.name}>
            <div className="progress-label"><span>{r.name}</span><strong>{num(r.value)}</strong></div>
            <div className="progress-track"><i className="progress-fill" style={{ width: `${t10?.top_wasted_rule ? 100 * r.value / t10.top_wasted_rule : 0}%`, background: r.color }} /></div>
          </div>)}
        </div>
      </Panel>
    </div>
    <div className="grid2">
      <Panel title="Attendance by invitation history" subtitle="Observed attendance within 12 months" action={<Badge tone="neutral">{period(d)}</Badge>}>
        <Chart label="Attendance by previous invitation count"><RateBars rows={d.attendance_by.prior_invitations} groupLabels={CAPPED_GROUP_LABELS.prior_invitations} /></Chart>
        <div className="chart-caption">Previous invitations · 0 = first invitation, 10+ = ten or more</div>
      </Panel>
      <Panel title="Attendance by risk decile" subtitle="Predicted risk groups, actual outcomes" action={<Badge tone="teal">TEST {d.meta.test_year}</Badge>}>
        <Chart label="Actual attendance in each model risk decile"><DecileChart d={d} /></Chart>
        <div className="chart-caption">Risk decile · 1 = lowest risk of non-attendance, 10 = highest</div>
      </Panel>
    </div>
    <Panel title="Your audience at a glance" subtitle={`Operational segments · ${num(d.meta.n_test)} test-year invitations`}
      action={<button className="text-button" onClick={() => navigate("segments")}>Explore segments <Icon name="arrow" size={15} /></button>}>
      <SegmentTable d={d} compact />
    </Panel>
    <div className="insight-strip"><span className="insight-icon"><Icon name="clock" /></span>
      <div><h3>An opportunity to improve invitation timing</h3><p>About {num(recentAverage(d))} invitations per year follow a screening in the previous six months.</p></div>
      <button className="text-button" onClick={() => navigate("segments")}>Review the opportunity <Icon name="arrow" size={15} /></button>
    </div>
  </>;
}

export function Who({ d }) {
  const rq = Object.fromEntries((d.ranking_quality || []).map((r) => [r.scorer, r]));
  const t10 = d.targeting?.find((r) => Math.abs(r.share - .1) < 1e-9);
  return <>
    <div className="kpis">
      <Kpi label="Model ROC-AUC" value={fixed(metric(d, "roc_auc"))} detail={`Baseline: ${fixed(metric(d, "roc_auc", "baseline"))}`} icon="chart" />
      <Kpi label="Average precision · non-attendance" value={fixed(metric(d, "average_precision"))} detail={`Baseline: ${fixed(metric(d, "average_precision", "baseline"))} · random: ${fixed(rq.random?.ap_attendance == null ? null : 1 - rq.random.ap_attendance)}`} tone="amber" icon="target" />
      <Kpi label="Lowest-risk decile" value={pct(d.deciles[0]?.attendance)} detail="Observed attendance within 12 months" tone="teal" icon="people" />
      <Kpi label="Highest-risk decile" value={pct(d.deciles.at(-1)?.attendance)} detail="Observed attendance within 12 months" tone="coral" icon="people" />
    </div>
    <div className="grid2">
      <Panel title="Model discrimination" subtitle={`ROC curve · held-out ${d.meta.test_year} invitations`}>
        <Chart height={300} label="ROC curves for model, baseline and random ranking"><LineChart margin={{ top: 10, right: 20, left: -12, bottom: 12 }}>
          <CartesianGrid {...GRID} /><XAxis {...AXIS} type="number" dataKey="fpr" domain={[0, 1]} tickFormatter={pctTick} /><YAxis {...AXIS} type="number" domain={[0, 1]} tickFormatter={pctTick} />
          <Tooltip content={<ChartTooltip labelFormat={(v) => `False positive rate: ${pct(v)}`} />} /><Legend iconType="circle" iconSize={6} wrapperStyle={{ paddingTop: 14 }} />
          <Line data={d.roc.model} dataKey="tpr" name="Model" stroke={INDIGO} strokeWidth={2.5} dot={false} isAnimationActive={false} />
          <Line data={d.roc.baseline} dataKey="tpr" name="Baseline" stroke={CORAL} strokeWidth={2} dot={false} isAnimationActive={false} />
          <Line data={[{ fpr: 0, tpr: 0 }, { fpr: 1, tpr: 1 }]} dataKey="tpr" name="Random" stroke={GREY} strokeDasharray="5 5" dot={false} isAnimationActive={false} />
        </LineChart></Chart><div className="chart-caption">Horizontal: false positive rate · Vertical: non-attenders captured</div>
      </Panel>
      <Panel title="Targeting at limited outreach capacity" subtitle="Observed attenders among the highest-risk women selected">
        <div className="targeting-highlight">
          <strong>{pct(t10?.top_wasted_rule ? 1 - t10.top_wasted_model / t10.top_wasted_rule : null, 0)} fewer observed attenders</strong>
          <span>At 10% capacity: {num(t10?.top_wasted_model)} model vs {num(t10?.top_wasted_rule)} baseline</span>
        </div>
        <Chart height={265} label="Observed attendance among the highest-risk 0 to 40 percent selected; vertical scale 0 to 6 percent"><LineChart margin={{ top: 12, right: 20, left: -12, bottom: 12 }}>
          <CartesianGrid {...GRID} /><XAxis {...AXIS} type="number" dataKey="top_share" domain={[0, 0.4]} ticks={[0, 0.1, 0.2, 0.3, 0.4]} allowDataOverflow tickFormatter={pctTick} /><YAxis {...AXIS} domain={[0, 0.06]} ticks={[0, 0.02, 0.04, 0.06]} allowDataOverflow tickFormatter={pctTick} />
          <Tooltip content={<ChartTooltip labelFormat={(v) => `Selected share: ${pct(v, 0)}`} />} /><Legend iconType="circle" iconSize={6} wrapperStyle={{ paddingTop: 14 }} />
          <ReferenceLine x={0.1} stroke={GREY} strokeDasharray="4 4" />
          <Line data={d.gain.model.filter((r) => r.top_share <= 0.400001)} dataKey="attendance_in_top" name="Model" stroke={INDIGO} strokeWidth={2.5} dot={false} isAnimationActive={false} />
          <Line data={d.gain.baseline.filter((r) => r.top_share <= 0.400001)} dataKey="attendance_in_top" name="Baseline" stroke={CORAL} strokeWidth={2} dot={false} isAnimationActive={false} />
        </LineChart></Chart><div className="chart-caption">Zoom: 0–40% selected, 0–6% attendance; both axes start at zero. Lower is better for targeting, not a measured outreach effect.</div>
      </Panel>
    </div>
    <Panel title="Model vs. baseline, in people" subtitle="Same selection size. Different ranking." className="section-gap" action={<Badge>TEST {d.meta.test_year}</Badge>}
      footer="Observed attendance is a retrospective targeting measure. It does not establish who benefits from extra contact.">
      <Table label="Model and baseline targeting comparison"><thead><tr><th>Selected share</th><th className="n">Women</th><th className="n">Low-risk attendance · model / baseline</th><th className="n">High-risk attenders · model / baseline</th></tr></thead>
        <tbody>{(d.targeting || []).map((r) => <tr key={r.share}><td><Badge>{pct(r.share, 0)}</Badge></td><td className="n">{num(r.n)}</td>
          <td className="n"><span className="ok">{pct(r.bottom_attendance_model)}</span> / {pct(r.bottom_attendance_rule)}</td>
          <td className="n"><span className="ok">{num(r.top_wasted_model)}</span> / {num(r.top_wasted_rule)}</td></tr>)}</tbody>
      </Table>
    </Panel>
    {d.ranking_quality && <Panel title="Ranking benchmarks" subtitle="Context for interpreting model performance" className="section-gap">
      <Table label="Ranking quality benchmarks"><thead><tr><th>Scorer</th><th className="n">ROC-AUC</th><th className="n">Average precision · attendance</th></tr></thead>
        <tbody>{d.ranking_quality.map((r) => <tr key={r.scorer}><td><strong>{{ random: "Random score", rule: "Baseline", model: "Model" }[r.scorer] || r.scorer}</strong></td>
          <td className="n">{fixed(r.roc_auc)}</td><td className="n">{fixed(r.ap_attendance)}</td></tr>)}</tbody></Table>
      <div className="panel-footer">The KPI measures non-attendance (81% of the test group); this table measures attendance (19%). The positive class changes the AP value and its random baseline.</div>
    </Panel>}
  </>;
}

export function Why({ d }) {
  const [key, setKey] = useState("prior_invitations");
  const [k, setK] = useState(10);
  const fi = d.feature_importance.slice(0, 12).map((r) => ({ ...r, label: FEATURES[r.feature] || r.feature,
    color: r.direction === 1 ? INDIGO : r.direction === -1 ? TEAL : GREY }));
  const isShap = fi.every((r) => r.method === "mean_abs_shap");
  const regions = [...d.attendance_by.region].sort((a, b) => a.attendance - b.attendance);
  const shown = [...new Map([...regions.slice(0, k), ...regions.slice(-k)].map((r) => [r.group, r])).values()];
  return <>
    <Panel title="What drives the prediction?" subtitle={isShap ? "Mean absolute SHAP impact on predicted risk · associations, not causes" : "Exported feature importance · associations, not causes"} className="section-gap" action={<Badge>{isShap ? "SHAP METHOD" : "IMPORTANCE METHOD"}</Badge>}>
      <div className="legend-explainer"><LegendItem color={INDIGO}>Higher value → higher risk</LegendItem><LegendItem color={TEAL}>Higher value → lower risk</LegendItem><LegendItem color={GREY}>No directional summary</LegendItem></div>
      <Chart height={430} label="Feature importance and direction of association"><BarChart data={fi} layout="vertical" margin={{ top: 0, right: 28, left: 24, bottom: 8 }}>
        <CartesianGrid {...GRID} horizontal={false} vertical /><XAxis {...AXIS} type="number" /><YAxis {...AXIS} type="category" dataKey="label" width={225} tick={{ fontSize: 11 }} />
        <Tooltip cursor={{ fill: "#f5f6fc" }} content={<ChartTooltip format={(v) => fixed(v)} />} />
        <Bar dataKey="importance" name={isShap ? "Mean |SHAP|" : "Importance"} radius={[0, 3, 3, 0]} maxBarSize={17} isAnimationActive={false}>{fi.map((r) => <Cell key={r.feature} fill={r.color} />)}</Bar>
      </BarChart></Chart>
    </Panel>
    <Panel title="Explore attendance patterns" subtitle={`Observed outcomes across ${period(d)}`} className="section-gap">
      <div className="controls panel-controls"><label className="field">Break down by<select value={key} onChange={(e) => setKey(e.target.value)}>
        {Object.entries(BREAKDOWNS).filter(([id]) => d.attendance_by[id]).map(([id, name]) => <option key={id} value={id}>{name}</option>)}</select></label></div>
      <Chart height={290} label={`Attendance by ${BREAKDOWNS[key]}`}><RateBars rows={d.attendance_by[key]} groupLabels={CAPPED_GROUP_LABELS[key]} /></Chart>
      <div className="chart-caption">Attendance within 12 months · whiskers show 95% confidence intervals.
        {BREAKDOWN_NOTES[key] && <><br />{BREAKDOWN_NOTES[key]}</>}</div>
    </Panel>
    <Panel title="Regional variation" subtitle="Territorial offices with the lowest and highest attendance" className="section-gap" action={<Badge tone="neutral">{regions.length} OFFICES</Badge>}>
      <div className="controls panel-controls"><label className="field">Offices at each end: {k}<input type="range" min={5} max={20} value={k} onChange={(e) => setK(+e.target.value)} /></label></div>
      <Chart height={50 + 25 * shown.length} label="Attendance by territorial office"><RateBars rows={shown} horizontal /></Chart>
      <div className="panel-footer">Crude rates are not adjusted for age or invitation history. A territorial office is not a measure of travel distance or access.</div>
    </Panel>
  </>;
}

export function What({ d, navigate }) {
  const speed = ["3m", "6m", "12m"].map((w) => Object.fromEntries([["window", w], ...d.segment_response_speed.map((r) => [r.segment, r[w]])]));
  const since = d.attendance_by.months_since_last_screening.filter((r) => r.group !== "none_in_5y");
  const recent = d.recently_screened_per_year;
  const recentN = recent.reduce((s, r) => s + r.n, 0);
  const recentRate = recentN ? recent.reduce((s, r) => s + r.attendance * r.n, 0) / recentN : null;
  return <>
    <Panel title="Segment-level outreach" subtitle={`Exclusive operational groups · test ${d.meta.test_year}`} className="section-gap" action={<Badge>{d.segments.length} SEGMENTS</Badge>}>
      <SegmentTable d={d} />
    </Panel>
    <div className="grid2">
      <Panel title="When women respond" subtitle="Cumulative attendance following the invitation">
        <Chart height={280} label="Attendance at three, six and twelve months by segment"><LineChart data={speed} margin={{ top: 12, right: 20, left: -12, bottom: 12 }}>
          <CartesianGrid {...GRID} /><XAxis {...AXIS} dataKey="window" /><YAxis {...AXIS} tickFormatter={pctTick} />
          <Tooltip content={<ChartTooltip labelFormat={(v) => `${v.replace("m", " months")} after invitation`} />} />
          {d.segment_response_speed.map((r) => <Line key={r.segment} dataKey={r.segment} name={SEGMENTS[r.segment] || r.segment} stroke={segmentColor(r.segment)} strokeWidth={2} dot={{ r: 3, strokeWidth: 0, fill: segmentColor(r.segment) }} isAnimationActive={false} />)}
        </LineChart></Chart>
        <div className="inline-legend">{d.segment_response_speed.map((r) => <LegendItem key={r.segment} color={segmentColor(r.segment)}>{SEGMENTS[r.segment] || r.segment}</LegendItem>)}</div>
      </Panel>
      <Panel title="Time since the last screening" subtitle="Attendance after a new invitation">
        <Chart height={300} label="Attendance by months since last screening"><RateBars rows={since} color={TEAL} /></Chart>
        <div className="chart-caption">Months since the previous screening, measured at invitation.
          * 61+: edge of the 5-year history window in the VZP data (193 invitations).</div>
      </Panel>
    </div>
    <Panel title="Important notice" subtitle="Recent screening before a new invitation" className="section-gap process-review" action={<Badge tone="amber">PROCESS REVIEW</Badge>}>
      <div className="process-grid"><div className="process-stat"><strong>{num(recentAverage(d))}</strong><p>invitations per year, on average<br />{pct(recentRate)} attended within 12 months</p></div>
        <div className="process-explanation"><div><h3>What we found</h3><p>These women had a screening recorded within six months before their invitation. We do not yet know whether those invitations were unnecessary.</p></div>
          <div className="process-suggestion"><h3>Suggested change</h3><p>Before mailing, check the latest screening records. Flag recent screenings for an eligibility review, then postpone an invitation only when programme rules allow.</p></div></div></div>
    </Panel>
    <div className="insight-strip"><span className="insight-icon"><Icon name="flask" /></span><div><h3>Turn an outreach idea into a measured result</h3><p>Plan the experiment around a segment, an outcome and a minimum detectable effect.</p></div>
      <button className="text-button" onClick={() => navigate("experiment")}>Plan an experiment <Icon name="arrow" size={15} /></button></div>
  </>;
}

export function Verify({ d }) {
  const seg = segmentRows(d).filter((r) => PILOT_SEGMENTS.includes(r.segment));
  const initial = seg.find((r) => r.segment === "lapsed_regular") || seg[0];
  const [segment, setSegment] = useState(initial.segment);
  const [mde, setMde] = useState(2);
  const row = seg.find((r) => r.segment === segment) || initial;
  const n = nPerGroup(row.attendance, mde / 100, .05, .8);
  const fits = n != null && 2 * n <= row.n;
  const design = useMemo(() => {
    const by = {};
    for (const r of d.experiment_design.filter((r) => PILOT_SEGMENTS.includes(r.segment))) (by[r.segment] ??= {})[r.mde_pp] = r.n_per_arm;
    return by;
  }, [d]);
  const mdes = [...new Set(d.experiment_design.map((r) => r.mde_pp))].sort((a, b) => a - b);
  return <>
    <Panel className="section-gap calculator-panel">
      <div className="controls calculator-controls">
        <label className="field">Segment<select aria-label="Segment" value={segment} onChange={(e) => setSegment(e.target.value)}>{seg.map((r) => <option key={r.segment} value={r.segment}>{r.label}</option>)}</select></label>
        <label className="field">Effect to detect: +{mde.toFixed(1)} pp<input type="range" min={.5} max={10} step={.5} value={mde} onChange={(e) => setMde(+e.target.value)} /></label>
      </div>
      <div className="planner-intervention"><span><Icon name={PLAYBOOKS[segment].icon} size={18} />{PLAYBOOKS[segment].title}</span><InterventionActions segment={segment} d={d} /></div>
      {n == null ? <p className="result-error" role="alert">This effect is too large for the segment's baseline attendance.</p> : <div className="calculator-results" aria-live="polite">
        <div><span className="result-label">Women per group</span><div className="result-number">{num(n)}</div><span className="result-note">baseline attendance {pct(row.attendance)}</span></div>
        <div><span className="result-label">Total in the pilot</span><div className="result-number">{num(2 * n)}</div></div>
        <div><span className="result-label">Available in {d.meta.test_year}</span><div className="result-number">{num(row.n)}</div>
          <Badge tone={fits ? "teal" : "amber"}>{fits ? "Fits in one year" : "Needs over a year"}</Badge></div>
      </div>}
      {segment === "care_no_prevention" && <div className="panel-body"><Notice tone="amber">Randomizing whole practices needs a larger sample.</Notice></div>}
    </Panel>
    <Panel title="Women per group" subtitle="80% power · α = 0.05" className="section-gap">
      <Table label="Sample sizes by segment and detectable effect"><thead><tr><th>Segment</th>{mdes.map((m) => <th key={m} className="n">+{m} pp</th>)}</tr></thead>
        <tbody>{Object.entries(design).map(([id, values]) => <tr key={id}><td><strong>{SEGMENTS[id] || id}</strong></td>{mdes.map((m) => <td className="n" key={m}>{num(values[m])}</td>)}</tr>)}</tbody></Table>
    </Panel>
  </>;
}
