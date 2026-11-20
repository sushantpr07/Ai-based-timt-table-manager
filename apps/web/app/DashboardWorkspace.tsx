"use client";

import { useCallback, useEffect, useState } from "react";
import { Activity, ArrowRight, CalendarDays, DoorOpen, GraduationCap, RefreshCw, Sparkles, Users, WandSparkles } from "lucide-react";
import { apiFetch } from "./api-client";

type Summary = { scope: string; totals: { departments: number; faculty: number; students: number; sections: number; rooms: number; published_timetables: number; scheduled_sessions: number; open_conflicts: number }; room_utilization_percent: number; selected_timetables: { name: string; version: number }[] };

export default function DashboardWorkspace({ fullName, onNavigate }: { fullName: string; onNavigate: (section: string) => void }) {
  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(true);
  const load = useCallback(async () => {
    setBusy(true); setError("");
    try {
      const response = await apiFetch(`${base}/analytics/summary`);
      const data = await response.json(); if (!response.ok) throw new Error(data.detail ?? "Could not load campus overview.");
      setSummary(data);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not load campus overview."); }
    finally { setBusy(false); }
  }, [base]);
  useEffect(() => { void load(); }, [load]);
  const metrics = summary ? [
    { icon: <CalendarDays size={17}/>, label: "Published sessions", value: summary.totals.scheduled_sessions, note: `${summary.totals.published_timetables} published timetables` },
    { icon: <Users size={17}/>, label: "Faculty", value: summary.totals.faculty, note: `${summary.totals.sections} sections in scope` },
    { icon: <GraduationCap size={17}/>, label: "Students", value: summary.totals.students, note: `${summary.totals.departments} departments` },
    { icon: <DoorOpen size={17}/>, label: "Room utilization", value: `${summary.room_utilization_percent}%`, note: `${summary.totals.rooms} rooms in scope` },
  ] : [];
  return <section className="dashboard-workspace"><div className="dashboard-welcome"><div><span className="panel-kicker">{summary?.scope.toUpperCase() ?? "CAMPUS OVERVIEW"} · LIVE DATA</span><h1>Welcome back, <em>{fullName.split(" ")[0]}.</em></h1><p>Your campus operations, summarized from live records.</p></div><div><button className="button button-quiet" onClick={() => void load()} disabled={busy}><RefreshCw size={14}/> Refresh</button><button className="button button-primary" onClick={() => onNavigate("Timetable")}><WandSparkles size={15}/> Open planner <ArrowRight size={14}/></button></div></div>
    {error && <div className="notice error-notice">{error}</div>}
    <div className="dashboard-live-metrics">{metrics.map(item => <article className="dashboard-live-card panel" key={item.label}><span>{item.icon}</span><small>{item.label}</small><b>{item.value}</b><i>{item.note}</i></article>)}</div>
    <div className="dashboard-lower"><article className="dashboard-focus panel"><div className="dashboard-focus-icon"><Sparkles size={18}/></div><span className="panel-kicker">PLANNING STATUS</span><h2>{summary?.totals.open_conflicts ? `${summary.totals.open_conflicts} conflicts to review` : summary?.totals.published_timetables ? "Your published plan is clear" : "Start with your campus setup"}</h2><p>{summary?.totals.published_timetables ? `Latest schedule: ${summary.selected_timetables[0]?.name ?? "Published timetable"} · v${summary.selected_timetables[0]?.version ?? 1}. Drafts are checked by the constraint optimizer before publishing.` : "Add academic terms, departments, subjects, rooms, and teaching assignments before generating your first schedule."}</p><button className="button button-primary" onClick={() => onNavigate(summary?.totals.published_timetables ? "Analytics" : "Academics")}>{summary?.totals.published_timetables ? "Review analytics" : "Set up academics"}<ArrowRight size={14}/></button></article>
      <article className="dashboard-shortcuts panel"><div className="panel-kicker">QUICK ACCESS</div><h3>Keep things moving</h3><button onClick={() => onNavigate("Academics")}><span><GraduationCap size={16}/></span><b>Academic structure</b><ArrowRight size={14}/></button><button onClick={() => onNavigate("People")}><span><Users size={16}/></span><b>People & teaching loads</b><ArrowRight size={14}/></button><button onClick={() => onNavigate("Classrooms")}><span><DoorOpen size={16}/></span><b>Classrooms & labs</b><ArrowRight size={14}/></button><button onClick={() => onNavigate("Analytics")}><span><Activity size={16}/></span><b>Analytics & reports</b><ArrowRight size={14}/></button></article></div>
    {busy && !summary && <div className="dashboard-loading">Loading live campus data…</div>}
    <div className="dashboard-data-note">{summary ? "Metrics reflect published timetable versions and current campus records." : "Live data requires a signed-in account and an available API."}</div>
  </section>;
}
