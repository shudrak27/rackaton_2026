import React, { useMemo, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Line, LineChart, ReferenceLine, Scatter, ScatterChart,
  Tooltip, XAxis, YAxis,
} from "recharts";
import { Badge, Chart, ChartTooltip, Kpi, LegendItem, Panel, Table } from "./components.jsx";
import { num, pct } from "./labels.js";
import {
  benchmarks, calibrationRows, capacityRows, finite, groupRows, metric, rocPoints, testPrevalence,
} from "./technical-data.js";

const INDIGO = "#626cf0", TEAL = "#55bca8", CORAL = "#ec858b", GREY = "#a6adc4";
const AXIS = { axisLine: false, tickLine: false, tick: { fontSize: 12 }, tickMargin: 8 };
const GRID = { stroke: "#eef0f6", strokeDasharray: "4 4" };
const RANGE = [0, 1], TICKS = [0, .25, .5, .75, 1];
const percentTick = (value) => `${Math.round(value * 100)}%`;
const decimal = (value, digits = 3) => finite(value) ? value.toFixed(digits) : "—";
const percent = (value, digits = 1) => finite(value) ? pct(value, digits) : "—";
const signedPoints = (value) => finite(value) ? `${value > 0 ? "+" : ""}${(value * 100).toFixed(1)} pp` : "—";
const testLabel = (d) => d.meta?.test_year ? `Test invitations · ${d.meta.test_year}` : "Held-out test invitations";
const noMarker = () => null;

function Empty({ children = "This result is not included in the current data export." }) {
  return <p className="technical-empty">{children}</p>;
}

function CurveTooltip({ active, payload, mode = "roc" }) {
  if (!active || !payload?.length) return null;
  const row = payload[0].payload;
  return <div className="chart-tooltip">
    <div className="tooltip-label">{row.series || "Model"}</div>
    {mode === "roc" ? <>
      <div className="tooltip-row"><span>False positive rate</span><strong>{percent(row.fpr)}</strong></div>
      <div className="tooltip-row"><span>True positive rate</span><strong>{percent(row.tpr)}</strong></div>
    </> : <>
      <div className="tooltip-row"><span>Predicted non-attendance</span><strong>{percent(row.predicted)}</strong></div>
      <div className="tooltip-row"><span>Observed non-attendance</span><strong>{percent(row.observed)}</strong></div>
      <div className="tooltip-count">{num(row.n)} invitations · {row.bin}</div>
    </>}
  </div>;
}

function RocPlot({ d }) {
  const model = rocPoints(d.roc?.model, "Model"), baseline = rocPoints(d.roc?.baseline, "Baseline");
  if (!model.length && !baseline.length) return <Empty />;
  return <>
    <Chart height={310} label="ROC curve comparing model and baseline on the held-out test year">
      <ScatterChart margin={{ top: 12, right: 20, bottom: 8, left: 0 }}>
        <CartesianGrid {...GRID} />
        <XAxis {...AXIS} type="number" dataKey="fpr" domain={RANGE} ticks={TICKS} tickFormatter={percentTick} />
        <YAxis {...AXIS} type="number" dataKey="tpr" domain={RANGE} ticks={TICKS} tickFormatter={percentTick} width={56} />
        <ReferenceLine segment={[{ x: 0, y: 0 }, { x: 1, y: 1 }]} stroke={GREY} strokeDasharray="5 5" />
        <Tooltip content={<CurveTooltip />} />
        {baseline.length > 0 && <Scatter name="Baseline" data={baseline} fill={CORAL} line={{ stroke: CORAL, strokeWidth: 2.5 }} shape={noMarker} isAnimationActive={false} />}
        {model.length > 0 && <Scatter name="Model" data={model} fill={INDIGO} line={{ stroke: INDIGO, strokeWidth: 2.5 }} shape={noMarker} isAnimationActive={false} />}
      </ScatterChart>
    </Chart>
    <div className="inline-legend"><LegendItem color={INDIGO}>Model</LegendItem><LegendItem color={CORAL}>Baseline</LegendItem><LegendItem color={GREY}>Chance</LegendItem></div>
    <div className="chart-caption">X: attenders incorrectly flagged. Y: non-attenders captured. A curve nearer the top-left ranks risk better.</div>
  </>;
}

