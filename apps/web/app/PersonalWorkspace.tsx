"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Bell, CalendarDays, Check, Clock3, ExternalLink, RefreshCw } from "lucide-react";
import { apiFetch } from "./api-client";
import { useCampusEvents } from "./useCampusEvents";

type PersonalEntry = { id: string; timetable: string; version: number; term_id: string; term: string; academic_year: string; is_current_term: boolean; days: number; weekdays?: number[]; weekday?: number; periods_per_day: number; period_labels?: string[]; section: string; subject: string; subject_code: string; room: string; day: number; period: number; duration_periods: number };
type Notice = { id: string; title: string; body: string; read: boolean; created_at: string };
const dayNames = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

export default function PersonalWorkspace({ active, role, fullName, onNavigate }: { active: string; role: "faculty" | "student"; fullName: string; onNavigate: (section: string) => void }) {
  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
  const [entries, setEntries] = useState<PersonalEntry[]>([]);
  const [notifications, setNotifications] = useState<Notice[]>([]);
  const [termId, setTermId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

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

  return <section className="personal-workspace">
    <div className="personal-heading"><div><span className="panel-kicker">{role === "student" ? "STUDENT WORKSPACE" : "FACULTY WORKSPACE"}</span><h2><CalendarDays size={21}/> {active === "Overview" ? `Good to see you, ${fullName.split(" ")[0]}.` : "My timetable"}</h2><p>{role === "student" ? "Your published class schedule, all in one place." : "Your teaching schedule and room assignments."}</p></div><div className="personal-actions"><button className="button button-quiet" onClick={() => void load()} disabled={loading}><RefreshCw size={14}/> Refresh</button><button className="button button-primary" onClick={() => onNavigate("Notifications")}><Bell size={14}/> Notifications {unread > 0 && <span className="button-count">{unread}</span>}</button></div></div>
    {error && <div className="notice error-notice">{error}</div>}
    <div className="personal-summary"><div><span className="summary-icon"><CalendarDays size={17}/></span><span><small>PUBLISHED CLASSES</small><b>{shown.length}</b></span></div><div><span className="summary-icon amber"><Clock3 size={17}/></span><span><small>UNREAD UPDATES</small><b>{unread}</b></span></div><div><span className="summary-icon green"><Check size={17}/></span><span><small>STATUS</small><b>{shown.length ? "Up to date" : "Awaiting publish"}</b></span></div></div>
    <section className="personal-panel panel"><div className="personal-schedule-heading"><div><div className="panel-kicker">PUBLISHED SCHEDULE</div><h3>{shown[0]?.term ? `${shown[0].term} · ${shown[0].academic_year}` : "Your weekly schedule"}</h3></div>{terms.length > 1 && <label className="term-picker">Term<select value={termId} onChange={event => setTermId(event.target.value)}>{terms.map(term => <option key={term.term_id} value={term.term_id}>{term.term} · {term.academic_year}</option>)}</select></label>}</div>
      {loading ? <div className="personal-empty">Loading your published schedule…</div> : shown.length ? <div className="personal-grid-wrap"><div className="personal-grid" style={{ gridTemplateColumns: `58px repeat(${dayCount}, minmax(100px, 1fr))` }}><div className="saved-day-head time">PERIOD</div>{visibleWeekdays.map(day => <div className="saved-day-head" key={day}>{dayNames[day]?.slice(0, 3) ?? `D${day + 1}`}</div>)}{schedulePeriodLabels.map(time => <div className="saved-row" key={time}><div className="saved-time">{time}</div>{visibleWeekdays.map(weekday => <div className="saved-slot" key={weekday}>{shown.filter(entry => (entry.weekday ?? entry.weekdays?.[entry.day] ?? entry.day) === weekday && (entry.period_labels?.[entry.period] ?? `${String(9 + entry.period).padStart(2, "0")}:00`) === time).map(entry => <article className="personal-class" key={entry.id}><b>{entry.subject}</b><small>{entry.subject_code} · {entry.room}</small>{role === "faculty" && <small>{entry.section}</small>}</article>)}</div>)}</div>)}</div></div> : <div className="personal-empty"><span><CalendarDays size={23}/></span><b>No published timetable yet</b><small>{role === "student" ? "Your college admin will publish your section schedule here." : "Your assigned teaching sessions will appear after your department publishes a timetable."}</small></div>}
      <div className="personal-foot"><span><i/> Showing published timetable versions only</span><button onClick={() => onNavigate("Notifications")}>View notifications <ExternalLink size={12}/></button></div>
    </section>
  </section>;
}
