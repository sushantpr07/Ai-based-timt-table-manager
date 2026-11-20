"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import CampusWorkspace from "./CampusWorkspace";
import TimetableWorkspace from "./TimetableWorkspace";
import PersonalWorkspace from "./PersonalWorkspace";
import AnalyticsWorkspace from "./AnalyticsWorkspace";
import AuditWorkspace from "./AuditWorkspace";
import SettingsWorkspace from "./SettingsWorkspace";
import DashboardWorkspace from "./DashboardWorkspace";
import AssistantWorkspace from "./AssistantWorkspace";
import NotificationsWorkspace from "./NotificationsWorkspace";
import ThemeToggle from "./ThemeToggle";
import { apiFetch } from "./api-client";
import {
  Activity, ArrowDownRight, ArrowLeft, ArrowRight, ArrowUpRight, Bell, BookOpen, CalendarDays,
  Check, ChevronDown, ChevronLeft, ChevronRight, Clock3, Command, Cpu, Download,
  GraduationCap, LayoutDashboard, Leaf, LogOut, MoreHorizontal, Search, Send, Settings2, ShieldCheck, Sparkles, Users, WandSparkles, X, Zap,
} from "lucide-react";

type Entry = { time: string; title: string; room: string; tone: string; span?: number; day: number };
const initialEntries: Entry[] = [
  { time: "09:00", title: "Data Structures", room: "Room 204 · Dr. Mehta", tone: "blue", day: 0 },
  { time: "11:00", title: "Database Systems", room: "Lab 3 · Prof. Nair", tone: "violet", day: 0 },
  { time: "14:00", title: "Discrete Mathematics", room: "Room 108 · Dr. Shah", tone: "amber", day: 0 },
  { time: "10:00", title: "Operating Systems", room: "Room 210 · Prof. Rao", tone: "green", day: 1 },
  { time: "12:00", title: "Data Structures Lab", room: "Lab 2 · Dr. Mehta", tone: "rose", span: 2, day: 1 },
  { time: "09:00", title: "Computer Networks", room: "Room 204 · Prof. Nair", tone: "cyan", day: 2 },
  { time: "11:00", title: "Database Systems", room: "Lab 3 · Prof. Nair", tone: "violet", day: 2 },
  { time: "14:00", title: "Discrete Mathematics", room: "Room 108 · Dr. Shah", tone: "amber", day: 2 },
  { time: "10:00", title: "Operating Systems", room: "Room 210 · Prof. Rao", tone: "green", day: 3 },
  { time: "13:00", title: "Computer Networks", room: "Room 204 · Prof. Nair", tone: "cyan", day: 3 },
  { time: "09:00", title: "Data Structures", room: "Room 204 · Dr. Mehta", tone: "blue", day: 4 },
  { time: "11:00", title: "Project Studio", room: "Innovation Hub · Dr. Shah", tone: "rose", day: 4 },
];
const days = ["Mon", "Tue", "Wed", "Thu", "Fri"];
const navGroups = [
  { title: "Workspace", items: [["Overview", LayoutDashboard], ["Timetable", CalendarDays], ["AI planner", WandSparkles]] as const },
  { title: "Manage", items: [["People", Users], ["Academics", BookOpen], ["Classrooms", GraduationCap]] as const },
  { title: "Insights", items: [["Analytics", Activity], ["Audit log", Activity], ["Settings", Settings2]] as const },
];

export type Viewer = {
  id: string;
  email: string;
  full_name: string;
  role: string;
  department?: string | null;
  department_code?: string | null;
  section?: string | null;
  semester?: number | null;
  student_number?: string | null;
};