function Capacity({ d }) {
  const rows = useMemo(() => capacityRows(d), [d]);
  const [share, setShare] = useState(.1);
  const selected = rows.find((row) => Math.abs(row.share - share) < 1e-7) || rows[0];
  const prevalence = testPrevalence(d).nonAttendance;
  return <Panel title="Precision at outreach capacity" subtitle="Positive class: non-attendance" footer="Precision is the share who did not attend among the selected invitations. Recall is the share of all non-attenders captured; neither measures the effect of a call.">
    {!selected ? <Empty /> : <>
      <div className="controls panel-controls technical-controls"><label className="field">Select highest-risk invitations
        <select aria-label="Outreach capacity" value={selected.share} onChange={(e) => setShare(Number(e.target.value))}>
          {rows.map((row) => <option key={row.share} value={row.share}>Top {percent(row.share, 0)}</option>)}
        </select></label></div>
      <Chart height={215} label="Precision among the highest-risk invitations as outreach capacity increases">
        <LineChart data={rows} margin={{ top: 8, right: 20, left: 0, bottom: 8 }}>
          <CartesianGrid {...GRID} /><XAxis {...AXIS} type="number" dataKey="share" domain={RANGE} ticks={TICKS} tickFormatter={percentTick} />
          <YAxis {...AXIS} domain={RANGE} ticks={TICKS} tickFormatter={percentTick} width={56} />
          <Tooltip content={<ChartTooltip labelFormat={(value) => `Top ${percent(value, 0)} by risk`} />} />
          {finite(prevalence) && <ReferenceLine y={prevalence} stroke={GREY} strokeDasharray="5 5" />}
          <ReferenceLine x={selected.share} stroke={GREY} strokeDasharray="3 3" />
          <Line type="linear" dataKey="modelPrecision" name="Model precision" stroke={INDIGO} strokeWidth={2.5} dot={false} isAnimationActive={false} />
          <Line type="linear" dataKey="baselinePrecision" name="Baseline precision" stroke={CORAL} strokeWidth={2.5} dot={false} isAnimationActive={false} />
        </LineChart>
      </Chart>
      <div className="inline-legend"><LegendItem color={INDIGO}>Model</LegendItem><LegendItem color={CORAL}>Baseline</LegendItem><LegendItem color={GREY}>Chance precision</LegendItem></div>
      <Table label="Precision and recall at the selected capacity"><thead><tr><th>Top {percent(selected.share, 0)}</th><th className="n">Model</th><th className="n">Baseline</th></tr></thead>
        <tbody><tr><td>Precision</td><td className="n"><strong>{percent(selected.modelPrecision)}</strong></td><td className="n">{percent(selected.baselinePrecision)}</td></tr>
          <tr><td>Recall</td><td className="n">{percent(selected.modelRecall)}</td><td className="n">{percent(selected.baselineRecall)}</td></tr></tbody></Table>
    </>}
  </Panel>;
}

