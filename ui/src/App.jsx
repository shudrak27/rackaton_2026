import React, { useEffect, useMemo, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Cell, ErrorBar, Legend, Line, LineChart, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { BREAKDOWNS, FEATURES, SEGMENTS, num, pct } from "./labels.js";
import { nPerGroup } from "./power.js";

const RED = "#c8102e", GREY = "#8c8c8c", GREEN = "#2e7d32", LIGHT = "#d9d9d9";
const pctTick = (v) => `${Math.round(v * 100)}%`;
const metric = (d, name, col = "model") => d.test_metrics.find((r) => r.metric === name)?.[col];
const GROUP_LABELS = { none_in_5y: "No screening in 5 y" };
const withErr = (rows) => rows.map((r) => ({
  ...r, group: GROUP_LABELS[r.group] ?? String(r.group), err: [r.attendance - r.ci_low, r.ci_high - r.attendance],
}));

function Kpi({ label, value, vs, hero }) {
  return (
    <div className={`kpi${hero ? " hero" : ""}`}>
      <div className="label">{label}</div>
      <div className="value">{value}</div>
      {vs && <div className="vs">{vs}</div>}
    </div>
  );
}

function Card({ title, children, height = 320 }) {
  return (
    <div className="card">
      {title && <h3>{title}</h3>}
      <div style={{ width: "100%", height }}>
        <ResponsiveContainer>{children}</ResponsiveContainer>
      </div>
    </div>
  );
}

// ResponsiveContainer injects width/height into its direct child; forward them to the chart.
export function RateBars({ rows, color = RED, horizontal = false, width, height }) {
  const data = withErr(rows);
  const tip = <Tooltip formatter={(v, k, p) => [`${pct(v)} (n = ${num(p.payload.n)})`, "Attendance"]} />;
  if (horizontal) {
    return (
      <BarChart width={width} height={height} data={data} layout="vertical" margin={{ left: 40, right: 20 }}>
        <CartesianGrid strokeDasharray="3 3" horizontal={false} />
        <XAxis type="number" tickFormatter={pctTick} />
        <YAxis type="category" dataKey="group" width={150} tick={{ fontSize: 11 }} />
        {tip}
        <Bar dataKey="attendance" fill={color} radius={[0, 4, 4, 0]}><ErrorBar dataKey="err" width={3} stroke="#555" direction="x" /></Bar>
      </BarChart>
    );
  }
  return (
    <BarChart width={width} height={height} data={data} margin={{ left: 0, right: 10 }}>
      <CartesianGrid strokeDasharray="3 3" vertical={false} />
      <XAxis dataKey="group" tick={{ fontSize: 12 }} />
      <YAxis tickFormatter={pctTick} />
      {tip}
      <Bar dataKey="attendance" fill={color} radius={[4, 4, 0, 0]}><ErrorBar dataKey="err" width={4} stroke="#555" /></Bar>
    </BarChart>
  );
}

// ------------------------------------------------------------------------------------- pages

function Overview({ d }) {
  const t10 = d.targeting?.find((r) => Math.abs(r.share - 0.1) < 1e-9);
  const recent = d.recently_screened_per_year;
  const wasted = recent.reduce((s, r) => s + r.n, 0) / recent.length;
  return (
    <>
      <h2 className="lead">One letter for everyone does not work equally well</h2>
      <div className="kpis">
        <Kpi label="Invitations 2020–2024" value={num(d.meta.n_invitations)} vs={`${num(d.meta.n_clients)} women`} />
        <Kpi label="Attendance within 12 months" value={pct(d.meta.attendance_overall)} />
        {t10 && <Kpi hero label="Lowest-risk 10% attend" value={pct(t10.bottom_attendance_model, 0)}
          vs={<>rule finds only <b>{pct(t10.bottom_attendance_rule, 0)}</b> — a letter is enough for them</>} />}
        {t10 && <Kpi label="Top-10% outreach: needless contacts" value={num(t10.top_wasted_model)}
          vs={<><b>−{Math.round((1 - t10.top_wasted_model / t10.top_wasted_rule) * 100)}%</b> vs rule ({num(t10.top_wasted_rule)})</>} />}
        <Kpi label="Wasted invitations / year" value={num(wasted)} vs="sent 0–6 months after a screening" />
      </div>
      <div className="grid2">
        <Card title="Attendance drops with every further invitation">
          <RateBars rows={d.attendance_by.prior_invitations} />
        </Card>
        <Card title="Attendance by model risk decile (test 2024, unseen in training)">
          <BarChart data={d.deciles}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="decile" label={{ value: "risk decile (1 = lowest)", position: "insideBottom", offset: -2, fontSize: 12 }} />
            <YAxis tickFormatter={pctTick} />
            <Tooltip formatter={(v) => [pct(v), "Attendance"]} labelFormatter={(l) => `Decile ${l}`} />
            <Bar dataKey="attendance" radius={[4, 4, 0, 0]}>
              {d.deciles.map((r) => <Cell key={r.decile} fill={r.decile <= 2 ? GREEN : RED} />)}
            </Bar>
          </BarChart>
        </Card>
      </div>
      <p className="note">01 WHO → risk · 02 WHY → drivers · 03 WHAT → segments &amp; interventions · 04 HOW TO VERIFY → A/B experiment.
        Aggregates only; groups smaller than {d.meta.min_cell} are hidden.</p>
    </>
  );
}

function Who({ d }) {
  const t = d.targeting || [];
  const rq = Object.fromEntries((d.ranking_quality || []).map((r) => [r.scorer, r]));
  return (
    <>
      <h2 className="lead">01 WHO — who is most likely not to attend</h2>
      <div className="kpis">
        <Kpi label="Attendance, lowest-risk decile" value={pct(d.deciles[0].attendance)} />
        <Kpi label="Attendance, highest-risk decile" value={pct(d.deciles.at(-1).attendance)} />
        <Kpi label="ROC-AUC model" value={metric(d, "roc_auc").toFixed(3)}
          vs={<>rule {metric(d, "roc_auc", "baseline").toFixed(3)} · random 0.500</>} />
        {rq.model && <Kpi label="Average precision, attendance" value={rq.model.ap_attendance.toFixed(3)}
          vs={<>rule {rq.rule.ap_attendance.toFixed(3)} · random {rq.random.ap_attendance.toFixed(3)}</>} />}
      </div>
      <div className="card">
        <h3>Model vs. rule in people (test 2024)</h3>
        <table className="tbl">
          <thead><tr><th>Selected share</th><th>Lowest risk → attendance (model / rule)</th><th>Highest risk → needless contacts (model / rule)</th></tr></thead>
          <tbody>{t.map((r) => (
            <tr key={r.share}>
              <td>{pct(r.share, 0)} ({num(r.n)} women)</td>
              <td><span className="ok">{pct(r.bottom_attendance_model)}</span> / {pct(r.bottom_attendance_rule)}</td>
              <td><span className="ok">{num(r.top_wasted_model)}</span> / {num(r.top_wasted_rule)}</td>
            </tr>))}
          </tbody>
        </table>
      </div>
      {d.ranking_quality && (
        <div className="card">
          <h3>Ranking quality vs. a random score</h3>
          <table className="tbl">
            <thead><tr><th>Scorer</th><th className="n">ROC-AUC</th><th className="n">Average precision (attendance)</th></tr></thead>
            <tbody>{d.ranking_quality.map((r) => (
              <tr key={r.scorer}>
                <td>{{ random: "Random score", rule: "Rule: number of invitations", model: "Model (LightGBM)" }[r.scorer]}</td>
                <td className="n">{r.roc_auc.toFixed(3)}</td>
                <td className="n">{r.scorer === "model" ? <span className="ok">{r.ap_attendance.toFixed(3)}</span> : r.ap_attendance.toFixed(3)}</td>
              </tr>))}
            </tbody>
          </table>
          <p className="note">Average precision is reported for attendance, the 19% minority class: a random score gets the
            attendance rate. On non-attendance (81% of invitations) even a random score gets ~0.81.</p>
        </div>
      )}
      <div className="grid2">
        <Card title="ROC curve — test year 2024">
          <LineChart margin={{ right: 10 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" dataKey="fpr" domain={[0, 1]} tickFormatter={pctTick} />
            <YAxis type="number" domain={[0, 1]} tickFormatter={pctTick} />
            <Tooltip formatter={(v) => pct(v)} labelFormatter={(l) => `FPR ${pct(l)}`} />
            <Legend />
            <Line data={d.roc.model} dataKey="tpr" name="Model" stroke={RED} strokeWidth={3} dot={false} />
            <Line data={d.roc.baseline} dataKey="tpr" name="Rule" stroke={GREY} strokeWidth={3} dot={false} />
            <Line data={[{ fpr: 0, tpr: 0 }, { fpr: 1, tpr: 1 }]} dataKey="tpr" name="Random" stroke={LIGHT} strokeDasharray="4 4" dot={false} />
          </LineChart>
        </Card>
        <Card title="Attendance among the selected highest-risk women (lower = more precise)">
          <LineChart margin={{ right: 10 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" dataKey="top_share" domain={[0, 1]} tickFormatter={pctTick} />
            <YAxis tickFormatter={pctTick} />
            <Tooltip formatter={(v) => pct(v)} labelFormatter={(l) => `Top ${pct(l, 0)}`} />
            <Legend />
            <Line data={d.gain.model} dataKey="attendance_in_top" name="Model" stroke={RED} strokeWidth={3} />
            <Line data={d.gain.baseline} dataKey="attendance_in_top" name="Rule" stroke={GREY} strokeWidth={3} />
          </LineChart>
        </Card>
      </div>
    </>
  );
}

function Why({ d }) {
  const [key, setKey] = useState("prior_invitations");
  const [k, setK] = useState(10);
  const fi = d.feature_importance.slice(0, 12).map((r) => ({
    ...r, label: FEATURES[r.feature] || r.feature,
    color: r.direction === 1 ? RED : r.direction === -1 ? GREEN : GREY,
  }));
  const regions = [...d.attendance_by.region].sort((a, b) => a.attendance - b.attendance);
  const shown = [...regions.slice(0, k), ...regions.slice(-k)];
  return (
    <>
      <h2 className="lead">02 WHY — what non-attendance is associated with</h2>
      <div className="callout">Associations learned by the model (SHAP), not causes. Causal effects come from the experiment (04).
        <span style={{ color: RED }}> ■</span> higher value → higher risk <span style={{ color: GREEN }}> ■</span> higher value → lower risk
        <span style={{ color: GREY }}> ■</span> categorical</div>
      <Card title="Most important drivers (mean |SHAP|)" height={420}>
        <BarChart data={fi} layout="vertical" margin={{ left: 30, right: 20 }}>
          <CartesianGrid strokeDasharray="3 3" horizontal={false} />
          <XAxis type="number" />
          <YAxis type="category" dataKey="label" width={230} tick={{ fontSize: 12 }} />
          <Tooltip formatter={(v) => [v.toFixed(3), "mean |SHAP|"]} />
          <Bar dataKey="importance" radius={[0, 4, 4, 0]}>{fi.map((r) => <Cell key={r.feature} fill={r.color} />)}</Bar>
        </BarChart>
      </Card>
      <div className="card">
        <div className="controls">
          <label>Attendance by
            <select value={key} onChange={(e) => setKey(e.target.value)}>
              {Object.entries(BREAKDOWNS).map(([k2, v]) => <option key={k2} value={k2}>{v}</option>)}
            </select>
          </label>
        </div>
        <div style={{ height: 320 }}><ResponsiveContainer><RateBars rows={d.attendance_by[key]} /></ResponsiveContainer></div>
      </div>
      <div className="card">
        <div className="controls">
          <label>VZP territorial offices: lowest and highest {k} of {regions.length}
            <input type="range" min={5} max={20} value={k} onChange={(e) => setK(+e.target.value)} />
          </label>
        </div>
        <div style={{ height: 40 + 24 * shown.length }}><ResponsiveContainer><RateBars rows={shown} horizontal /></ResponsiveContainer></div>
        <p className="note">Not adjusted for age or invitation history — not proof of a regional barrier.</p>
      </div>
    </>
  );
}

function What({ d }) {
  const seg = d.segments.map((r) => ({ ...r, attendance: 1 - r.non_attendance, label: SEGMENTS[r.segment] || r.segment }))
    .sort((a, b) => a.attendance - b.attendance);
  const maxShare = Math.max(...seg.map((r) => r.share));
  const speed = ["3m", "6m", "12m"].map((w) => Object.fromEntries([["window", w],
    ...d.segment_response_speed.map((r) => [SEGMENTS[r.segment] || r.segment, r[w]])]));
  const palette = [RED, "#1f77b4", "#ff7f0e", GREEN, "#9467bd", "#8c564b", GREY];
  const since = d.attendance_by.months_since_last_screening.filter((r) => r.group !== "none_in_5y");
  const recent = d.recently_screened_per_year;
  return (
    <>
      <h2 className="lead">03 WHAT — segments and targeted support</h2>
      <div className="card">
        <h3>Segments (test 2024)</h3>
        <table className="tbl">
          <thead><tr><th>Segment</th><th className="n">Women</th><th style={{ width: 140 }}>Share</th><th className="n">Attendance</th><th>Proposed intervention</th></tr></thead>
          <tbody>{seg.map((r) => (
            <tr key={r.segment}>
              <td><b>{r.label}</b></td>
              <td className="n">{num(r.n)}</td>
              <td><div className="bar" style={{ width: `${(r.share / maxShare) * 100}%` }} title={pct(r.share)} /></td>
              <td className="n">{pct(r.attendance)}</td>
              <td>{r.intervention}</td>
            </tr>))}
          </tbody>
        </table>
      </div>
      <div className="callout"><b>High risk ≠ high effect.</b> The most expensive support (phone call, physician) goes where the experiment
        proves it works — not automatically to the highest-risk women.</div>
      <div className="grid2">
        <Card title="How fast women respond — when to send a reminder">
          <LineChart data={speed} margin={{ right: 10 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="window" />
            <YAxis tickFormatter={pctTick} />
            <Tooltip formatter={(v) => pct(v)} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            {d.segment_response_speed.map((r, i) => (
              <Line key={r.segment} dataKey={SEGMENTS[r.segment] || r.segment} stroke={palette[i % palette.length]} strokeWidth={2} />
            ))}
          </LineChart>
        </Card>
        <Card title="Quick win: attendance by months since last screening">
          <RateBars rows={since} />
        </Card>
      </div>
      <div className="card">
        <h3>Invitations sent 0–6 months after a screening</h3>
        <ul className="points">
          <li><b>{num(recent.reduce((s, r) => s + r.n, 0) / recent.length)} per year</b>, attendance ~2%</li>
          <li>half of them were invited a year earlier and <b>94% of those attended</b> — late, after 11–12 months</li>
          <li>the yearly cycle probably does not see the fresh screening yet (claims reporting lag) — <i>hypothesis</i></li>
          <li><b>Proposal:</b> check claims right before sending, or postpone the repeat invitation</li>
        </ul>
      </div>
    </>
  );
}

function Verify({ d }) {
  const seg = d.segments.map((r) => ({ ...r, attendance: 1 - r.non_attendance, label: SEGMENTS[r.segment] || r.segment }));
  const [segment, setSegment] = useState("repeated_nonresponder");
  const row = seg.find((r) => r.segment === segment) || seg[0];
  const [p0, setP0] = useState(row.attendance);
  const [mde, setMde] = useState(2);
  const [power, setPower] = useState(0.8);
  useEffect(() => setP0(+row.attendance.toFixed(3)), [segment]);
  const n = nPerGroup(p0, mde / 100, 0.05, power);
  const design = useMemo(() => {
    const by = {};
    for (const r of d.experiment_design) (by[r.segment] ??= {})[r.mde_pp] = r.n_per_arm;
    return by;
  }, [d]);
  const mdes = [...new Set(d.experiment_design.map((r) => r.mde_pp))].sort((a, b) => a - b);
  return (
    <>
      <h2 className="lead">04 HOW TO VERIFY — randomised experiment</h2>
      <div className="card">
        <ul className="points">
          <li><b>Control:</b> standard invitation · <b>Treatment:</b> the segment's intervention</li>
          <li><b>Randomisation unit:</b> the woman; strata = segment × risk quintile</li>
          <li><b>Primary metric:</b> attendance within 12 months (intention-to-treat) · <b>early signal:</b> 3 months</li>
          <li>Results → uplift model: who the intervention actually helps</li>
        </ul>
      </div>
      <div className="card">
        <h3>Sample size calculator</h3>
        <div className="controls">
          <label>Segment
            <select value={segment} onChange={(e) => setSegment(e.target.value)}>
              {seg.map((r) => <option key={r.segment} value={r.segment}>{r.label}</option>)}
            </select>
          </label>
          <label>Baseline attendance
            <input type="number" min={0.001} max={0.999} step={0.005} value={p0} onChange={(e) => setP0(+e.target.value)} />
          </label>
          <label>Expected effect: {mde} pp
            <input type="range" min={0.5} max={10} step={0.5} value={mde} onChange={(e) => setMde(+e.target.value)} />
          </label>
          <label>Power
            <select value={power} onChange={(e) => setPower(+e.target.value)}>
              {[0.7, 0.8, 0.9].map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
          </label>
        </div>
        {n == null ? <p className="bad">Invalid parameters.</p> : (
          <div className="kpis">
            <Kpi label="Women per arm" value={num(n)} />
            <Kpi label="Total (control + treatment)" value={num(2 * n)} />
            <Kpi label="Segment size (2024)" value={num(row.n)}
              vs={2 * n <= row.n ? <span className="ok">enough in one year</span> : <span className="bad">one year is not enough</span>} />
          </div>
        )}
      </div>
      <div className="card">
        <h3>Women per arm by expected effect (α = 0.05, power 0.8)</h3>
        <table className="tbl">
          <thead><tr><th>Segment</th>{mdes.map((m) => <th key={m} className="n">{m} pp</th>)}</tr></thead>
          <tbody>{Object.entries(design).map(([s, v]) => (
            <tr key={s}><td>{SEGMENTS[s] || s}</td>{mdes.map((m) => <td key={m} className="n">{num(v[m])}</td>)}</tr>))}
          </tbody>
        </table>
      </div>
    </>
  );
}

// ------------------------------------------------------------------------------------- app

export const TABS = [["Overview", Overview], ["01 WHO", Who], ["02 WHY", Why], ["03 WHAT", What], ["04 HOW TO VERIFY", Verify]];

export default function App() {
  const [d, setD] = useState(null);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState(0);
  useEffect(() => {
    fetch("./data.json").then((r) => (r.ok ? r.json() : Promise.reject(r.statusText)))
      .then(setD).catch((e) => setError(String(e)));
  }, []);
  if (error) return <div className="shell"><p className="bad">Cannot load data.json: {error}. Run <code>npm run data</code>.</p></div>;
  if (!d) return <div className="shell"><p className="note">Loading…</p></div>;
  const Page = TABS[tab][1];
  return (
    <div className="shell">
      <header className="top">
        <div>
          <h1>Who will not attend mammography screening</h1>
          <div className="sub">Rakathon 2026 · VZP data {d.meta.years[0]}–{d.meta.years.at(-1)} · test year {d.meta.test_year} ·
            aggregates only · generated {d.meta.generated_at}</div>
        </div>
      </header>
      <nav className="tabs">
        {TABS.map(([name], i) => <button key={name} className={i === tab ? "on" : ""} onClick={() => setTab(i)}>{name}</button>)}
      </nav>
      <Page d={d} />
    </div>
  );
}
