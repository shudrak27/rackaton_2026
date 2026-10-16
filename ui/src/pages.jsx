import React, { useMemo, useState } from "react";
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, ErrorBar, Legend, Line, LineChart,
  Tooltip, XAxis, YAxis,
} from "recharts";
import { BREAKDOWNS, FEATURES, SEGMENTS, num, pct } from "./labels.js";
import { nPerGroup } from "./power.js";
import { Badge, Chart, ChartTooltip, Icon, Kpi, LegendItem, Notice, Panel, Table } from "./components.jsx";

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

export function RateBars({ rows = [], color = INDIGO, horizontal = false, width, height }) {
  const data = rows.map((r) => ({ ...r, group: r.group === "none_in_5y" ? "No screen in 5y" : String(r.group),
    err: [Math.max(0, r.attendance - r.ci_low), Math.max(0, r.ci_high - r.attendance)] }));
  return <BarChart width={width} height={height} data={data} layout={horizontal ? "vertical" : "horizontal"}
    margin={{ top: 8, right: 18, left: horizontal ? 5 : -12, bottom: 8 }} barCategoryGap="30%">
    <CartesianGrid {...GRID} vertical={horizontal} horizontal={!horizontal} />
    {horizontal ? <><XAxis {...AXIS} type="number" tickFormatter={pctTick} /><YAxis {...AXIS} type="category" dataKey="group" width={125} /></>
      : <><XAxis {...AXIS} dataKey="group" /><YAxis {...AXIS} tickFormatter={pctTick} width={58} /></>}
    <Tooltip cursor={{ fill: "#f4f5ff" }} content={<ChartTooltip showCount />} />
    <Bar dataKey="attendance" name="Attendance" fill={color} radius={horizontal ? [0, 3, 3, 0] : [4, 4, 0, 0]} maxBarSize={42} isAnimationActive={false}>
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
      <td className="intervention-cell">{r.intervention}</td>
    </tr>)}</tbody>
  </Table>;
}