export function ModelQuality({ d }) {
  const rows = benchmarks(d), model = rows[2], baseline = rows[1];
  return <>
    <div className="kpis technical-kpis">
      <Kpi label="ROC-AUC" value={decimal(model.auc)} detail={`Baseline ${decimal(baseline.auc)} · chance 0.500`} icon="chart" highlight />
      <Kpi label="AP · non-attendance" value={decimal(model.apNonAttendance)} detail={`Baseline ${decimal(baseline.apNonAttendance)} · chance ${decimal(rows[0].apNonAttendance)}`} icon="target" />
      <Kpi label="AP · attendance" value={decimal(model.apAttendance)} detail={`Baseline ${decimal(baseline.apAttendance)} · chance ${decimal(rows[0].apAttendance)}`} icon="people" tone="teal" />
      <Kpi label="Test invitations" value={finite(d.meta?.n_test) ? num(d.meta.n_test) : "—"} detail={testLabel(d)} icon="calendar" tone="amber" />
    </div>
    <div className="grid2"><Panel title="ROC curve" subtitle={testLabel(d)}><RocPlot d={d} /></Panel><Capacity d={d} /></div>
    <Panel title="Model vs baseline" subtitle="Same test invitations, two ways to rank risk" className="section-gap"
      footer="AP means average precision across ranking thresholds, not the percentage of correct predictions. Its chance level changes with the positive class; the high non-attendance rate makes that AP easier to achieve.">
      <Table label="Ranking benchmarks for both positive classes"><thead><tr><th>Scorer</th><th className="n">ROC-AUC</th><th className="n">AP · non-attendance</th><th className="n">AP · attendance</th></tr></thead>
        <tbody>{rows.map((row) => <tr key={row.scorer}><td><strong>{row.scorer}</strong></td><td className="n">{decimal(row.auc)}</td><td className="n">{decimal(row.apNonAttendance)}</td><td className="n">{decimal(row.apAttendance)}</td></tr>)}</tbody></Table>
    </Panel>
    <div className="grid2">
      <Panel title="What is the baseline?" action={<Badge tone="neutral">REFERENCE RULE</Badge>}>
        <div className="panel-body technical-explainer"><p>Higher risk for more previous invitations, with a small adjustment for screening history.</p>
          <p><code>score = previous invitations − 0.1 × screening codes in the last 5 years</code></p>
          <p>Counts are measured before the current invitation; missing counts become zero. This is a ranking score, not a probability or a documented VZP operating rule.</p></div>
      </Panel>
      <Panel title="Why no single accuracy number?" action={<Badge tone="neutral">THRESHOLD MATTERS</Badge>}>
        <div className="panel-body technical-explainer"><p>The model returns a risk score. Accuracy, sensitivity and a confusion matrix require a chosen decision threshold.</p>
          <p>For a limited outreach team, choosing the highest-risk fraction gives a practical threshold. The precision and recall above show the trade-off.</p>
          <p>ROC-AUC measures ranking; calibration checks whether the risk percentages are reliable.</p></div>
      </Panel>
    </div>
  </>;
}

