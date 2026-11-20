"use client";

import { useCallback, useEffect, useState } from "react";
import { Activity, Download, GraduationCap, RefreshCw, Users, DoorOpen, CalendarDays, AlertTriangle } from "lucide-react";
import { apiFetch } from "./api-client";
import ReportsWorkspace from "./ReportsWorkspace";

type Analytics = {
  scope: string;
  totals: { departments: number; faculty: number; students: number; sections: number; rooms: number; published_timetables: number; scheduled_sessions: number; open_conflicts: number };
  room_utilization_percent: number;
  daily_sessions: { day: number; sessions: number }[];
  faculty_load: { id: string; name: string; sessions: number }[];
  selected_timetables: { name: string; version: number }[];
};
const weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

export default function AnalyticsWorkspace() {
  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
  const [data, setData] = useState<Analytics | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(true);
  const load = useCallback(async () => {
    setBusy(true); setError("");
    try {
      const response = await apiFetch(`${base}/analytics/summary`);
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail ?? "Could not load analytics.");
      setData(result);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not load analytics."); }
    finally { setBusy(false); }
  }, [base]);
  useEffect(() => { void load(); }, [load]);

  function download() {
    if (!data) return;
    const rows = [["Metric", "Value"], ...Object.entries(data.totals).map(([key, value]) => [key.replaceAll("_", " "), String(value)]), ["Room utilization (%)", String(data.room_utilization_percent)], ...data.daily_sessions.map(item => [`${weekdays[item.day]} sessions`, String(item.sessions)])];
    const csv = rows.map(row => row.map(value => `"${value.replaceAll('"', '""')}"`).join(",")).join("\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    const link = document.createElement("a"); link.href = url; link.download = "dayleaf-analytics.csv"; link.click(); URL.revokeObjectURL(url);
  }

  const maxDay = Math.max(1, ...(data?.daily_sessions.map(item => item.sessions) ?? []));
  return <section className="analytics-workspace">
    <div className="analytics-heading"><div><span className="panel-kicker">CAMPUS PERFORMANCE</span><h2>Analytics & reports</h2><p>Live metrics from your campus records and published timetables · {data?.scope ?? "your workspace"}</p></div><div><button className="button button-quiet" onClick={() => void load()} disabled={busy}><RefreshCw size={14}/> Refresh</button><button className="button button-primary" onClick={download} disabled={!data}><Download size={14}/> Export summary</button></div></div>
    {error && <div className="notice error-notice">{error}</div>}
    {busy && !data ? <div className="analytics-loading panel">Loading campus metrics…</div> : data && <>
      <div className="analytics-metrics">
        <AnalyticCard icon={<CalendarDays size={17}/>} label="Scheduled sessions" value={data.totals.scheduled_sessions} note={`${data.totals.published_timetables} published timetable${data.totals.published_timetables === 1 ? "" : "s"}`} />
        <AnalyticCard icon={<Users size={17}/>} label="Faculty" value={data.totals.faculty} note={`${data.totals.sections} active sections`} />
        <AnalyticCard icon={<GraduationCap size={17}/>} label="Students" value={data.totals.students} note={`${data.totals.departments} departments`} />
        <AnalyticCard icon={<DoorOpen size={17}/>} label="Room utilization" value={`${data.room_utilization_percent}%`} note={`${data.totals.rooms} rooms in scope`} />
      </div>
      <div className="analytics-columns"><article className="panel analytics-panel"><div className="analytics-panel-heading"><div><span className="panel-kicker">PUBLISHED SCHEDULE</span><h3>Sessions by day</h3></div><Activity size={17}/></div>{data.daily_sessions.some(item => item.sessions > 0) ? <div className="day-bars">{data.daily_sessions.map(item => <div className="day-bar-row" key={item.day}><span>{weekdays[item.day]?.slice(0, 3)}</span><div><i style={{ width: `${Math.max(4, item.sessions / maxDay * 100)}%` }}/></div><b>{item.sessions}</b></div>)}</div> : <div className="analytics-empty">Publish a timetable to see scheduled sessions here.</div>}<small className="analytics-caption">{data.selected_timetables.map(item => `${item.name} · v${item.version}`).join("  /  ") || "No published timetable selected"}</small></article>
      <article className="panel analytics-panel"><div className="analytics-panel-heading"><div><span className="panel-kicker">TEACHING LOAD</span><h3>Faculty sessions</h3></div><Users size={17}/></div>{data.faculty_load.length ? <div className="load-list">{data.faculty_load.map((item, index) => <div className="load-row" key={item.id}><span className="load-rank">{String(index + 1).padStart(2, "0")}</span><b>{item.name}</b><span>{item.sessions} sessions</span></div>)}</div> : <div className="analytics-empty">Faculty workload appears once a timetable is published.</div>}</article></div>
      <div className={`conflict-banner ${data.totals.open_conflicts ? "has-conflicts" : "clear-conflicts"}`}><span>{data.totals.open_conflicts ? <AlertTriangle size={17}/> : <Activity size={17}/>}</span><div><b>{data.totals.open_conflicts ? `${data.totals.open_conflicts} schedule conflict${data.totals.open_conflicts === 1 ? "" : "s"} found` : "Published schedule checks are clear"}</b><small>Conflict count is calculated from published timetables in your access scope.</small></div></div>
      <ReportsWorkspace/>
    </>}
  </section>;
}

function AnalyticCard({ icon, label, value, note }: { icon: React.ReactNode; label: string; value: string | number; note: string }) {
  return <article className="analytics-card panel"><span>{icon}</span><small>{label}</small><b>{value}</b><i>{note}</i></article>;
}
