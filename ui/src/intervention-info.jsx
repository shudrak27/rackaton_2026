import React, { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Badge, Icon } from "./components.jsx";
import { PLAYBOOKS } from "./interventions.js";
import { num, pct } from "./labels.js";

export function InterventionActions({ segment, d }) {
  const [view, setView] = useState(null);
  const play = PLAYBOOKS[segment];
  if (!play) return null;
  return <>
    <span className="intervention-actions">
      <button className="intervention-action" aria-label={`Use case: ${play.title}`} aria-haspopup="dialog" onClick={() => setView("case")}>
        <Icon name="people" size={15} />Use case
      </button>
      <button className="intervention-action" aria-label={`A/B test: ${play.title}`} aria-haspopup="dialog" onClick={() => setView("test")}>
        <Icon name="flask" size={15} />A/B test
      </button>
    </span>
    {view && <InterventionDialog segment={segment} d={d} view={view} onClose={() => setView(null)} />}
  </>;
}

function InterventionDialog({ segment, d, view, onClose }) {
  const ref = useRef(null);
  const play = PLAYBOOKS[segment];
  const row = d.segments.find((r) => r.segment === segment);
  const plan = d.experiment_design?.find((r) => r.segment === segment && r.mde_pp === 2);
  function close(e) {
    e?.preventDefault();
    ref.current?.close();
    onClose();
  }
  useEffect(() => {
    const dialog = ref.current;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    dialog.showModal();
    return () => { dialog.close(); document.body.style.overflow = previousOverflow; };
  }, []);
  return createPortal(<dialog ref={ref} className="intervention-dialog" aria-labelledby="intervention-title" onCancel={close}
    onClick={(e) => {
      if (e.target !== ref.current) return;
      const r = ref.current.getBoundingClientRect();
      if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) close();
    }}>
    <div className="intervention-dialog-top">
      <span className="action-icon"><Icon name={play.icon} size={25} /></span>
      <div><div className="dialog-labels"><Badge tone={play.tone}>{play.status}</Badge><span>{view === "case" ? "USE CASE" : "A/B TEST"}</span></div><h2 id="intervention-title">{play.title}</h2><p>{play.audience}</p></div>
      <button className="icon-button" aria-label="Close intervention details" onClick={close} autoFocus><Icon name="close" /></button>
    </div>
    <div className="intervention-dialog-body">
      {view === "case" ? <>
        <div className="case-evidence"><Badge tone="teal">OBSERVED · {d.meta.test_year}</Badge>
          <p><strong>{num(row?.n)} women</strong><span>·</span><strong>{pct(row ? 1 - row.non_attendance : null, 2)} attended</strong> within 12 months</p>
          <small>{play.definition}</small>
        </div>
        <h3 className="detail-label">What happens</h3>
        <div className="journey">{play.steps.map(([icon, title, body], i) => <div className="journey-step" key={title}>
          <div className="journey-symbol"><Icon name={icon} size={22} /><span>{i + 1}</span></div><h4>{title}</h4><p>{body}</p>
        </div>)}</div>
        <div className="case-example"><span><Icon name={play.icon} size={16} />{play.pilot ? "Draft wording" : "Example workflow"}</span><p>“{play.example}”</p></div>
        <div className="case-rationale"><h3>Why</h3><p>{play.why}</p></div>
        <details className="readiness"><summary>Before launch <Icon name="down" size={15} /></summary><p>{play.readiness}</p></details>
      </> : <>
        <Badge tone="amber">{play.pilot ? "PROPOSED · NO TRIAL RESULTS" : "NOT AN OUTREACH PILOT"}</Badge>
        <h3 className="trial-question">{play.question}</h3>
        {play.pilot ? <>
          <div className="trial-arms"><div><span className="arm-letter">A</span><h4>Control</h4><p>Standard invitation.</p></div>
            <div><span className="arm-letter treatment">B</span><h4>Additional support</h4><p>{play.treatment}</p></div></div>
          <div className="trial-facts"><div><small>Primary outcome</small><strong>Screened within 12 months</strong></div><div><small>Effect to detect · assumption</small><strong>+2 percentage points</strong></div>
            <div><small>Reference baseline</small><strong>{pct(row ? 1 - row.non_attendance : null, 2)} attendance</strong></div>
            <div><small>{segment === "care_no_prevention" ? "Individual-randomization reference" : "Required per arm"}</small><strong>{num(plan?.n_per_arm)} women</strong></div></div>
          <p className="trial-method">Randomize 1:1 within risk groups. Include unreachable women in their assigned arm. Planning: 80% power; two-sided α = 0.05.</p>
          {segment === "care_no_prevention" && <p className="trial-caution">If entire practices are randomized, recalculate the sample size for clustering.</p>}
          <div className="success-rule"><Icon name="target" size={20} /><div><strong>Decision after 12 months</strong><p>Report B − A attendance with a 95% confidence interval and cost per additional screening. Set the minimum useful gain before launch.</p></div></div>
          <p className="trial-method">Wait for complete follow-up and claims. Multiple pilots need a multiple-comparison plan.</p>
        </> : <div className="case-rationale"><p>{play.alternative}</p></div>}
      </>}
    </div>
    <div className="intervention-dialog-footer"><Icon name="info" size={14} />{play.pilot ? "Proposed action. Its effect has not been measured." : "No measured effect or savings are claimed."}</div>
  </dialog>, document.body);
}