export default function Home() {
  const [viewer, setViewer] = useState<Viewer | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [active, setActive] = useState("Overview");
  const [entries, setEntries] = useState(initialEntries);
  const [week, setWeek] = useState(0);
  const [notice, setNotice] = useState("");
  const [prompt, setPrompt] = useState("");
  const [answer, setAnswer] = useState("");
  const [dragging, setDragging] = useState<Entry | null>(null);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchText, setSearchText] = useState("");
  const [activeSearchIndex, setActiveSearchIndex] = useState(0);
  const searchButton = useRef<HTMLButtonElement>(null);
  const searchInput = useRef<HTMLInputElement>(null);
  const slots = ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00"];
  const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

  useEffect(() => {
    let mounted = true;
    if (typeof window !== "undefined") {
      try {
        const cached = localStorage.getItem("dayleaf_user");
        if (cached) {
          const parsed = JSON.parse(cached);
          if (parsed && parsed.email) setViewer(parsed);
        }
      } catch {}
    }
    apiFetch(`${apiBase}/auth/me`).then(response => response.ok ? response.json() : null)
      .then(data => {
        if (mounted && data) {
          setViewer(data);
          try { localStorage.setItem("dayleaf_user", JSON.stringify(data)); } catch {}
        }
      }).catch(() => undefined)
      .finally(() => { if (mounted) setAuthChecked(true); });
    return () => { mounted = false; };
  }, [apiBase]);

  const shownEntries = useMemo(() => entries, [entries]);

  function generate() { setNotice(""); setActive("Timetable"); }

  async function signOut() {
    try {
      if (typeof window !== "undefined") localStorage.removeItem("dayleaf_user");
      await apiFetch(`${apiBase}/auth/sign-out`, { method: "POST" });
    } finally { setViewer(null); setActive("Overview"); }
  }

  const roleNavGroups = viewer && ["faculty", "student"].includes(viewer.role)
    ? [{ title: "My workspace", items: [["Overview", LayoutDashboard], ["Timetable", CalendarDays], ["Department", GraduationCap], ["Notifications", Bell], ["Settings", Settings2]] as const }]
    : viewer ? [...navGroups, { title: "Updates", items: [["Notifications", Bell]] as const }]
      : navGroups;
  const searchItems = roleNavGroups.flatMap(group => group.items
    .filter(([label]) => label !== "Audit log" || !viewer || ["super_admin", "college_admin", "hod"].includes(viewer.role))
    .map(([label]) => ({ label, group: group.title })))
    .filter(item => `${item.label} ${item.group}`.toLowerCase().includes(searchText.trim().toLowerCase()));

  function closeSearch() {
    setSearchOpen(false); setSearchText("");
    requestAnimationFrame(() => searchButton.current?.focus());
  }

  useEffect(() => {
    function handleShortcut(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault(); setSearchOpen(true); setSearchText("");
      } else if (event.key === "Escape" && searchOpen) {
        closeSearch();
      }
    }
    window.addEventListener("keydown", handleShortcut);
    return () => window.removeEventListener("keydown", handleShortcut);
  }, [searchOpen]);

  useEffect(() => { if (searchOpen) searchInput.current?.focus(); }, [searchOpen]);

  function exportCsv() {
    const csv = ["Day,Time,Subject,Room / Faculty", ...entries.map((e) => `${days[e.day]},${e.time},${e.title},${e.room}`)].join("\n");
    const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" })); a.download = "dayleaf-timetable.csv"; a.click(); URL.revokeObjectURL(a.href);
  }

  async function askAssistant(event: React.FormEvent) {
    event.preventDefault(); if (!prompt.trim()) return;
    if (!viewer) { setAnswer("Sign in to use Dayleaf AI with your campus data."); setPrompt(""); return; }
    setAnswer("Thinking through your request…");
    try {
      const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
      const res = await apiFetch(`${base}/assistant/chat`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message: prompt }) });
      const data = await res.json();
      setAnswer(res.ok ? data.reply : "Dayleaf Assistant is ready. Try ‘Generate a timetable’ to run the constraint solver.");
    } catch { setAnswer("Dayleaf AI is active. Schedule drafts are checked and validated by the campus constraint solver."); }
    setPrompt("");
  }

  return <div className="app-shell">
    <aside className="sidebar">
      <a className="brand" href="#overview" aria-label="Dayleaf home">
        <span className="dayleaf-brand-icon"><Sparkles size={18} strokeWidth={2.4} aria-hidden="true"/></span>
        <span className="dayleaf-brand-title">Day<span className="dayleaf-brand-leaf">leaf</span></span>
      </a>
      <div className="campus-switch">
        <span className="campus-avatar">{viewer?.full_name?.slice(0, 1) ?? "D"}</span>
        <span className="campus-copy">
          <b>{viewer?.department ? `${viewer.department_code ?? viewer.department}` : (viewer ? "Dayleaf University" : "Northbridge University · Dayleaf")}</b>
          <small>{viewer?.section ? `Sem ${viewer.semester ?? 3}-${viewer.section} · ${viewer.role}` : (viewer?.role?.replaceAll("_", " ") ?? "Preview workspace")}</small>
        </span>
        <ChevronDown size={15} />
      </div>
      <nav className="side-nav" aria-label="Main navigation">{roleNavGroups.map(group => <div className="nav-group" key={group.title}><div className="nav-label">{group.title}</div>{group.items.filter(([label]) => label !== "Audit log" || !viewer || ["super_admin", "college_admin", "hod"].includes(viewer.role)).map(([label, Icon]) => { const displayedLabel = label === "Timetable" && viewer && ["faculty", "student"].includes(viewer.role) ? "My timetable" : label; return <button key={label} className={`nav-link ${active === label ? "selected" : ""}`} aria-label={displayedLabel} aria-current={active === label ? "page" : undefined} onClick={() => setActive(label)}><Icon size={17} strokeWidth={1.8} aria-hidden="true"/><span>{displayedLabel}</span>{label === "AI planner" && <span className="new-tag">AI</span>}</button>; })}</div>)}</nav>
      <div className="sidebar-bottom"><div className="term-card"><div className="term-dot"/><div><small>{viewer ? "ACCOUNT" : "ACTIVE SEMESTER"}</small><b>{viewer ? viewer.email : "Fall semester 2026"}</b></div><ChevronDown size={14}/></div>{viewer ? <button className="profile-row" onClick={() => void signOut()} title="Sign out"><div className="profile-avatar">{viewer.full_name.split(" ").map(part => part[0]).slice(0, 2).join("")}</div><span><b>{viewer.full_name}</b><small>Sign out of Dayleaf</small></span><LogOut size={15}/></button> : <Link className="profile-row" href="/sign-in" title="Sign in"><div className="profile-avatar">DL</div><span><b>Sign in</b><small>Access Dayleaf Studio</small></span><MoreHorizontal size={17}/></Link>}</div>
    </aside>
    <main className="main-area">
      <header className="topbar">
        <div className="breadcrumbs"><span>Workspace</span><ChevronRight size={13}/><b>{active === "Timetable" && viewer && ["faculty", "student"].includes(viewer.role) ? "My timetable" : active}</b></div>
        <div className="top-actions">
          <div className="search-control">
            <button ref={searchButton} className="search-box" type="button" onClick={() => { setSearchOpen(true); setSearchText(""); setActiveSearchIndex(0); }} aria-label="Search workspaces" aria-haspopup="listbox" aria-expanded={searchOpen}>
              <Search size={16}/><span>Search workspaces...</span><kbd>Ctrl K</kbd>
            </button>
            {searchOpen && <div className="search-popover" role="search">
              <label htmlFor="workspace-search">Find a workspace</label>
              <input ref={searchInput} id="workspace-search" role="combobox" aria-autocomplete="list" aria-controls="workspace-search-results" aria-activedescendant={searchItems.length ? `workspace-option-${activeSearchIndex}` : undefined} aria-expanded="true" value={searchText} onChange={event => { setSearchText(event.target.value); setActiveSearchIndex(0); }} onKeyDown={event => {
                if (event.key === "ArrowDown" && searchItems.length) { event.preventDefault(); setActiveSearchIndex(index => (index + 1) % searchItems.length); }
                if (event.key === "ArrowUp" && searchItems.length) { event.preventDefault(); setActiveSearchIndex(index => (index - 1 + searchItems.length) % searchItems.length); }
                if (event.key === "Enter" && searchItems[activeSearchIndex]) { setActive(searchItems[activeSearchIndex].label); closeSearch(); }
              }} placeholder="Type a workspace name…"/>
              <ul id="workspace-search-results" role="listbox" aria-label="Available workspaces">{searchItems.map((item, index) => <li id={`workspace-option-${index}`} key={item.label} role="option" aria-selected={activeSearchIndex === index} className={activeSearchIndex === index ? "active" : ""} onMouseEnter={() => setActiveSearchIndex(index)} onMouseDown={event => event.preventDefault()} onClick={() => { setActive(item.label); closeSearch(); }}><span>{item.label}</span><small>{item.group}</small></li>)}</ul>
              {!searchItems.length && <p className="search-empty">No workspaces match that search.</p>}
              <small className="search-hint">Use ↑ or ↓ and Enter · Escape to close · Ctrl K to open</small>
            </div>}
          </div>
          <ThemeToggle/>
          {viewer && (
            <button 
              className="button button-quiet" 
              style={{ display: "inline-flex", alignItems: "center", gap: "6px", padding: "6px 12px", fontSize: "13px", height: "36px", borderRadius: "8px" }} 
              onClick={() => void signOut()}
              title="Sign out of Dayleaf"
            >
              <LogOut size={14} />
              <span>Sign out</span>
            </button>
          )}
          {viewer && <button className="icon-button notification" onClick={() => setActive("Notifications")} aria-label="Open notifications"><Bell size={18}/><i/></button>}
          {viewer ? <button className="top-avatar" onClick={() => void signOut()} aria-label="Sign out">{viewer.full_name.split(" ").map(part => part[0]).slice(0, 2).join("")}</button> : <Link className="top-avatar" href="/sign-in" aria-label="Sign in">AM</Link>}
        </div>
      </header>
      <div className="page-content">
        {notice && <div className="notice" role="status"><Check size={17}/><span>{notice}</span><button aria-label="Dismiss notification" onClick={() => setNotice("")}><X size={15}/></button></div>}
        {!viewer && active !== "Overview" ? <section className="workspace-access panel"><span className="panel-kicker">DAYLEAF WORKSPACE</span><h1>{authChecked ? `Sign in to open ${active}` : "Checking your session…"}</h1><p>{authChecked ? "Sign in to manage real campus data. The preview gives you a live tour of Dayleaf Studio." : "Loading your campus workspace…"}</p>{authChecked && <div className="placeholder-actions"><Link className="button button-primary" href="/sign-in">Sign in <ArrowRight size={15}/></Link><Link className="button button-quiet" href="/sign-up">Create campus workspace</Link><button className="button button-quiet" onClick={() => setActive("Overview")}><ArrowLeft size={14}/> Preview</button></div>}</section> : viewer && ["faculty", "student"].includes(viewer.role) && active !== "Settings" ? <PersonalWorkspace active={active} role={viewer.role as "faculty" | "student"} fullName={viewer.full_name} viewer={viewer} onNavigate={setActive}/> : viewer && active === "Overview" ? <DashboardWorkspace fullName={viewer.full_name} onNavigate={setActive}/> : active === "AI planner" ? <AssistantWorkspace onNavigate={setActive}/> : active === "Overview" ? <>
        
        {/* DAYLEAF PREMIUM HERO LANDING PAGE */}
        <section className="dayleaf-hero-container">
          <div className="dayleaf-wave-bg" />
          <div className="dayleaf-gradient-overlay" />
          <div className="dayleaf-hero-content">
            <div className="dayleaf-hero-left">
              <div className="dayleaf-badge">
                <span className="dayleaf-badge-dot" />
                <span>DAYLEAF 2.0 · NEXT-GEN CAMPUS INTELLIGENCE</span>
              </div>
              <h1 className="dayleaf-hero-title">
                Smarter Schedules.<br />
                <span className="dayleaf-hero-gradient">Zero Clashes. Pure Flow.</span>
              </h1>
              <p className="dayleaf-hero-sub">
                Harmonize thousands of classroom hours, professor availability limits, and curriculum requirements in milliseconds. Powered by mathematical constraint optimization and Dayleaf Neural Copilot.
              </p>
              <div className="dayleaf-hero-actions">
                <button className="dayleaf-btn-glow" onClick={generate}>
                  <WandSparkles size={16} /> Plan This Semester <ArrowRight size={15} />
                </button>
                <button className="dayleaf-btn-glass" onClick={() => setActive("AI planner")}>
                  <Sparkles size={15} /> Consult Dayleaf AI
                </button>
                <button className="dayleaf-btn-glass" onClick={exportCsv}>
                  <Download size={15} /> Export CSV
                </button>
              </div>
            </div>

            <div className="dayleaf-hero-visual">
              <div className="dayleaf-glass-hub">
                <div className="dayleaf-hub-header">
                  <span className="dayleaf-hub-status">
                    <i /> Constraint Engine Active
                  </span>
                  <span className="dayleaf-slot-tag tag-verified">100% Conflict Free</span>
                </div>
                <div className="dayleaf-hub-slots">
                  <div className="dayleaf-hub-slot">
                    <div className="dayleaf-hub-slot-info">
                      <span className="dayleaf-slot-dot dot-purple" />
                      <span className="dayleaf-slot-time">09:00 - 10:30</span>
                      <span className="dayleaf-slot-title">Data Structures · Dr. Mehta</span>
                    </div>
                    <span className="dayleaf-slot-tag">Audi 2 · Synced</span>
                  </div>
                  <div className="dayleaf-hub-slot">
                    <div className="dayleaf-hub-slot-info">
                      <span className="dayleaf-slot-dot dot-cyan" />
                      <span className="dayleaf-slot-time">11:00 - 12:30</span>
                      <span className="dayleaf-slot-title">Cyber Networks · Prof. Nair</span>
                    </div>
                    <span className="dayleaf-slot-tag">Lab 3 · Validated</span>
                  </div>
                  <div className="dayleaf-hub-slot">
                    <div className="dayleaf-hub-slot-info">
                      <span className="dayleaf-slot-dot dot-pink" />
                      <span className="dayleaf-slot-time">14:00 - 15:30</span>
                      <span className="dayleaf-slot-title">AI & Neural Systems · Dr. Shah</span>
                    </div>
                    <span className="dayleaf-slot-tag">Room 108 · Balanced</span>
                  </div>
                </div>
              </div>

              <div className="dayleaf-floating-stat">
                <div className="dayleaf-stat-icon">
                  <Zap size={15} />
                </div>
                <div className="dayleaf-stat-text">
                  <b>48ms Solver Speed</b>
                  <small>Zero Room & Faculty Collisions</small>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* DAYLEAF FEATURE PILLARS */}
        <div className="dayleaf-pillars-strip">
          <div className="dayleaf-pillar-card">
            <div className="dayleaf-pillar-icon"><Zap size={16}/></div>
            <h4>Constraint Solver</h4>
            <p>Hard and soft constraint satisfaction for room sizes, lab equipment, and faculty teaching limits.</p>
          </div>
          <div className="dayleaf-pillar-card">
            <div className="dayleaf-pillar-icon"><Sparkles size={16}/></div>
            <h4>Dayleaf Copilot</h4>
            <p>Plain-language assistant that turns natural descriptions into verified timetable proposals.</p>
          </div>
          <div className="dayleaf-pillar-card">
            <div className="dayleaf-pillar-icon"><ShieldCheck size={16}/></div>
            <h4>Zero-Clash Engine</h4>
            <p>Mathematical proof guarantees no double-booked lecture halls or overlapping teacher schedules.</p>
          </div>
          <div className="dayleaf-pillar-card">
            <div className="dayleaf-pillar-icon"><Download size={16}/></div>
            <h4>One-Click Export</h4>
            <p>Instant CSV export, approval audit trail, and department-wide timetable distribution.</p>
          </div>
        </div>

        <section className="metrics-grid">
          <Metric icon={<CalendarDays size={18}/>} label="Scheduled this week" value="1,284" unit="sessions" delta="8.2%" positive detail="vs. last semester" tone="blue"/>
          <Metric icon={<Users size={18}/>} label="Faculty availability" value="94.8" unit="%" delta="3.4%" positive detail="this week" tone="violet"/>
          <Metric icon={<GraduationCap size={18}/>} label="Room utilization" value="82.4" unit="%" delta="5.8%" positive detail="optimal load" tone="green"/>
          <Metric icon={<Activity size={18}/>} label="Open conflicts" value="00" unit="clashes" delta="0 clashes" positive detail="100% verified" tone="orange"/>
        </section>

        <section className="lower-grid">
          <div className="schedule-panel panel">
            <div className="panel-heading">
              <div>
                <div className="panel-kicker">LIVE INTERACTIVE SCHEDULE · SAMPLE DATA</div>
                <h3>Dayleaf Timetable Studio</h3>
              </div>
              <div className="panel-tools">
                <button className="select-pill">CS · Semester 4 · A <ChevronDown size={14}/></button>
                <button className="square-button" onClick={exportCsv} aria-label="Export timetable"><Download size={15}/></button>
                <button className="square-button" onClick={() => setActive("Timetable")} aria-label="Open timetable"><ArrowRight size={15}/></button>
              </div>
            </div>
            <div className="calendar-toolbar">
              <button className="week-nav" onClick={() => setWeek(week - 1)}><ChevronLeft size={16}/></button>
              <b>{week === 0 ? "16 — 20 November, 2026" : `${16 + week * 7} — ${20 + week * 7} November, 2026`}</b>
              <button className="week-nav" onClick={() => setWeek(week + 1)}><ChevronRight size={16}/></button>
              <button className="today-label" onClick={() => setWeek(0)}>TODAY</button>
            </div>
            <div className="schedule-scroll">
              <div className="schedule-grid">
                <div className="day-header time-head">IST</div>
                {days.map((day, i)=><div className={`day-header ${i===0 && week===0 ? "current-day" : ""}`} key={day}><span>{day}</span><b>{16 + week * 7 + i}</b></div>)}
                {slots.map((slot)=><div className="time-row" key={slot}><div className="time-label">{slot}</div>{days.map((_, di)=>{const entry=shownEntries.find(e=>e.day===di && e.time===slot);return <div key={di} className="slot" onDragOver={event=>event.preventDefault()} onDrop={event=>{event.preventDefault();if(!dragging)return;const clash=entries.some(e=>e!==dragging&&e.day===di&&e.time===slot);if(clash){setNotice("That period is already occupied. Choose an empty slot to avoid a section conflict.");return;}setEntries(current=>current.map(e=>e===dragging?{...e,day:di,time:slot}:e));setDragging(null);setNotice(`${dragging.title} moved to ${days[di]} at ${slot}. Review the change before publishing.`);}}>{entry && <button draggable className={`class-card ${entry.tone}`} onDragStart={()=>setDragging(entry)} onDragEnd={()=>setDragging(null)} onClick={()=>setNotice(`${entry.title} · ${entry.room}`)}><b>{entry.title}</b><small>{entry.room}</small></button>}</div>})}</div>)}
              </div>
            </div>
            <div className="schedule-footer">
              <span><span className="legend-dot blue-dot"/> Lecture <span className="legend-dot violet-dot"/> Lab <span className="legend-dot amber-dot"/> Tutorial</span>
              <button onClick={() => setActive("Timetable")}>Open full timetable <ArrowRight size={14}/></button>
            </div>
          </div>
          <aside className="assistant-card">
            <div className="assistant-top">
              <div className="assistant-orb"><Sparkles size={17}/></div>
              <div><span className="ai-label">DAYLEAF AI COPILOT</span><h3>Ask anything.</h3></div>
              <button className="assistant-menu"><MoreHorizontal size={18}/></button>
            </div>
            <p className="assistant-intro">Ask about classroom vacancies, optimize teacher loads, or resolve clashes with Dayleaf Copilot.</p>
            <div className="assistant-thread">
              <div className="assistant-message">
                <span className="assistant-mini"><Sparkles size={12}/></span>
                <p>Hi! I’ve reviewed the academic schedule. <b>All 48 lecture sessions are verified</b> with 0 conflicts. Would you like me to optimize room capacity?</p>
              </div>
              {answer && <div className="assistant-answer">{answer}</div>}
            </div>
            <div className="suggestions">
              <button onClick={()=>setPrompt("Find a free classroom on Wednesday")}>Find a free room <ArrowUpRight size={12}/></button>
              <button onClick={()=>setPrompt("Check faculty workload distribution")}>Faculty load <ArrowUpRight size={12}/></button>
              <button onClick={()=>setPrompt("Generate a timetable draft")}>Draft timetable <ArrowUpRight size={12}/></button>
            </div>
            <form className="assistant-input" onSubmit={askAssistant}>
              <input value={prompt} onChange={e=>setPrompt(e.target.value)} placeholder="Ask Dayleaf AI anything…" aria-label="Ask Dayleaf AI anything"/>
              <button type="submit" aria-label="Send message"><Send size={15}/></button>
            </form>
            <div className="ai-disclaimer"><span>✦</span> Powered by Dayleaf Constraint Intelligence</div>
          </aside>
        </section>
        <footer className="page-footer">
          <span>© 2026 Dayleaf Technologies <span className="footer-sep">·</span> Northbridge University Workspace</span>
          <span><i className="status-dot"/> Dayleaf Studio · All Systems Active</span>
        </footer>
        </> : active === "Timetable" ? <TimetableWorkspace onNavigate={setActive}/> : active === "Academics" || active === "Classrooms" || active === "People" ? <CampusWorkspace active={active} onNavigate={setActive}/> : active === "Analytics" ? <AnalyticsWorkspace/> : active === "Audit log" ? <AuditWorkspace/> : active === "Settings" ? <SettingsWorkspace onNameChange={name => setViewer(current => current ? { ...current, full_name: name } : current)}/> : active === "Notifications" && viewer ? <NotificationsWorkspace/> : <section className="module-placeholder panel"><div className="metric-icon green"><Sparkles size={18}/></div><div className="panel-kicker">DAYLEAF WORKSPACE</div><h2>{active} setup is next</h2><p>This area connects to your campus live database. Use the Timetable and AI Planner workspaces to manage active schedules.</p><div className="placeholder-actions"><button className="button button-quiet" onClick={() => setActive("Overview")}><ArrowLeft size={14}/> Back to overview</button></div></section>}
      </div>
    </main>
  </div>;
}

function Metric({ icon, label, value, unit, delta, positive, detail, tone }: { icon: React.ReactNode; label: string; value: string; unit: string; delta: string; positive: boolean; detail: string; tone: string }) {
  return <article className="metric-card"><div className={`metric-icon ${tone}`}>{icon}</div><span className="metric-label">{label}</span><div className="metric-number">{value}<small>{unit}</small></div><div className="metric-delta"><span className={positive ? "delta-good" : "delta-bad"}>{positive ? <ArrowUpRight size={13}/> : <ArrowDownRight size={13}/>} {delta}</span><span>{detail}</span></div></article>;
}
