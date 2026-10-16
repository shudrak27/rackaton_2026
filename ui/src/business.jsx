import React from "react";
import { Badge, Icon } from "./components.jsx";
import { InterventionActions } from "./intervention-info.jsx";
import { PLAYBOOKS } from "./interventions.js";
import { num, pct } from "./labels.js";

const ACTION_ORDER = [
  "repeated_nonresponder",
  "care_no_prevention",
  "first_invitation",
  "low_contact",
  "lapsed_regular",
  "recently_screened",
];

export function Business({ d }) {
  return <ol className="action-list" aria-label="Actions by screening segment">
    {ACTION_ORDER.map((id, index) => {
      const play = PLAYBOOKS[id];
      const row = d.segments.find((item) => item.segment === id);
      if (!row) return null;
      return <li className={`action-row action-row-${play.tone}`} key={id}>
        <span className="action-index" aria-hidden="true">{String(index + 1).padStart(2, "0")}</span>
        <span className="action-symbol" aria-hidden="true"><Icon name={play.icon} size={23} /></span>
        <div className="action-copy">
          <div className="action-topline"><h2>{play.audience}</h2><Badge tone={play.tone}>{play.status}</Badge></div>
          <p className="action-treatment">{play.title}</p>
          <p className="action-meta">{num(row.n)} women <span aria-hidden="true">·</span> {pct(1 - row.non_attendance, 2)} attended in {d.meta.test_year}</p>
        </div>
        <InterventionActions segment={id} d={d} />
      </li>;
    })}
  </ol>;
}
