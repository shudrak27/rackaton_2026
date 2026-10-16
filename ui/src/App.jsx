import React, { useEffect, useRef, useState } from "react";
import { Badge, Icon } from "./components.jsx";
import { Overview, Who, Why, What, Verify } from "./pages.jsx";
export { RateBars } from "./pages.jsx";

const PAGES = [
  { id: "overview", label: "Overview", title: "Screening overview", icon: "overview", component: Overview,
    description: "Attendance, model performance and outreach opportunities in one place." },
  { id: "risk", label: "Risk & performance", title: "Risk & performance", icon: "chart", component: Who,
    description: "See how well the model ranks risk and where it improves on the invitation-count rule." },
  { id: "drivers", label: "Attendance drivers", title: "Attendance drivers", icon: "drivers", component: Why,
    description: "Explore the histories and patterns associated with non-attendance." },
  { id: "segments", label: "Segments & outreach", title: "Segments & outreach", icon: "people", component: What,
    description: "Connect audience segments with practical ideas for more relevant support." },
  { id: "experiment", label: "Experiment planner", title: "Experiment planner", icon: "flask", component: Verify,
    description: "Design a controlled pilot and estimate the participants needed to measure its impact." },
];

// Preserve the page exports for consumers of the original dashboard.
export const TABS = [["Overview", Overview], ["01 WHO", Who], ["02 WHY", Why], ["03 WHAT", What], ["04 HOW TO VERIFY", Verify]];

function currentPage() {
  const id = window.location.hash.slice(1);
  return PAGES.some((p) => p.id === id) ? id : "overview";
}

function MetricHelp({ onClose }) {
  const ref = useRef(null);
  useEffect(() => {
    const dialog = ref.current;
    dialog.showModal();
    return () => dialog.close();
  }, []);
  return <dialog ref={ref} className="help-dialog" aria-labelledby="help-title" onCancel={onClose}
    onClick={(e) => { if (e.target === ref.current) onClose(); }}>
    <div className="help-heading"><h2 id="help-title">A quick guide to the numbers</h2><button className="icon-button" aria-label="Close guide" onClick={onClose}><Icon name="close" /></button></div>
    <dl>
      <dt>What does the model predict?</dt><dd>The probability of not attending mammography screening within 12 months of an invitation.</dd>
      <dt>What is a risk decile?</dt><dd>One of ten equally sized groups, sorted by predicted risk. Decile 1 has the lowest risk; decile 10 has the highest. The bars show actual attendance.</dd>
      <dt>What does ROC-AUC measure?</dt><dd>How well the model ranks non-attenders above attenders. A random ranking scores 0.5; perfect separation scores 1.</dd>
      <dt>What is average precision?</dt><dd>Here, it evaluates ranking for attendance. Its random baseline is the attendance rate in the test year.</dd>
      <dt>Does high risk mean a call will help?</dt><dd>Risk identifies likely non-attendance. A randomized experiment is needed to measure the effect of additional outreach.</dd>
    </dl>
  </dialog>;
}

