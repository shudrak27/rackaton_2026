import React, { useMemo, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Cell, ErrorBar, Line, LineChart, Tooltip, XAxis, YAxis,
} from "recharts";
import { BREAKDOWNS, FEATURES, SEGMENTS, num, pct } from "./labels.js";
import { nPerGroup } from "./power.js";
import { Badge, Chart, ChartTooltip, Icon, LegendItem, Notice, Panel, Table } from "./components.jsx";
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
  const call = d.personas?.call?.find((c) => c.share === 0.1);
  const gyn = contrast(d.attendance_by.gyn_prevention_24m);
  return <>
    <div className="hero-stats">
      <div className="hero-stat"><strong>{num(d.meta.n_invitations)}</strong><span>invitations analysed · {num(d.meta.n_clients)} women</span></div>
      <div className="hero-stat"><strong>{pct(d.meta.attendance_overall, 0)}</strong><span>come after a standard letter</span></div>
      <div className="hero-stat hero-accent"><strong>{pct(first?.attendance, 0)} <small>vs</small> {pct(last?.attendance, 1)}</strong><span>the model splits likely attenders from women who will skip</span></div>
      <div className="hero-stat"><strong>−{pct(reduction, 0)}</strong><span>wasted calls compared with today's rule</span></div>
    </div>
    <Panel title="The model sorts women by how likely they are to skip" subtitle={`Real attendance in ${d.meta.test_year}, ten equal groups by predicted risk`}
      action={<Badge tone="teal">{d.meta.test_year} · DATA THE MODEL NEVER SAW</Badge>} className="section-gap">
      <Chart height={300} label="Actual attendance in each model risk group"><DecileChart d={d} /></Chart>
      <div className="chart-caption">Green: a standard letter is enough. Right side: women who need more than a letter.</div>
    </Panel>
    <div className="finding-grid">
      <button className="finding" onClick={() => navigate("call")}>
        <span className="finding-icon"><Icon name="phone" size={22} /></span><h3>Who to call</h3>
        <p>{call ? <>Typically aged {call.top_age_band}, invited {Math.round(call.median_prior_invitations)} times, about {Math.round(call.median_contacts_12m)} doctor visit a year.
          Without a call only <b>{pct(call.attendance, 1)}</b> come.</> : "Portrait of the woman worth a call."}</p>
        <span className="finding-link">See her portrait <Icon name="arrow" size={15} /></span></button>
      <button className="finding" onClick={() => navigate("drivers")}>
        <span className="finding-icon"><Icon name="drivers" size={22} /></span><h3>Why women skip</h3>
        <p>{gyn ? <>No gynaecologist check-up: <b>{pct(gyn.low.attendance, 0)}</b> come. Regular check-ups: <b>{pct(gyn.high.attendance, 0)}</b>.
          Prevention habits predict screening.</> : "The habits behind skipping."}</p>
        <span className="finding-link">See the drivers <Icon name="arrow" size={15} /></span></button>
      <button className="finding" onClick={() => navigate("segments")}>
        <span className="finding-icon"><Icon name="clock" size={22} /></span><h3>Quick win</h3>
        <p><b>{num(recentAverage(d))}</b> letters a year go to women screened in the last 6 months. Only ~2% of them come again.</p>
        <span className="finding-link">See the fix <Icon name="arrow" size={15} /></span></button>
    </div>
  </>;
}

// Lowest- and highest-attendance group of a breakdown (for plain "this vs that" driver cards).
function contrast(rows) {
  if (!rows?.length) return null;
  const sorted = [...rows].filter((r) => r.group !== "none_in_5y").sort((a, b) => a.attendance - b.attendance);
  return { low: sorted[0], high: sorted.at(-1) };
}

const DRIVERS = [
  ["prior_invitations", "mail", "Ignored earlier letters", (g) => g === "0" ? "First letter" : `${g}${g === "10" ? "+" : ""} letters before`],
  ["gyn_prevention_24m", "doctor", "Gynaecologist check-ups", (g) => g === "0" ? "No check-up in 2 years" : `${g}${g === "3" ? "+" : ""} check-ups in 2 years`],
  ["other_screening_36m", "shield", "Other cancer screenings", (g) => g === "0" ? "None in 3 years" : `${g}${g === "4" ? "+" : ""} in 3 years`],
  ["healthcare_contacts_12m", "activity", "Doctor visits last year", (g) => g === "0" ? "No visits" : `${g} visits`],
  ["age_band", "calendar", "Age", (g) => `Age ${g}`],
];

export function Why({ d }) {
  const [key, setKey] = useState("prior_invitations");
  const fi = d.feature_importance.slice(0, 8).map((r) => ({ ...r, label: FEATURES[r.feature] || r.feature }));
  const max = Math.max(...fi.map((r) => r.importance));
  return <>
    <div className="driver-grid">{DRIVERS.map(([id, icon, title, say]) => {
      const c = contrast(d.attendance_by[id]);
      if (!c) return null;
      return <section className="driver" key={id}>
        <div className="driver-head"><span className="driver-icon"><Icon name={icon} size={20} /></span><h3>{title}</h3></div>
        {[[c.high, "driver-good"], [c.low, "driver-bad"]].map(([r, cls]) => <div className={`driver-row ${cls}`} key={cls}>
          <span>{say(String(r.group))}</span><div className="driver-bar"><i style={{ width: `${100 * r.attendance / c.high.attendance}%` }} /></div>
          <strong>{pct(r.attendance, 0)}</strong></div>)}
        <p className="driver-x">{(c.high.attendance / c.low.attendance).toFixed(c.high.attendance / c.low.attendance >= 10 ? 0 : 1)}× more likely to come</p>
      </section>;
    })}</div>
    <p className="persona-caveat"><Icon name="info" size={15} />Share who came within 12 months of the letter, all invitations {period(d)}. These are patterns, not causes.</p>

    <div className="grid2">
      <Panel title="What the AI looks at most" subtitle="Ranked by influence on the prediction">
        <ol className="ai-ranking">{fi.map((r, i) => <li key={r.feature}><span className="ai-rank">{i + 1}</span><span className="ai-label">{r.label}</span>
          <div className="ai-bar"><i style={{ width: `${100 * r.importance / max}%` }} /></div></li>)}</ol>
      </Panel>
      <Panel title="Explore any factor" subtitle="Share who came, by group">
        <div className="controls panel-controls"><label className="field"><select aria-label="Factor" value={key} onChange={(e) => setKey(e.target.value)}>
          {Object.entries(BREAKDOWNS).filter(([id]) => d.attendance_by[id]).map(([id, name]) => <option key={id} value={id}>{name}</option>)}</select></label></div>
        <Chart height={280} label={`Attendance by ${BREAKDOWNS[key]}`}><RateBars rows={d.attendance_by[key]} groupLabels={CAPPED_GROUP_LABELS[key]} /></Chart>
        {BREAKDOWN_NOTES[key] && <div className="chart-caption">{BREAKDOWN_NOTES[key]}</div>}
      </Panel>
    </div>
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
