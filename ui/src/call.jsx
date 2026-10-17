import React, { useState } from "react";
import { CartesianGrid, Line, LineChart, Tooltip, XAxis, YAxis } from "recharts";
import { Badge, Chart, ChartTooltip, Icon, Panel } from "./components.jsx";
import { SEGMENTS, num, pct } from "./labels.js";

// Who to call when calls are limited: plain-language portraits from data.json `personas`.

const INDIGO = "#5863ed", CORAL = "#ec858b", GREY = "#b4bbcf";
const AXIS = { axisLine: false, tickLine: false, tick: { fontSize: 12 }, tickMargin: 8 };
const pctTick = (v) => `${Math.round(v * 100)}%`;
const times = (v) => v == null ? "–" : v === 0 ? "first invitation" : `${Math.round(v)} times before`;
// small shares keep one decimal (1.8%, not 2%)
const share = (v) => pct(v, v != null && v < 0.1 ? 1 : 0);

// Each trait: icon, question, how to say it for one persona (and, optionally, for the average).
const TRAITS = [
  ["calendar", "Age", (p) => p.top_age_band ? `mostly ${p.top_age_band}` : "–", (p) => p.top_age_band],
  ["mail", "Invited before", (p) => times(p.median_prior_invitations)],
  ["doctor", "Doctor visits last year", (p) => p.median_contacts_12m == null ? "–" : `${Math.round(p.median_contacts_12m)}`],
  ["people", "No gynaecologist check-up (2 years)", (p) => pct(p.no_gyn_checkup_24m, 0)],
  ["shield", "No other cancer screening (3 years)", (p) => pct(p.no_other_screening_36m, 0)],
  ["activity", "No dental check-up (2 years)", (p) => pct(p.no_dental_checkup_24m, 0)],
];

function PersonaCard({ title, tone, icon, persona, headline, everyone }) {
  return <section className={`persona persona-${tone}`}>
    <div className="persona-top">
      <span className="persona-avatar"><Icon name={icon} size={30} /></span>
      <div><h2>{title}</h2><p>{num(persona.n)} women · mostly “{SEGMENTS[persona.top_segment] || persona.top_segment}”</p></div>
    </div>
    <div className="persona-headline"><strong>{share(persona.attendance)}</strong><span>{headline}</span></div>
    <ul className="persona-traits">{TRAITS.map(([ic, label, say, sayAvg = say]) => <li key={label}>
      <Icon name={ic} size={17} /><span className="trait-label">{label}</span>
      <strong>{say(persona)}</strong>{everyone && <small>avg {sayAvg(everyone)}</small>}
    </li>)}</ul>
  </section>;
}

export function WhoToCall({ d }) {
  const p = d.personas;
  const [share, setShare] = useState(0.1);
  if (!p) return <p className="result-error">Re-run <code>python -m screening export-ui</code> to add the portraits.</p>;
  const call = p.call.find((c) => c.share === share) || p.call[0];
  const t = (d.targeting || []).find((r) => Math.abs(r.share - share) < 1e-9);
  const auc = d.test_metrics.find((r) => r.metric === "roc_auc");
  return <>
    <div className="capacity">
      <span className="capacity-label">VZP can call</span>
      <div className="capacity-options" role="radiogroup" aria-label="Call capacity">
        {p.call.map((c) => <button key={c.share} role="radio" aria-checked={c.share === share}
          className={c.share === share ? "on" : ""} onClick={() => setShare(c.share)}>{pct(c.share, 0)}</button>)}
      </div>
      <span className="capacity-note">of invited women = <strong>{num(call.n)} calls</strong> a year</span>
    </div>

    <div className="persona-grid">
      <PersonaCard title="Call her" tone="call" icon="phone" persona={call} everyone={p.everyone}
        headline="come with the letter alone" />
      <PersonaCard title="A letter is enough" tone="letter" icon="mail" persona={p.letter_enough}
        headline="come with the letter alone" />
    </div>
    <p className="persona-caveat"><Icon name="info" size={15} />The call goes to women who will almost certainly not come otherwise.
      Whether the call changes that is what the pilot measures (04).</p>

    <div className="grid2">
      <Panel title="Why the model, not a simple rule?" subtitle={`Calling the highest-risk ${pct(share, 0)}`}>
        {t && <div className="versus">
          {[["Our model", t.top_wasted_model, INDIGO], ["Rule: “invited many times”", t.top_wasted_rule, GREY]].map(([name, v, color]) =>
            <div className="versus-row" key={name}><span>{name}</span>
              <div className="versus-bar"><i style={{ width: `${100 * v / t.top_wasted_rule}%`, background: color }} /></div>
              <strong>{num(v)}</strong></div>)}
          <p className="versus-note">calls wasted on women who would have come anyway ·
            <b> {pct(1 - t.top_wasted_model / t.top_wasted_rule, 0)} fewer</b> with the model</p>
        </div>}
      </Panel>
      <Panel title="How well it ranks women" subtitle="Tested on 2024 — data the model never saw" action={<Badge tone="teal">AUC {auc?.model.toFixed(2)}</Badge>}>
        <Chart height={230} label="ROC curve of the model, the rule and a coin flip"><LineChart margin={{ top: 6, right: 18, left: -10, bottom: 6 }}>
          <CartesianGrid stroke="#eef0f6" strokeDasharray="4 4" />
          <XAxis {...AXIS} type="number" dataKey="fpr" domain={[0, 1]} tickFormatter={pctTick} />
          <YAxis {...AXIS} type="number" domain={[0, 1]} tickFormatter={pctTick} />
          <Tooltip content={<ChartTooltip labelFormat={(v) => `Wrongly flagged: ${pct(v)}`} />} />
          <Line data={d.roc.model} dataKey="tpr" name="Model" stroke={INDIGO} strokeWidth={3} dot={false} isAnimationActive={false} />
          <Line data={d.roc.baseline} dataKey="tpr" name="Rule" stroke={CORAL} strokeWidth={2} dot={false} isAnimationActive={false} />
          <Line data={[{ fpr: 0, tpr: 0 }, { fpr: 1, tpr: 1 }]} dataKey="tpr" name="Coin flip" stroke={GREY} strokeDasharray="5 5" dot={false} isAnimationActive={false} />
        </LineChart></Chart>
        <div className="chart-caption"><span className="key key-model" />Model {auc?.model.toFixed(2)}
          <span className="key key-rule" />Rule {auc?.baseline.toFixed(2)} <span className="key key-coin" />Coin flip 0.50 · higher curve = better</div>
      </Panel>
    </div>
  </>;
}