function exportData(data) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = `screening-aggregates-${data.meta.test_year}.json`;
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export default function App() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [attempt, setAttempt] = useState(0);
  const [tab, setTab] = useState(currentPage);
  const [help, setHelp] = useState(false);
  const [mobile, setMobile] = useState(() => window.matchMedia("(max-width: 760px)").matches);
  const [sidebarHidden, setSidebarHidden] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const page = PAGES.find((p) => p.id === tab) || PAGES[0];

  useEffect(() => {
    const controller = new AbortController();
    setError(null);
    fetch("./data.json", { signal: controller.signal })
      .then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then((payload) => {
        if (!payload.meta || !Array.isArray(payload.deciles) || !payload.deciles.length || !Array.isArray(payload.segments) || !payload.segments.length) {
          throw new Error("The aggregate export is incomplete.");
        }
        setData(payload);
      }).catch((e) => { if (e.name !== "AbortError") setError(e.message); });
    return () => controller.abort();
  }, [attempt]);

  useEffect(() => {
    const update = () => { setTab(currentPage()); setMobileOpen(false); };
    window.addEventListener("hashchange", update);
    return () => window.removeEventListener("hashchange", update);
  }, []);

  useEffect(() => {
    const query = window.matchMedia("(max-width: 760px)");
    const update = (e) => { setMobile(e.matches); setMobileOpen(false); };
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);

  useEffect(() => { document.title = `${page.title} · Screening Insights`; }, [page.title]);

  useEffect(() => {
    if (!mobileOpen) return;
    const escape = (e) => { if (e.key === "Escape") setMobileOpen(false); };
    window.addEventListener("keydown", escape);
    return () => window.removeEventListener("keydown", escape);
  }, [mobileOpen]);

  function navigate(id) {
    setTab(id);
    window.location.hash = id;
    setMobileOpen(false);
    window.scrollTo({ top: 0 });
  }

  const Page = page.component;
  const generatedDate = data?.meta.generated_at ? new Date(data.meta.generated_at) : null;
  const updated = generatedDate && !Number.isNaN(generatedDate.getTime())
    ? new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric" }).format(generatedDate) : null;

  return <div className={`app${sidebarHidden && !mobile ? " sidebar-hidden" : ""}${mobileOpen ? " mobile-open" : ""}`}>
    <a href="#main-content" className="skip-link" onClick={(e) => { e.preventDefault(); document.getElementById("main-content").focus(); }}>Skip to content</a>
    <header className="topbar">
      <a className="brand" href="#overview" onClick={(e) => { e.preventDefault(); navigate("overview"); }} aria-label="Screening Insights overview">
        <span className="brand-symbol"><Icon name="activity" size={24} /></span><span className="brand-name">screening<span> insights</span></span>
      </a>
      <div className="topbar-inner">
        <button className="icon-button" aria-label="Toggle navigation" aria-controls="sidebar" aria-expanded={mobile ? mobileOpen : !sidebarHidden}
          onClick={() => mobile ? setMobileOpen((v) => !v) : setSidebarHidden((v) => !v)}><Icon name="menu" size={19} /></button>
        <div className="topbar-context">Analytics workspace <span>/ Mammography screening</span></div>
        <div className="topbar-right"><span className="topbar-status"><i className="status-dot" />Aggregate data</span>
          <button className="icon-button" aria-label="Open metric guide" title="Metric guide" onClick={() => setHelp(true)}><Icon name="help" size={19} /></button>
          <span className="avatar" title="Rakathon research workspace">RA</span></div>
      </div>
    </header>
    <button className="sidebar-overlay" aria-label="Close navigation" tabIndex={mobileOpen ? 0 : -1} onClick={() => setMobileOpen(false)} />
    <aside className="sidebar" id="sidebar">
      <div className="workspace"><span className="workspace-icon"><Icon name="activity" size={19} /></span><div><strong>Screening analytics</strong><small>Rakathon 2026 · VZP cohort</small></div></div>
      <p className="nav-heading">WORKSPACE</p>
      <nav className="side-nav" aria-label="Dashboard sections">{PAGES.map((p, i) => <button key={p.id} className={`nav-item${tab === p.id ? " active" : ""}`}
        aria-current={tab === p.id ? "page" : undefined} onClick={() => navigate(p.id)}><Icon name={p.icon} size={18} /><span>{p.label}</span>{i > 0 && <span className="nav-number">0{i}</span>}</button>)}</nav>
      <div className="sidebar-bottom"><div className="pilot-card"><Badge>THE NEXT STEP</Badge><strong>From insight to impact</strong>
        <p>Test which support makes a difference to attendance.</p><button onClick={() => navigate("experiment")}>Plan your pilot <Icon name="arrow" size={15} /></button></div>
        <div className="sidebar-footer"><Icon name="shield" size={14} />Aggregated. De-identified.</div></div>
    </aside>
    <main className="main" id="main-content" tabIndex={-1}>
      <div className="breadcrumbs"><Icon name="overview" size={12} /><span>Workspace</span><Icon name="chevron" size={10} /><span>{page.label}</span></div>
      {data ? <><div className="page-heading"><div><h1>{page.title}</h1><p className="page-description">{page.description}</p></div>
        <div className="page-actions"><span className="date-chip"><Icon name="calendar" size={15} />{data.meta.years[0]}–{data.meta.years.at(-1)}</span>
          <button className="button" aria-label="Export aggregate data" onClick={() => exportData(data)}><Icon name="download" size={15} /><span>Export data</span></button></div></div>
        <Page key={page.id} d={data} navigate={navigate} />
        <footer className="page-footer"><span>Rakathon 2026 · Screening Insights</span><span>Aggregates only · Small groups below {data.meta.min_cell} suppressed{updated && ` · Updated ${updated}`}</span></footer>
      </> : <div className="empty-state" role={error ? "alert" : "status"}>
        {error ? <><Icon name="file" size={32} /><h1>Dashboard data is unavailable</h1><p>The aggregate report could not be loaded. Check that the supplied reports are available, then try again.</p>
          <button className="button" onClick={() => setAttempt((v) => v + 1)}>Try again <Icon name="arrow" size={15} /></button></>
          : <><div className="spinner" /><h1>Preparing your overview</h1><p>Loading the latest aggregate report.</p></>}
      </div>}
    </main>
    {help && <MetricHelp onClose={() => setHelp(false)} />}
  </div>;
}
