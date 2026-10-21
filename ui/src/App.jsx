import React, { useEffect, useRef, useState } from "react";
import { Icon } from "./components.jsx";
import { Overview, Why, What, Verify } from "./pages.jsx";
import { Business } from "./business.jsx";
import { WhoToCall } from "./call.jsx";
import { ModelQuality, Calibration, Validation } from "./technical.jsx";

// block = the challenge question each page answers (VZP: KDO / PROČ / CO / JAK OVĚŘIT)
const PAGES = [
  { id: "overview", label: "Overview", block: null, icon: "overview", component: Overview,
    title: "Screening overview", description: null },
  { id: "call", label: "Who to call", block: "01 · Who", icon: "phone", component: WhoToCall,
    title: "Who to call", description: null },
  { id: "drivers", label: "Drivers", block: "02 · Why", icon: "drivers", component: Why,
    title: "Why women skip screening", description: null },
  { id: "segments", label: "Segments", block: "03 · What", icon: "people", component: What,
    title: "Segments and targeted support", description: "Operational segments, each with a proposed intervention." },
  { id: "experiment", label: "Experiment", block: "04 · How to verify", icon: "flask", component: Verify,
    title: "Proving the effect", description: null },
  { id: "business", label: "Business actions", block: "Action plan", icon: "target", component: Business,
    title: "What to do for each group", description: null },
  { id: "model-quality", label: "Model quality", group: "technical", block: "Model evaluation", icon: "chart", component: ModelQuality,
    title: "Model quality", description: "How well the model ranks risk, compared with a simple baseline." },
  { id: "calibration", label: "Calibration", group: "technical", block: "Model evaluation", icon: "target", component: Calibration,
    title: "Calibration", description: "How closely predicted probabilities match observed outcomes." },
  { id: "validation", label: "Validation", group: "technical", block: "Model evaluation", icon: "shield", component: Validation,
    title: "Validation", description: "How the model is evaluated and where performance varies." },
];

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
      <dt>What is average precision?</dt><dd>It measures ranking quality for a named outcome: attendance or non-attendance. The technical pages show both, with their respective random references. AP is not the percentage of correct predictions.</dd>
      <dt>What is the baseline?</dt><dd>A simple history-based score: previous invitations minus 0.1 times the screening procedure count in the last five years. It is a comparator, not a probability.</dd>
      <dt>What is calibration?</dt><dd>When the model gives a group an 80% risk, roughly 80% of that group should actually miss screening. The calibration page checks this agreement.</dd>
      <dt>Does high risk mean a call will help?</dt><dd>Risk identifies likely non-attendance. A randomized experiment is needed to measure the effect of additional outreach.</dd>
    </dl>
  </dialog>;
}

export default function App() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [attempt, setAttempt] = useState(0);
  const [tab, setTab] = useState(currentPage);
  const [help, setHelp] = useState(false);
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

  useEffect(() => { document.title = `${page.label} · Screening Insights`; }, [page.label]);

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

  return <div className={`app${mobileOpen ? " mobile-open" : ""}`}>
    <a href="#main-content" className="skip-link" onClick={(e) => { e.preventDefault(); document.getElementById("main-content").focus(); }}>Skip to content</a>
    <header className="topbar">
      <button className="icon-button menu-button" aria-label="Toggle navigation" aria-controls="sidebar" aria-expanded={mobileOpen}
        onClick={() => setMobileOpen((v) => !v)}><Icon name="menu" size={19} /></button>
      <a className="brand" href="#overview" onClick={(e) => { e.preventDefault(); navigate("overview"); }} aria-label="Screening Insights overview">
        <span className="brand-symbol"><Icon name="activity" size={20} /></span><span className="brand-name">screening<span> insights</span></span>
      </a>
      <span className="topbar-context">Rakathon 2026 · VZP mammography screening</span>
      <button className="icon-button help-button" aria-label="Open metric guide" title="Metric guide" onClick={() => setHelp(true)}><Icon name="help" size={19} /></button>
    </header>
    <button className="sidebar-overlay" aria-label="Close navigation" tabIndex={mobileOpen ? 0 : -1} onClick={() => setMobileOpen(false)} />
    <aside className="sidebar" id="sidebar">
      <nav className="side-nav" aria-label="Dashboard sections">{[
        ["business", "Screening & outreach"], ["technical", "Model evaluation"],
      ].map(([group, label]) => <div className="nav-group" key={group}>
        <p className="nav-group-label">{label}</p>
        {PAGES.filter((p) => (p.group || "business") === group).map((p, i) => <button key={p.id} className={`nav-item${tab === p.id ? " active" : ""}`}
          aria-current={tab === p.id ? "page" : undefined} onClick={() => navigate(p.id)}><Icon name={p.icon} size={18} /><span>{p.label}</span>{group === "business" && i > 0 && <span className="nav-number">0{i}</span>}</button>)}
      </div>)}</nav>
      <div className="sidebar-footer"><Icon name="shield" size={14} />Aggregates only</div>
    </aside>
    <main className="main" id="main-content" tabIndex={-1}>
      {data ? <><div className="page-heading">{page.block && <span className="eyebrow">{page.block}</span>}<h1>{page.title}</h1>{page.description && <p className="page-description">{page.description}</p>}</div>
        <Page key={page.id} d={data} navigate={navigate} />
        <footer className="page-footer"><span>VZP invitations {data.meta.years[0]}–{data.meta.years.at(-1)} · model tested on {data.meta.test_year}</span><span>Groups below {data.meta.min_cell} suppressed</span></footer>
      </> : <div className="empty-state" role={error ? "alert" : "status"}>
        {error ? <><Icon name="file" size={32} /><h1>Dashboard data is unavailable</h1><p>Run <code>python -m screening export-ui</code>, then <code>npm run dev</code> again.</p>
          <button className="button" onClick={() => setAttempt((v) => v + 1)}>Try again <Icon name="arrow" size={15} /></button></>
          : <><div className="spinner" /><h1>Loading</h1></>}
      </div>}
    </main>
    {help && <MetricHelp onClose={() => setHelp(false)} />}
  </div>;
}