export function Calibration({ d }) {
  const rows = useMemo(() => calibrationRows(d), [d]);
  const count = rows.reduce((sum, row) => sum + row.n, 0);
  const predicted = count ? rows.reduce((sum, row) => sum + row.n * row.predicted, 0) / count : null;
  const observed = count ? rows.reduce((sum, row) => sum + row.n * row.observed, 0) / count : null;
  const deciles = (d.deciles || []).filter((row) => finite(row.non_attendance) && finite(row.mean_score));
  return <>
    <div className="kpis technical-kpis">
      <Kpi label="Brier score" value={decimal(metric(d, "brier"), 4)} detail="Mean squared probability error · lower is better" icon="target" />
      <Kpi label="Log loss" value={decimal(metric(d, "log_loss"), 4)} detail="Penalises confident mistakes · lower is better" icon="chart" />
      <Kpi label="Mean predicted risk" value={percent(predicted)} detail="Weighted across exported probability bins" icon="activity" />
      <Kpi label="Observed non-attendance" value={percent(observed)} detail="Actual rate in the same exported bins" icon="people" tone="teal" />
    </div>
    <div className="grid2">
      <Panel title="Do predicted risks match reality?" subtitle="Non-attendance within 12 months" footer="Each point is one probability bin. Above the diagonal: risk is underestimated. Below it: risk is overestimated. Small bins are less stable.">
        {!rows.length ? <Empty /> : <>
          <Chart height={315} label="Mean predicted and observed non-attendance in each probability bin"><ScatterChart margin={{ top: 12, right: 20, bottom: 8, left: 0 }}>
            <CartesianGrid {...GRID} />
            <XAxis {...AXIS} type="number" dataKey="predicted" domain={RANGE} ticks={TICKS} tickFormatter={percentTick} />
            <YAxis {...AXIS} type="number" dataKey="observed" domain={RANGE} ticks={TICKS} tickFormatter={percentTick} width={56} />
            <ReferenceLine segment={[{ x: 0, y: 0 }, { x: 1, y: 1 }]} stroke={GREY} strokeDasharray="5 5" />
            <Tooltip content={<CurveTooltip mode="calibration" />} />
            <Scatter name="Model" data={rows} fill={INDIGO} line={{ stroke: INDIGO, strokeWidth: 2 }} isAnimationActive={false} />
          </ScatterChart></Chart>
          <div className="inline-legend"><LegendItem color={INDIGO}>Model</LegendItem><LegendItem color={GREY}>Perfect agreement</LegendItem></div>
          <div className="chart-caption">X: predicted risk. Y: observed non-attendance.</div>
        </>}
      </Panel>
      <Panel title="Where the predictions fall" subtitle="Invitation count in each probability bin" footer="These counts show how much evidence sits behind each calibration point. Bins with no exported observations are omitted.">
        {!rows.length ? <Empty /> : <Chart height={315} label="Number of invitations per predicted non-attendance probability bin"><BarChart data={rows} margin={{ top: 12, right: 20, left: 8, bottom: 8 }}>
          <CartesianGrid {...GRID} vertical={false} /><XAxis {...AXIS} dataKey="predicted" tickFormatter={percentTick} interval="preserveStartEnd" />
          <YAxis {...AXIS} width={64} tickFormatter={(value) => value >= 1000 ? `${Math.round(value / 1000)}k` : value} />
          <Tooltip content={<ChartTooltip format={num} labelFormat={(value) => `Mean risk ${percent(value)}`} />} />
          <Bar dataKey="n" name="Invitations" fill={INDIGO} radius={[4, 4, 0, 0]} maxBarSize={42} isAnimationActive={false} />
        </BarChart></Chart>}
      </Panel>
    </div>
    <div className="grid2">
      <Panel title="Before and after calibration" subtitle="Saved test metrics · lower is better" footer="Calibration adjusts probabilities. The baseline is an uncalibrated count-based score, so Brier score and log loss are not compared with it.">
        <Table label="Raw and final model probability errors"><thead><tr><th>Metric</th><th className="n">Before</th><th className="n">Final model</th></tr></thead><tbody>
          {[["brier", "Brier score"], ["log_loss", "Log loss"]].map(([key, label]) => <tr key={key}><td>{label}</td><td className="n">{decimal(metric(d, key, "model_uncalibrated"), 5)}</td><td className="n"><strong>{decimal(metric(d, key), 5)}</strong></td></tr>)}
        </tbody></Table>
        <div className="panel-body technical-explainer"><p>Calibration, when enabled, is fitted on a recent part of the training data. The test year remains separate.</p><p>A dash means that result was not exported.</p></div>
      </Panel>
      <Panel title="Risk deciles" subtitle="Ten similarly sized groups, from low to high predicted risk" footer="Decile 1 is lowest risk; decile 10 is highest. The model is useful when observed non-attendance rises with the risk group.">
        {!deciles.length ? <Empty /> : <Chart height={265} label="Predicted and observed non-attendance across risk deciles"><LineChart data={deciles} margin={{ top: 12, right: 20, left: 0, bottom: 8 }}>
          <CartesianGrid {...GRID} /><XAxis {...AXIS} dataKey="decile" /><YAxis {...AXIS} width={56} domain={RANGE} ticks={TICKS} tickFormatter={percentTick} />
          <Tooltip content={<ChartTooltip labelFormat={(value) => `Risk decile ${value}`} showCount />} />
          <Line dataKey="mean_score" name="Predicted risk" stroke={INDIGO} strokeWidth={2.5} dot={{ r: 3 }} isAnimationActive={false} />
          <Line dataKey="non_attendance" name="Observed non-attendance" stroke={TEAL} strokeWidth={2.5} dot={{ r: 3 }} isAnimationActive={false} />
        </LineChart></Chart>}
        <div className="inline-legend"><LegendItem color={INDIGO}>Predicted</LegendItem><LegendItem color={TEAL}>Observed</LegendItem></div>
      </Panel>
    </div>
  </>;
}

const PROTOCOL = [
  ["Features at invitation", "Use information available before the letter. Exclude identifiers and post-invitation outcomes from model inputs."],
  ["Search within training data", "FLAML, when enabled, searches model families. Optuna tunes LightGBM with early stopping."],
  ["Compare on shared folds", "Candidate models compete on the same client-grouped folds. A woman stays in one fold during cross-validation."],
  ["Fit and calibrate", "Refit the selected candidate. If enabled, reserve the most recent training period for calibration."],
  ["Evaluate a later year", "Compare model and baseline on the same held-out invitation year. Keep it separate from model selection."],
];

