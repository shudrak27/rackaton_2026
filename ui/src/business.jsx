import React from "react";
import { Badge, Icon } from "./components.jsx";
import { InterventionActions } from "./intervention-info.jsx";
import { PLAYBOOKS } from "./interventions.js";
import { num, pct } from "./labels.js";

// One card per segment: who, what we do, how big the group is and how many come today.
const ACTION_ORDER = [
  "lapsed_regular",
  "repeated_nonresponder",
  "care_no_prevention",
  "low_contact",
  "recently_screened",
  "first_invitation",
];

export function Business({ d }) {
  return <>
    <p className="business-lead">Six groups of invited women, one concrete action for each. The first pilot is highlighted.</p>
    <ol className="action-grid" aria-label="Actions by screening segment">
      {ACTION_ORDER.map((id, index) => {
        const play = PLAYBOOKS[id];
        const row = d.segments.find((item) => item.segment === id);
        if (!play || !row) return null;
        const first = play.status === "First pilot";
        return <li className={`action-card action-${play.tone}${first ? " action-first" : ""}`} key={id}>
          <div className="action-head">
            <span className="action-avatar" aria-hidden="true"><Icon name={play.icon} size={24} /></span>
            <div className="action-titles"><span className="action-number">{String(index + 1).padStart(2, "0")}</span>
              <h2>{play.audience}</h2></div>
            <Badge tone={play.tone}>{play.status}</Badge>
          </div>
          <p className="action-do"><Icon name="arrow" size={16} />{play.title}</p>
          <div className="action-stats">
            <div><strong>{num(row.n)}</strong><span>women in {d.meta.test_year}</span></div>
            <div><strong>{pct(1 - row.non_attendance, 0)}</strong><span>come today</span></div>
          </div>
          <div className="action-buttons"><InterventionActions segment={id} d={d} /></div>
        </li>;
      })}
    </ol>
  </>;
}