export function Overview({ d, navigate }) {
  const t10 = d.targeting?.find((r) => Math.abs(r.share - .1) < 1e-9);
  const reduction = t10?.top_wasted_rule ? 1 - t10.top_wasted_model / t10.top_wasted_rule : null;
  const first = d.deciles[0], last = d.deciles.at(-1);
  return <>
    <div className="kpis">
      <Kpi label="Total invitations" value={num(d.meta.n_invitations)} detail={`${num(d.meta.n_clients)} women in the cohort`} foot={`Invitation history · ${period(d)}`} tone="amber" icon="mail" />
      <Kpi label="Attendance rate" value={pct(d.meta.attendance_overall)} detail="Screened within 12 months" foot="Observed across all invitation years" tone="coral" icon="calendar" />
      <Kpi label="Lowest-risk 10% · attendance" value={pct(t10?.bottom_attendance_model, 0)} detail={`Compared with ${pct(t10?.bottom_attendance_rule, 0)} using the rule`} foot={`A standard letter is enough · ${d.meta.test_year}`} tone="teal" icon="people" highlight />
      <Kpi label="Model ROC-AUC" value={fixed(metric(d, "roc_auc"))} detail={`Invitation-count rule: ${fixed(metric(d, "roc_auc", "baseline"))}`} foot="Evaluated on the held-out test year" icon="chart" />
    </div>
    <div className="overview-grid">
      <Panel title="A clearer picture of risk" subtitle="Observed attendance across risk deciles" className="risk-highlight" action={<Badge>TEST {d.meta.test_year}</Badge>}
        footer="Equal-sized groups, ordered by predicted non-attendance.">
        <div className="risk-range"><div><strong>{pct(first?.attendance)}</strong><small>Lowest-risk decile</small></div><Icon name="arrow" /><div><strong>{pct(last?.attendance)}</strong><small>Highest-risk decile</small></div></div>
        <Chart height={122} label="Attendance decreases across model risk deciles">
          <AreaChart data={d.deciles} margin={{ top: 12, right: 0, left: 0, bottom: 0 }}>
            <defs><linearGradient id="riskFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={INDIGO} stopOpacity={.22} /><stop offset="100%" stopColor={INDIGO} stopOpacity={0} /></linearGradient></defs>
            <Tooltip content={<ChartTooltip labelFormat={(v) => `Risk decile ${d.deciles[v]?.decile ?? v}`} />} />
            <Area type="monotone" dataKey="attendance" name="Observed attendance" stroke={INDIGO} strokeWidth={2} fill="url(#riskFill)" isAnimationActive={false} />
          </AreaChart>
        </Chart>
      </Panel>
      <Panel title="Outreach precision" subtitle="Highest-risk 10% · model vs. rule" action={<Icon name="target" size={18} />}
        footer="Historical attenders in the selected group; outreach effects need a trial.">
        <div className="precision-body"><div className="precision-summary"><div className="precision-value">{pct(reduction, 0)} fewer</div>
          <p className="precision-description">contacts with observed attenders</p></div>
          {[{ name: "Model", value: t10?.top_wasted_model, color: INDIGO }, { name: "Invitation-count rule", value: t10?.top_wasted_rule, color: GREY }].map((r) => <div className="progress-row" key={r.name}>
            <div className="progress-label"><span>{r.name}</span><strong>{num(r.value)}</strong></div>
            <div className="progress-track"><i className="progress-fill" style={{ width: `${t10?.top_wasted_rule ? 100 * r.value / t10.top_wasted_rule : 0}%`, background: r.color }} /></div>
          </div>)}
        </div>
      </Panel>
    </div>
    <div className="grid2">
      <Panel title="Attendance by invitation history" subtitle="Observed attendance within 12 months" action={<Badge tone="neutral">{period(d)}</Badge>}>
        <Chart label="Attendance by previous invitation count"><RateBars rows={d.attendance_by.prior_invitations} /></Chart>
        <div className="chart-caption">Previous invitations · 0 = first invitation, 10 = 10 or more</div>
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
  return <>
    <div className="kpis">
      <Kpi label="Model ROC-AUC" value={fixed(metric(d, "roc_auc"))} detail={`Rule baseline: ${fixed(metric(d, "roc_auc", "baseline"))}`} foot="Ranking non-attendance risk" icon="chart" />
      <Kpi label="Average precision" value={fixed(rq.model?.ap_attendance)} detail={`Attendance · rule: ${fixed(rq.rule?.ap_attendance)}`} foot="Evaluated for the attendance class" tone="amber" icon="target" />
      <Kpi label="Lowest-risk decile" value={pct(d.deciles[0]?.attendance)} detail="Observed attendance within 12 months" foot="10% with the lowest predicted risk" tone="teal" icon="people" />
      <Kpi label="Highest-risk decile" value={pct(d.deciles.at(-1)?.attendance)} detail="Observed attendance within 12 months" foot="10% with the highest predicted risk" tone="coral" icon="people" />
    </div>
    <div className="grid2">
      <Panel title="Model discrimination" subtitle={`ROC curve · held-out ${d.meta.test_year} invitations`}>
        <Chart height={300} label="ROC curves for model, rule and random ranking"><LineChart margin={{ top: 10, right: 20, left: -12, bottom: 12 }}>
          <CartesianGrid {...GRID} /><XAxis {...AXIS} type="number" dataKey="fpr" domain={[0, 1]} tickFormatter={pctTick} /><YAxis {...AXIS} type="number" domain={[0, 1]} tickFormatter={pctTick} />
          <Tooltip content={<ChartTooltip labelFormat={(v) => `False positive rate: ${pct(v)}`} />} /><Legend iconType="circle" iconSize={6} wrapperStyle={{ paddingTop: 14 }} />
          <Line data={d.roc.model} dataKey="tpr" name="Model" stroke={INDIGO} strokeWidth={2.5} dot={false} isAnimationActive={false} />
          <Line data={d.roc.baseline} dataKey="tpr" name="Rule" stroke={CORAL} strokeWidth={2} dot={false} isAnimationActive={false} />
          <Line data={[{ fpr: 0, tpr: 0 }, { fpr: 1, tpr: 1 }]} dataKey="tpr" name="Random" stroke={GREY} strokeDasharray="5 5" dot={false} isAnimationActive={false} />
        </LineChart></Chart><div className="chart-caption">Horizontal: false positive rate · Vertical: non-attenders captured</div>
      </Panel>
      <Panel title="Precision at your outreach capacity" subtitle="Attendance among the highest-risk women selected">
        <Chart height={300} label="Attendance among selected high-risk women"><LineChart margin={{ top: 10, right: 20, left: -12, bottom: 12 }}>
          <CartesianGrid {...GRID} /><XAxis {...AXIS} type="number" dataKey="top_share" domain={[0, 1]} tickFormatter={pctTick} /><YAxis {...AXIS} tickFormatter={pctTick} />
          <Tooltip content={<ChartTooltip labelFormat={(v) => `Selected share: ${pct(v, 0)}`} />} /><Legend iconType="circle" iconSize={6} wrapperStyle={{ paddingTop: 14 }} />
          <Line data={d.gain.model} dataKey="attendance_in_top" name="Model" stroke={INDIGO} strokeWidth={2.5} dot={false} isAnimationActive={false} />
          <Line data={d.gain.baseline} dataKey="attendance_in_top" name="Rule" stroke={CORAL} strokeWidth={2} dot={false} isAnimationActive={false} />
        </LineChart></Chart><div className="chart-caption">A lower curve means fewer observed attenders selected for extra outreach.</div>
      </Panel>
    </div>
    <Panel title="Model vs. rule, in people" subtitle="Same selection size. Different ranking." className="section-gap" action={<Badge>TEST {d.meta.test_year}</Badge>}
      footer="Observed attendance is a retrospective targeting measure. It does not establish who benefits from extra contact.">
      <Table label="Model and rule targeting comparison"><thead><tr><th>Selected share</th><th className="n">Women</th><th className="n">Low-risk attendance · model / rule</th><th className="n">High-risk attenders · model / rule</th></tr></thead>
        <tbody>{(d.targeting || []).map((r) => <tr key={r.share}><td><Badge>{pct(r.share, 0)}</Badge></td><td className="n">{num(r.n)}</td>
          <td className="n"><span className="ok">{pct(r.bottom_attendance_model)}</span> / {pct(r.bottom_attendance_rule)}</td>
          <td className="n"><span className="ok">{num(r.top_wasted_model)}</span> / {num(r.top_wasted_rule)}</td></tr>)}</tbody>
      </Table>
    </Panel>
    {d.ranking_quality && <Panel title="Ranking benchmarks" subtitle="Context for interpreting model performance" className="section-gap">
      <Table label="Ranking quality benchmarks"><thead><tr><th>Scorer</th><th className="n">ROC-AUC</th><th className="n">Average precision · attendance</th></tr></thead>
        <tbody>{d.ranking_quality.map((r) => <tr key={r.scorer}><td><strong>{{ random: "Random score", rule: "Invitation-count rule", model: "Model" }[r.scorer] || r.scorer}</strong></td>
          <td className="n">{fixed(r.roc_auc)}</td><td className="n">{fixed(r.ap_attendance)}</td></tr>)}</tbody></Table>
      <div className="panel-footer">Average precision uses the attendance class. Its random baseline is the test-year attendance rate.</div>
    </Panel>}
    <Notice icon="shield"><strong>Evaluated on a future wave.</strong> These results use {d.meta.test_year} invitations held out from training. The score estimates non-attendance within 12 months.</Notice>
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
    <Notice><strong>Understand the signals.</strong> Feature importance explains the model’s associations. An experiment is needed to establish what changes attendance.</Notice>
    <Panel title="What drives the prediction?" subtitle={isShap ? "Top features by mean absolute SHAP value" : "Top features by exported importance"} className="section-gap" action={<Badge>{isShap ? "SHAP" : "IMPORTANCE"}</Badge>}>
      <div className="legend-explainer"><LegendItem color={INDIGO}>Higher value → higher risk</LegendItem><LegendItem color={TEAL}>Higher value → lower risk</LegendItem><LegendItem color={GREY}>No directional summary</LegendItem></div>
      <Chart height={430} label="Feature importance and direction of association"><BarChart data={fi} layout="vertical" margin={{ top: 0, right: 28, left: 0, bottom: 8 }}>
        <CartesianGrid {...GRID} horizontal={false} vertical /><XAxis {...AXIS} type="number" /><YAxis {...AXIS} type="category" dataKey="label" width={195} tick={{ fontSize: 10 }} />
        <Tooltip cursor={{ fill: "#f5f6fc" }} content={<ChartTooltip format={(v) => fixed(v)} />} />
        <Bar dataKey="importance" name={isShap ? "Mean |SHAP|" : "Importance"} radius={[0, 3, 3, 0]} maxBarSize={17} isAnimationActive={false}>{fi.map((r) => <Cell key={r.feature} fill={r.color} />)}</Bar>
      </BarChart></Chart>
    </Panel>
    <Panel title="Explore attendance patterns" subtitle={`Observed outcomes across ${period(d)}`} className="section-gap">
      <div className="controls panel-controls"><label className="field">Break down by<select value={key} onChange={(e) => setKey(e.target.value)}>
        {Object.entries(BREAKDOWNS).filter(([id]) => d.attendance_by[id]).map(([id, name]) => <option key={id} value={id}>{name}</option>)}</select></label></div>
      <Chart height={290} label={`Attendance by ${BREAKDOWNS[key]}`}><RateBars rows={d.attendance_by[key]} /></Chart>
      <div className="chart-caption">Attendance within 12 months · whiskers show the intervals provided in the aggregate export.</div>
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
    <Notice tone="amber"><strong>High risk does not guarantee a large treatment effect.</strong> Use these segments to define pilots, then scale the support that improves attendance.</Notice>
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
        <div className="chart-caption">Months since the previous screening, measured at invitation.</div>
      </Panel>
    </div>
    <Panel title="A closer look at invitation timing" subtitle="Invitations sent within six months of a recorded screening" className="section-gap" action={<Badge tone="amber">PROCESS REVIEW</Badge>}>
      <div className="process-grid"><div className="process-stat"><strong>{num(recentAverage(d))}</strong><p>invitations per year, on average<br />{pct(recentRate)} subsequent attendance</p></div>
        <ul className="points"><li><strong>Observed:</strong> some invitations follow a recently recorded screening.</li>
          <li><strong>Possible explanation:</strong> the mailing list may not include the latest claims. This is a hypothesis.</li>
          <li><strong>Proposed action:</strong> review fresh claims before sending and check eligibility for postponement.</li>
          <li><strong>Next step:</strong> validate the workflow before claiming avoidable costs.</li></ul></div>
    </Panel>
    <div className="insight-strip"><span className="insight-icon"><Icon name="flask" /></span><div><h3>Turn an outreach idea into a measured result</h3><p>Plan the experiment around a segment, an outcome and a minimum detectable effect.</p></div>
      <button className="text-button" onClick={() => navigate("experiment")}>Plan an experiment <Icon name="arrow" size={15} /></button></div>
  </>;
}

