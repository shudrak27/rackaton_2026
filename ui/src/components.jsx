import React from "react";
import { ResponsiveContainer } from "recharts";
import { num } from "./labels.js";

const paths = {
  activity: <path d="M3 12h4l3-8 4 16 3-8h4" />,
  overview: <><rect x="3" y="3" width="7" height="7" rx="1.5" /><rect x="14" y="3" width="7" height="7" rx="1.5" /><rect x="3" y="14" width="7" height="7" rx="1.5" /><rect x="14" y="14" width="7" height="7" rx="1.5" /></>,
  chart: <><path d="M4 4v16h16M8 15l4-5 4 3 5-8" /><path d="M17 5h4v4" /></>,
  drivers: <><path d="M4 7h16M4 17h16" /><circle cx="9" cy="7" r="3" /><circle cx="15" cy="17" r="3" /></>,
  people: <><circle cx="9" cy="8" r="3" /><path d="M3 20v-2a6 6 0 0 1 12 0v2M16 5a3 3 0 0 1 0 6M18 15a5 5 0 0 1 3 5" /></>,
  flask: <path d="M9 3h6M10 3v6l-6 10a1.4 1.4 0 0 0 1.2 2h13.6a1.4 1.4 0 0 0 1.2-2L14 9V3M7 15h10" />,
  mail: <><rect x="3" y="5" width="18" height="14" rx="2" /><path d="m3 6 9 7 9-7" /></>,
  calendar: <><rect x="3" y="5" width="18" height="16" rx="2" /><path d="M7 3v4M17 3v4M3 11h18M8 15h2M14 15h2" /></>,
  target: <><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="5" /><circle cx="12" cy="12" r="1" /></>,
  arrow: <path d="M5 12h14m-5-5 5 5-5 5" />,
  chevron: <path d="m9 5 7 7-7 7" />,
  down: <path d="m6 9 6 6 6-6" />,
  download: <path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5" />,
  help: <><circle cx="12" cy="12" r="9" /><path d="M9.5 9a2.5 2.5 0 0 1 5 0c0 2-2.5 2-2.5 4M12 16h.01" /></>,
  shield: <><path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6l8-3Z" /><path d="m8 12 3 3 5-6" /></>,
  menu: <path d="M4 6h16M4 12h16M4 18h16" />,
  close: <path d="m6 6 12 12M6 18 18 6" />,
  check: <path d="m5 12 4 4L19 6" />,
  clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
  file: <path d="M14 3H5v18h14V8l-5-5Zm0 0v5h5M8 12h8M8 16h5" />,
  globe: <><circle cx="12" cy="12" r="9" /><ellipse cx="12" cy="12" rx="4" ry="9" /><path d="M3 12h18" /></>,
  info: <><circle cx="12" cy="12" r="9" /><path d="M12 11v6M12 7h.01" /></>,
};

export function Icon({ name, size = 20, ...props }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
    strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>{paths[name] || paths.chart}</svg>;
}

export function Kpi({ label, value, detail, foot, tone = "indigo", icon = "chart", highlight = false }) {
  return <article className={`kpi tone-${tone}${highlight ? " kpi-highlight" : ""}`}>
    <div className="kpi-main"><div><p className="kpi-label">{label}</p><div className="kpi-value">{value}</div></div>
      <span className="kpi-icon"><Icon name={icon} size={22} /></span></div>
    <p className="kpi-detail">{detail}</p>
    {foot && <p className="kpi-foot">{foot}</p>}
  </article>;
}

export function Panel({ title, subtitle, action, children, className = "", footer }) {
  return <section className={`panel ${className}`}>
    {(title || action) && <div className="panel-heading"><div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div>{action}</div>}
    {children}
    {footer && <div className="panel-footer">{footer}</div>}
  </section>;
}

export function Chart({ children, height = 270, label }) {
  return <div className="chart-container" style={{ height }} role="img" aria-label={label}>
    <ResponsiveContainer width="100%" height="100%" minWidth={0}>{children}</ResponsiveContainer>
  </div>;
}

export function Badge({ children, tone = "indigo" }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

export function Notice({ children, tone = "indigo", icon = "info" }) {
  return <div className={`notice notice-${tone}`}><Icon name={icon} size={19} /><div>{children}</div></div>;
}

export function ChartTooltip({ active, payload, label, format = (v) => `${(v * 100).toFixed(1)}%`, labelFormat = (v) => v, showCount = false }) {
  if (!active || !payload?.length) return null;
  return <div className="chart-tooltip"><div className="tooltip-label">{labelFormat(label)}</div>
    {payload.filter((p) => p.value != null).map((p, i) => <div className="tooltip-row" key={`${p.dataKey}-${i}`}>
      <span className="legend-dot" style={{ background: p.color || p.payload?.fill || "#5863ed" }} />
      <span>{p.name}</span><strong>{format(p.value)}</strong></div>)}
    {showCount && payload[0]?.payload?.n != null && <div className="tooltip-count">{num(payload[0].payload.n)} invitations</div>}
  </div>;
}

export function Table({ label, children }) {
  return <div className="table-scroll" tabIndex={0} role="region" aria-label={label}><table className="data-table">{children}</table></div>;
}

export function LegendItem({ color, children }) {
  return <span className="legend-item"><i className="legend-dot" style={{ background: color }} />{children}</span>;
}
