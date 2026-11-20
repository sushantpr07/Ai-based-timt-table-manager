"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Bell, BookOpen, CalendarDays, Check, Clock3, ExternalLink, GraduationCap, RefreshCw } from "lucide-react";
import { apiFetch } from "./api-client";
import { useCampusEvents } from "./useCampusEvents";

type PersonalEntry = { id: string; timetable: string; version: number; term_id: string; term: string; academic_year: string; is_current_term: boolean; days: number; weekdays?: number[]; weekday?: number; periods_per_day: number; period_labels?: string[]; section: string; subject: string; subject_code: string; room: string; day: number; period: number; duration_periods: number };
type Notice = { id: string; title: string; body: string; read: boolean; created_at: string };
const dayNames = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

export default function PersonalWorkspace({ active, role, fullName, viewer, onNavigate }: { active: string; role: "faculty" | "student"; fullName: string; viewer?: any; onNavigate: (section: string) => void }) {
  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
  const [entries, setEntries] = useState<PersonalEntry[]>([]);
  const [notifications, setNotifications] = useState<Notice[]>([]);
  const [termId, setTermId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [meta, setMeta] = useState<{
    department?: string | null;
    department_code?: string | null;
    section?: string | null;
    semester?: number | null;
    student_number?: string | null;
  }>({});

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const [scheduleResponse, noticeResponse] = await Promise.all([
        apiFetch(`${base}/me/schedule`),
        apiFetch(`${base}/me/notifications`),
      ]);
      if (!scheduleResponse.ok || !noticeResponse.ok) throw new Error("Could not load your workspace. Sign in again to refresh the session.");
      const schedule = await scheduleResponse.json();
      const notices = await noticeResponse.json();
      setEntries(schedule.entries);
      setNotifications(notices);
      setMeta({
        department: schedule.department,
        department_code: schedule.department_code,
        section: schedule.section,
        semester: schedule.semester,
        student_number: schedule.student_number,
      });
      setTermId(current => current || schedule.entries.find((entry: PersonalEntry) => entry.is_current_term)?.term_id || schedule.entries[0]?.term_id || "");
    } catch (e) { setError(e instanceof Error ? e.message : "Could not load your workspace."); }
    finally { setLoading(false); }
  }, [base]);

  useEffect(() => { void load(); }, [load]);
  useCampusEvents(() => { void load(); }, active === "Notifications");

  const terms = useMemo(() => Array.from(new Map(entries.map(entry => [entry.term_id, entry])).values()), [entries]);
  const shown = useMemo(() => termId ? entries.filter(entry => entry.term_id === termId) : entries, [entries, termId]);
  const visibleWeekdays = Array.from(new Set(shown.flatMap(entry => entry.weekdays ?? Array.from({ length: entry.days }, (_, index) => index)))).sort((a, b) => a - b);
  const dayCount = visibleWeekdays.length;
  const schedulePeriodLabels = Array.from(new Set(shown.flatMap(entry => entry.period_labels ?? Array.from({ length: entry.periods_per_day }, (_, index) => `${String(9 + index).padStart(2, "0")}:00`)))).sort((a, b) => a.localeCompare(b));
  const unread = notifications.filter(item => !item.read).length;

  async function markRead(item: Notice) {
    if (item.read) return;
    const response = await apiFetch(`${base}/me/notifications/${item.id}/read`, { method: "PATCH" });
    if (response.ok) setNotifications(current => current.map(row => row.id === item.id ? { ...row, read: true } : row));
  }

  async function markAllRead() {
    const response = await apiFetch(`${base}/me/notifications/read-all`, { method: "POST" });
    if (response.ok) setNotifications(current => current.map(item => ({ ...item, read: true })));
  }

  if (active === "Notifications") return <section className="personal-panel panel"><div className="personal-heading"><div><span className="panel-kicker">YOUR CAMPUS UPDATES</span><h2><Bell size={20}/> Notifications {unread > 0 && <span className="unread-count">{unread}</span>}</h2><p>Schedule changes and campus updates sent to you.</p></div>{unread > 0 && <button className="button button-quiet" onClick={() => void markAllRead()}><Check size={14}/> Mark all read</button>}</div>{error && <div className="notice error-notice">{error}</div>}{loading ? <div className="personal-empty">Loading your notifications…</div> : notifications.length ? <div className="notification-list">{notifications.map(item => <article key={item.id} className={`notification-item ${item.read ? "read" : "unread"}`} onClick={() => void markRead(item)}><span className="notification-icon"><Bell size={16}/></span><div><b>{item.title}</b><p>{item.body}</p><small>{new Date(item.created_at).toLocaleString()}</small></div><button aria-label="Mark as read" onClick={event => { event.stopPropagation(); void markRead(item); }}>{item.read ? <Check size={15}/> : <span className="unread-dot"/>}</button></article>)}</div> : <div className="personal-empty"><Bell size={22}/><b>You’re all caught up</b><small>New timetable announcements will show up here.</small></div>}</section>;

  if (active === "Settings") return <section className="personal-panel panel"><div className="personal-heading"><div><span className="panel-kicker">ACCOUNT PREFERENCES</span><h2>Settings</h2><p>Signed in as {fullName}. Notification and profile preferences are next in the rollout.</p></div></div><div className="settings-preview"><Bell size={18}/><span><b>Timetable announcements</b><small>We’ll show schedule updates in your Dayleaf notifications.</small></span><span className="enabled-pill">On</span></div></section>;

  if (active === "Department") {
    const deptName = viewer?.department || meta.department || "Computer Science & Engineering";
    const deptCode = viewer?.department_code || meta.department_code || "CSE";
    const secName = viewer?.section || meta.section || "A";
    const semNum = viewer?.semester || meta.semester || 3;
    const rollNum = viewer?.student_number || meta.student_number || "DL2026CSE001";

    return (
      <section className="personal-panel panel">
        <div className="personal-heading">
          <div>
            <span className="panel-kicker">ACADEMIC DEPARTMENT</span>
            <h2><GraduationCap size={22}/> {deptName} ({deptCode})</h2>
            <p>Your department details, enrolled section, and academic faculty.</p>
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px", marginTop: "20px" }}>
          <div className="stat-card" style={{ padding: "18px", borderRadius: "12px", background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)" }}>
            <small style={{ color: "#94a3b8", fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.05em" }}>DEPARTMENT</small>
            <h3 style={{ fontSize: "18px", margin: "6px 0 2px 0", color: "#f8fafc" }}>{deptName}</h3>
            <span style={{ fontSize: "12px", color: "#c084fc", fontWeight: 600 }}>Code: {deptCode}</span>
          </div>

          <div className="stat-card" style={{ padding: "18px", borderRadius: "12px", background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)" }}>
            <small style={{ color: "#94a3b8", fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.05em" }}>ENROLLED CLASS</small>
            <h3 style={{ fontSize: "18px", margin: "6px 0 2px 0", color: "#f8fafc" }}>Semester {semNum} · Section {secName}</h3>
            <span style={{ fontSize: "12px", color: "#60a5fa", fontWeight: 600 }}>Academic Year 2026-27</span>
          </div>

          <div className="stat-card" style={{ padding: "18px", borderRadius: "12px", background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)" }}>
            <small style={{ color: "#94a3b8", fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.05em" }}>STUDENT IDENTITY</small>
            <h3 style={{ fontSize: "18px", margin: "6px 0 2px 0", color: "#f8fafc" }}>{fullName}</h3>
            <span style={{ fontSize: "12px", color: "#34d399", fontWeight: 600 }}>Roll No: {rollNum}</span>
          </div>

          <div className="stat-card" style={{ padding: "18px", borderRadius: "12px", background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)" }}>
            <small style={{ color: "#94a3b8", fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.05em" }}>HEAD OF DEPARTMENT (HOD)</small>
            <h3 style={{ fontSize: "18px", margin: "6px 0 2px 0", color: "#f8fafc" }}>
              {deptCode === "CSE" ? "Dr. Rajesh Raman" : deptCode === "CYS" ? "Dr. Aditi Rao" : deptCode === "DS" ? "Dr. Neha Kulkarni" : "Dr. Vikram Malhotra"}
            </h3>
            <span style={{ fontSize: "12px", color: "#e2e8f0" }}>hod.{deptCode.toLowerCase()}@dayleaf.edu</span>
          </div>
        </div>

        <div style={{ marginTop: "24px", padding: "18px", borderRadius: "12px", background: "rgba(168, 85, 247, 0.05)", border: "1px solid rgba(168, 85, 247, 0.2)" }}>
          <h4 style={{ margin: "0 0 8px 0", fontSize: "15px", color: "#c084fc", display: "flex", alignItems: "center", gap: "8px" }}>
            <BookOpen size={16}/> Enrolled Department Curriculum ({deptCode} Semester {semNum})
          </h4>
          <p style={{ margin: 0, fontSize: "13px", color: "#94a3b8", lineHeight: 1.6 }}>
            Your class schedule is automatically synchronized with the department master timetable generated by the Dayleaf constraint solver. 
            All lectures, lab sessions, and classroom allocations (Section {secName}) are updated in real-time.
          </p>
        </div>
      </section>
    );
  }

  return <section className="personal-workspace">
    <div className="personal-heading">
      <div>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap", marginBottom: "8px" }}>
          <span className="panel-kicker">{role === "student" ? "STUDENT WORKSPACE" : "FACULTY WORKSPACE"}</span>
          {meta.department && (
            <span style={{ 
              display: "inline-flex", 
              alignItems: "center", 
              gap: "5px", 
              background: "rgba(168, 85, 247, 0.15)", 
              color: "#c084fc", 
              padding: "3px 10px", 
              borderRadius: "6px", 
              fontSize: "12px", 
              fontWeight: 600,
              border: "1px solid rgba(168, 85, 247, 0.3)"
            }}>
              <GraduationCap size={13}/> {meta.department} ({meta.department_code})
            </span>
          )}
          {meta.section && (
            <span style={{ 
              display: "inline-flex", 
              alignItems: "center", 
              gap: "5px", 
              background: "rgba(59, 130, 246, 0.15)", 
              color: "#60a5fa", 
              padding: "3px 10px", 
              borderRadius: "6px", 
              fontSize: "12px", 
              fontWeight: 600,
              border: "1px solid rgba(59, 130, 246, 0.3)"
            }}>
              Semester {meta.semester ?? 3} · Section {meta.section}
            </span>
          )}
          {meta.student_number && (
            <span style={{ 
              display: "inline-flex", 
              alignItems: "center", 
              gap: "5px", 
              background: "rgba(16, 185, 129, 0.15)", 
              color: "#34d399", 
              padding: "3px 10px", 
              borderRadius: "6px", 
              fontSize: "12px", 
              fontWeight: 600,
              border: "1px solid rgba(16, 185, 129, 0.3)"
            }}>
              Roll: {meta.student_number}
            </span>
          )}
        </div>
        <h2><CalendarDays size={21}/> {active === "Overview" ? `Good to see you, ${fullName.split(" ")[0]}.` : "My timetable"}</h2>
        <p>{meta.department ? `${meta.department} · Class Schedule & Room Allocations` : (role === "student" ? "Your published class schedule, all in one place." : "Your teaching schedule and room assignments.")}</p>
      </div>
      <div className="personal-actions">
        <button className="button button-quiet" onClick={() => void load()} disabled={loading}><RefreshCw size={14}/> Refresh</button>
        <button className="button button-primary" onClick={() => onNavigate("Notifications")}><Bell size={14}/> Notifications {unread > 0 && <span className="button-count">{unread}</span>}</button>
      </div>
    </div>
    {error && <div className="notice error-notice">{error}</div>}
    <div className="personal-summary"><div><span className="summary-icon"><CalendarDays size={17}/></span><span><small>PUBLISHED CLASSES</small><b>{shown.length}</b></span></div><div><span className="summary-icon amber"><Clock3 size={17}/></span><span><small>UNREAD UPDATES</small><b>{unread}</b></span></div><div><span className="summary-icon green"><Check size={17}/></span><span><small>STATUS</small><b>{shown.length ? "Up to date" : "Awaiting publish"}</b></span></div></div>
    <section className="personal-panel panel"><div className="personal-schedule-heading"><div><div className="panel-kicker">PUBLISHED SCHEDULE</div><h3>{shown[0]?.term ? `${shown[0].term} · ${shown[0].academic_year}` : "Your weekly schedule"}</h3></div>{terms.length > 1 && <label className="term-picker">Term<select value={termId} onChange={event => setTermId(event.target.value)}>{terms.map(term => <option key={term.term_id} value={term.term_id}>{term.term} · {term.academic_year}</option>)}</select></label>}</div>
      {loading ? <div className="personal-empty">Loading your published schedule…</div> : shown.length ? <div className="personal-grid-wrap"><div className="personal-grid" style={{ gridTemplateColumns: `58px repeat(${dayCount}, minmax(100px, 1fr))` }}><div className="saved-day-head time">PERIOD</div>{visibleWeekdays.map(day => <div className="saved-day-head" key={day}>{dayNames[day]?.slice(0, 3) ?? `D${day + 1}`}</div>)}{schedulePeriodLabels.map(time => <div className="saved-row" key={time}><div className="saved-time">{time}</div>{visibleWeekdays.map(weekday => <div className="saved-slot" key={weekday}>{shown.filter(entry => (entry.weekday ?? entry.weekdays?.[entry.day] ?? entry.day) === weekday && (entry.period_labels?.[entry.period] ?? `${String(9 + entry.period).padStart(2, "0")}:00`) === time).map(entry => <article className="personal-class" key={entry.id}><b>{entry.subject}</b><small>{entry.subject_code} · {entry.room}</small>{role === "faculty" && <small>{entry.section}</small>}</article>)}</div>)}</div>)}</div></div> : <div className="personal-empty"><span><CalendarDays size={23}/></span><b>No published timetable yet</b><small>{role === "student" ? "Your college admin will publish your section schedule here." : "Your assigned teaching sessions will appear after your department publishes a timetable."}</small></div>}
      <div className="personal-foot"><span><i/> Showing published timetable versions only</span><button onClick={() => onNavigate("Notifications")}>View notifications <ExternalLink size={12}/></button></div>
    </section>
  </section>;
}