export function Verify({ d }) {
  const seg = segmentRows(d);
  const initial = seg.find((r) => r.segment === "repeated_nonresponder") || seg[0];
  const [segment, setSegment] = useState(initial.segment);
  const row = seg.find((r) => r.segment === segment) || initial;
  const [baseline, setBaseline] = useState(+(initial.attendance * 100).toFixed(1));
  const [mde, setMde] = useState(2);
  const [power, setPower] = useState(.8);
  const n = nPerGroup(Number(baseline) / 100, mde / 100, .05, power);
  const design = useMemo(() => {
    const by = {};
    for (const r of d.experiment_design) (by[r.segment] ??= {})[r.mde_pp] = r.n_per_arm;
    return by;
  }, [d]);
  const mdes = [...new Set(d.experiment_design.map((r) => r.mde_pp))].sort((a, b) => a - b);
  function changeSegment(value) { setSegment(value); setBaseline(+((seg.find((r) => r.segment === value)?.attendance || 0) * 100).toFixed(1)); }
  return <>
    <Panel title="From prediction to evidence" subtitle="A randomized test of segment-specific support" className="section-gap" action={<Badge tone="amber">PLANNING</Badge>}>
      <div className="experiment-steps">{[
        ["01", "Assign the intervention", "Randomize women within segment × risk-quintile strata."],
        ["02", "Measure attendance", "Compare standard invitations with additional support over 12 months."],
        ["03", "Learn what works", "Analyze by assigned group. Use results to develop uplift models."],
      ].map(([i, title, body]) => <div className="experiment-step" key={i}><span className="step-number">{i}</span><div><strong>{title}</strong><p>{body}</p></div></div>)}</div>
    </Panel>
    <Panel title="Sample size calculator" subtitle="Plan a two-arm trial for an absolute increase in attendance" className="section-gap" action={<Badge>1:1 ALLOCATION</Badge>}>
      <div className="controls calculator-controls">
        <label className="field">Target segment<select aria-label="Target segment" value={segment} onChange={(e) => changeSegment(e.target.value)}>{seg.map((r) => <option key={r.segment} value={r.segment}>{r.label}</option>)}</select></label>
        <label className="field">Baseline attendance (%)<input type="number" min={.1} max={99.9} step={.1} value={baseline} onChange={(e) => setBaseline(e.target.value)} /></label>
        <label className="field">Minimum detectable effect: +{mde.toFixed(1)} pp<input type="range" min={.5} max={10} step={.5} value={mde} onChange={(e) => setMde(+e.target.value)} /></label>
        <label className="field">Statistical power<select value={power} onChange={(e) => setPower(+e.target.value)}>{[.7, .8, .9].map((p) => <option key={p} value={p}>{pct(p, 0)}</option>)}</select></label>
      </div>
      {n == null ? <p className="result-error" role="alert">Choose a positive baseline and effect whose sum is below 100%.</p> : <div className="calculator-results" aria-live="polite">
        <div><span className="result-label">Required per arm</span><div className="result-number">{num(n)}</div><span className="result-note">Women in each group</span></div>
        <div><span className="result-label">Total participants</span><div className="result-number">{num(n * 2)}</div><span className="result-note">Control + treatment</span></div>
        <div><span className="result-label">Available in test-year segment</span><div className="result-number">{num(row.n)}</div><Badge tone={2 * n <= row.n ? "teal" : "amber"}>{2 * n <= row.n ? "Within annual segment size" : "Exceeds annual segment size"}</Badge></div>
      </div>}
      <div className="panel-footer">Two-sided α = 0.05 · Historical segment size is an upper recruitment bound. Effect size is a planning assumption.</div>
    </Panel>
    <Panel title="Recruitment requirements by segment" subtitle="Women per arm · α = 0.05 · 80% power" className="section-gap" footer="Exported planning scenarios. The calculator above updates independently when you change its inputs.">
      <Table label="Sample sizes by segment and detectable effect"><thead><tr><th>Segment</th>{mdes.map((m) => <th key={m} className="n">+{m} pp</th>)}</tr></thead>
        <tbody>{Object.entries(design).map(([id, values]) => <tr key={id}><td><strong>{SEGMENTS[id] || id}</strong></td>{mdes.map((m) => <td className="n" key={m}>{num(values[m])}</td>)}</tr>)}</tbody></Table>
    </Panel>
    <Notice icon="clock"><strong>Keep the primary outcome fixed.</strong> Use 12-month attendance for intention-to-treat analysis. Three-month attendance is an early signal, not a replacement endpoint.</Notice>
  </>;
}