export function Validation({ d }) {
  const keys = Object.keys(d.fairness || {}).filter((key) => Array.isArray(d.fairness[key]) && d.fairness[key].length);
  const [group, setGroup] = useState("age_band"), [showAll, setShowAll] = useState(false);
  const chosen = keys.includes(group) ? group : keys[0];
  const rows = groupRows(d, chosen), visible = showAll ? rows : rows.slice(0, 12);
  const groupName = (key) => ({ age_band: "Age band", region: "Territorial office" })[key] || key;
  const prevalence = testPrevalence(d);
  return <>
    <div className="kpis technical-kpis">
      <Kpi label="Dataset invitations" value={finite(d.meta?.n_invitations) ? num(d.meta.n_invitations) : "—"} detail={d.meta?.years?.length ? `Dataset years ${d.meta.years.join(", ")}` : "Years not recorded"} icon="mail" />
      <Kpi label="Unique women" value={finite(d.meta?.n_clients) ? num(d.meta.n_clients) : "—"} detail="Across the complete exported dataset" icon="people" tone="teal" />
      <Kpi label="Test invitations" value={finite(d.meta?.n_test) ? num(d.meta.n_test) : "—"} detail={testLabel(d)} icon="calendar" />
      <Kpi label="Test class balance" value={percent(prevalence.nonAttendance)} detail={`Non-attendance · attendance ${percent(prevalence.attendance)}`} icon="chart" tone="amber" />
    </div>
    <div className="grid2">
      <Panel title="How validation is designed" subtitle="Protocol implemented in this project">
        <ol className="technical-steps">{PROTOCOL.map(([title, body]) => <li key={title}><strong>{title}</strong><p>{body}</p></li>)}</ol>
      </Panel>
      <Panel title="What this test establishes" subtitle="Scope and limits of the evidence">
        <div className="panel-body technical-explainer">
          <p><strong>Target:</strong> no recorded mammography screening within 12 months of the invitation. This is one target, not four monthly models.</p>
          <p><strong>Time split:</strong> the test uses a later invitation year. The pipeline supports a gap before it so training outcomes have time to mature.</p>
          <p><strong>Returning women:</strong> a woman may appear in earlier training years and the test year. This checks future invitations, not exclusively new clients.</p>
          <p><strong>Population:</strong> this VZP extract covers women continuously insured since 2015 under the supplied eligibility criteria. Results do not automatically generalise to other populations.</p>
          <p><strong>Run details:</strong> this export contains aggregate results. Consult the saved training run for the selected model, fold scores, dates and search settings.</p>
          <p><strong>Next check:</strong> group differences and probability drift need monitoring. An A/B test is still needed to measure the effect of outreach.</p>
        </div>
      </Panel>
    </div>
    <Panel title="Performance across groups" subtitle={testLabel(d)} className="section-gap"
      footer="Gap = mean predicted risk minus observed non-attendance. These are descriptive group checks, not proof of fairness; different sample sizes and histories affect comparisons.">
      {!rows.length ? <Empty /> : <>
        <div className="controls panel-controls technical-controls"><label className="field">Compare groups
          <select aria-label="Validation group" value={chosen} onChange={(event) => { setGroup(event.target.value); setShowAll(false); }}>
            {keys.map((key) => <option key={key} value={key}>{groupName(key)}</option>)}
          </select></label><span>{rows.length > 12 && !showAll ? "12 largest groups by invitation count" : `${rows.length} exported groups`}</span>
          {rows.length > 12 && <button className="text-button" onClick={() => setShowAll(!showAll)}>{showAll ? "Show largest 12" : `Show all ${rows.length}`}</button>}
        </div>
        <Table label="Model performance and calibration by group"><thead><tr><th>{groupName(chosen)}</th><th className="n">Invitations</th><th className="n">ROC-AUC</th><th className="n">Observed risk</th><th className="n">Predicted risk</th><th className="n">Gap</th></tr></thead><tbody>
          {visible.map((row) => <tr key={row.label}><td><strong>{row.label}</strong></td><td className="n">{num(row.n)}</td><td className="n">{decimal(row.roc_auc)}</td><td className="n">{percent(row.non_attendance)}</td><td className="n">{percent(row.mean_risk)}</td><td className="n">{signedPoints(row.gap)}</td></tr>)}
        </tbody></Table>
        {finite(d.meta?.min_cell) && <div className="chart-caption">Groups below {d.meta.min_cell} invitations are suppressed in the dashboard export. No confidence intervals are included here.</div>}
      </>}
    </Panel>
  </>;
}
