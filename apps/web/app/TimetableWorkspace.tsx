"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { CalendarDays, Check, ChevronDown, Clock3, Download, GripVertical, LockKeyhole, Redo2, Sparkles, Undo2, WandSparkles } from "lucide-react";
import { apiFetch } from "./api-client";
import "./approval.css";

type Option = { id: string; name?: string; code?: string; number?: number; semester_number?: number; is_current?: boolean; academic_year?: string; semester_id?: string; department_id?: string; term_id?: string };
type TimetableInfo = { id: string; name: string; status: string; approval_status?: string; approval_note?: string | null; version: number; term_id: string; department_id: string; days?: number; weekdays?: number[]; periods_per_day?: number; period_labels?: string[]; score?: number };
type ApprovalInfo = { id: string; name: string; version: number; term_id: string; term: string; department_id: string; department: string; requested_by_name: string; requested_at: string };
type Entry = { id: string; subject: string; section: string; section_id?: string; faculty: string; room: string; room_id?: string; day: number; period: number; duration_periods: number; is_locked?: boolean };
type MoveLocation = { day: number; period: number; room_id?: string; room: string };
type MoveHistory = { entryId: string; from: MoveLocation; to: MoveLocation };
type SlotSuggestion = { day: number; period: number; score: number; reason: string; room_id: string; room: string };
type TimetableIssue = { entry_ids: string[]; category: string; day: number; weekday?: number; periods: number[]; reason: string };
class ApiError extends Error { constructor(message: string, readonly status: number, readonly detail: unknown) { super(message); } }
const dayNames = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const periods = ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00", "20:00", "21:00", "22:00"];

export default function TimetableWorkspace({ onNavigate }: { onNavigate: (page: string) => void }) {
  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
  const [terms, setTerms] = useState<Option[]>([]);
  const [departments, setDepartments] = useState<Option[]>([]);
  const [sections, setSections] = useState<Option[]>([]);
  const [versions, setVersions] = useState<TimetableInfo[]>([]);
  const [approvals, setApprovals] = useState<ApprovalInfo[]>([]);
  const [userRole, setUserRole] = useState("");
  const [termId, setTermId] = useState("");
  const [departmentId, setDepartmentId] = useState("");
  const [weekdaysToSchedule, setWeekdaysToSchedule] = useState([0, 1, 2, 3, 4]);
  const [periodsToSchedule, setPeriodsToSchedule] = useState(8);
  const [maximumPeriods, setMaximumPeriods] = useState(14);
  const [sectionId, setSectionId] = useState("");
  const [selected, setSelected] = useState<TimetableInfo | null>(null);
  const [entries, setEntries] = useState<Entry[]>([]);
  const [issues, setIssues] = useState<TimetableIssue[]>([]);
  const [undoHistory, setUndoHistory] = useState<MoveHistory[]>([]);
  const [redoHistory, setRedoHistory] = useState<MoveHistory[]>([]);
  const [name, setName] = useState("Semester timetable");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [refresh, setRefresh] = useState(0);
  const [dragging, setDragging] = useState<Entry | null>(null);
  const [suggestions, setSuggestions] = useState<{ entry: Entry; slots: SlotSuggestion[] } | null>(null);
  const entriesRef = useRef(entries);
  const selectedTimetableId = selected?.id;

  useEffect(() => { entriesRef.current = entries; }, [entries]);

  const request = useCallback(async (path: string, init?: RequestInit) => {
    const response = await apiFetch(`${base}${path}`, { ...init, headers: { ...(init?.headers ?? {}) } });
    const body = response.status === 204 ? null : await response.json();
    if (!response.ok) {
      const detail = body?.detail;
      const message = Array.isArray(detail) ? detail.map(item => item.msg).join(". ") : typeof detail === "object" ? detail.message ?? "Request failed." : detail ?? "Request failed.";
      const conflicts = Array.isArray(detail?.conflicts) ? detail.conflicts.map((item: { day: number; weekday?: number; periods: number[]; reason: string }) => `${dayNames[item.weekday ?? item.day] ?? `Day ${item.day + 1}`} periods ${item.periods.join("–")}: ${item.reason}`).join("; ") : "";
      const diagnostics = Array.isArray(detail?.diagnostics) ? detail.diagnostics.map((item: { category?: string; subject?: string; required_room_type?: string; minimum_capacity?: number; blocked_slots?: number; institution_breaks?: boolean; suspected_constraints?: string[] }) => {
        if (item.category === "room_eligibility") return `${item.subject}: no room matches ${item.required_room_type} with capacity ${item.minimum_capacity}.`;
        if (item.category === "time_availability") return `${item.subject}: no period fits its duration and availability${item.institution_breaks ? ", including campus-wide breaks" : ""} (${item.blocked_slots} faculty-blocked slots).`;
        if (item.category === "combined_constraints") return `Review these constraints: ${(item.suspected_constraints ?? []).join(", ")}.`;
        if (item.category === "solver_limit") return "The optimizer needs a simpler or less restricted request to finish within its search limit.";
        return "The optimizer found a constraint issue; review room eligibility, availability, and weekly limits.";
      }).join(" ") : "";
      throw new ApiError([message, conflicts, diagnostics].filter(Boolean).join(" "), response.status, detail);
    }
    return body;
  }, [base]);

  useEffect(() => {
    setBusy(true); setError("");
    Promise.all([request("/campus/terms"), request("/campus/departments"), request("/campus/sections"), request("/campus/timetables"), request("/auth/me"), request("/settings")])
      .then(([termRows, departmentRows, sectionRows, timetableRows, viewer, settings]) => {
        setTerms(termRows); setDepartments(departmentRows); setSections(sectionRows); setVersions(timetableRows);
        setUserRole(viewer.role);
        if (settings.institution) {
          const [hour, minute] = settings.institution.timetable_period_start.split(":").map(Number);
          setMaximumPeriods(Math.min(14, Math.floor((1440 - (hour * 60 + minute)) / settings.institution.timetable_period_minutes)));
        }
        setTermId(current => current || termRows.find((term: Option) => term.is_current)?.id || termRows[0]?.id || "");
        setDepartmentId(current => current || departmentRows[0]?.id || "");
        if (timetableRows.length) {
          setSelected(timetableRows[0]);
          setWeekdaysToSchedule(timetableRows[0].weekdays ?? Array.from({ length: timetableRows[0].days ?? 5 }, (_, index) => index));
          setPeriodsToSchedule(timetableRows[0].periods_per_day ?? 8);
        }
        if (["super_admin", "college_admin"].includes(viewer.role)) request("/campus/timetables/approvals").then(setApprovals).catch(e => setError(e instanceof Error ? e.message : "Could not load approval requests."));
        else setApprovals([]);
      }).catch(e => setError(e instanceof Error && e.message === "Sign in required." ? "Sign in with a college admin or HOD account to generate and edit timetables." : e instanceof Error ? e.message : "Could not load timetable setup."))
      .finally(() => setBusy(false));
  }, [request, refresh]);

  useEffect(() => {
    if (!selected) { setEntries([]); return; }
    request(`/campus/timetables/${selected.id}/entries`).then(setEntries).catch(e => setError(e instanceof Error ? e.message : "Could not load this timetable."));
  }, [request, selected]);

  useEffect(() => {
    if (!selected) { setIssues([]); return; }
    request(`/campus/timetables/${selected.id}/conflicts`)
      .then(result => setIssues(result.conflicts ?? []))
      .catch(() => setIssues([]));
  }, [request, selected, entries]);

  useEffect(() => {
    if (!selectedTimetableId || busy) return;
    let active = true;
    let streamConnected = false;
    const syncEntries = async () => {
      if (!active || document.visibilityState !== "visible") return;
      try {
        const latest: Entry[] = await request(`/campus/timetables/${selectedTimetableId}/entries`);
        if (!active) return;
        if (JSON.stringify(entriesRef.current) !== JSON.stringify(latest)) {
          setEntries(latest);
          setNotice("This timetable changed in another session. The latest saved schedule is now shown.");
          setUndoHistory([]);
          setRedoHistory([]);
        }
      } catch {
        // Keep the last successful snapshot; the next poll can recover from transient network errors.
      }
    };
    const syncCampusState = async () => {
      await syncEntries();
      try {
        const latest: TimetableInfo[] = await request("/campus/timetables");
        if (!active) return;
        setVersions(latest);
        setSelected(current => current ? latest.find(item => item.id === current.id) ?? current : current);
        if (["super_admin", "college_admin"].includes(userRole)) {
          const latestApprovals: ApprovalInfo[] = await request("/campus/timetables/approvals");
          if (active) setApprovals(latestApprovals);
        }
      } catch {
        // The normal screen requests and fallback synchronization can recover after a transient failure.
      }
    };
    let source: EventSource | null = null;
    if (typeof EventSource !== "undefined") {
      source = new EventSource(`${base}/events`, { withCredentials: true });
      source.onopen = () => { streamConnected = true; };
      source.onerror = () => { streamConnected = false; };
      source.addEventListener("campus.refresh", () => void syncCampusState());
    }
    const timer = window.setInterval(() => {
      if (!streamConnected) void syncCampusState();
    }, 8000);
    return () => { active = false; source?.close(); window.clearInterval(timer); };
  }, [base, request, selectedTimetableId, busy, userRole]);

  useEffect(() => {
    setUndoHistory([]); setRedoHistory([]);
  }, [selected?.id]);

  const matchingSections = useMemo(() => sections.filter(section => (!section.department_id || section.department_id === departmentId) && (!section.term_id || section.term_id === termId)), [sections, departmentId, termId]);
  const visibleEntries = useMemo(() => sectionId ? entries.filter(entry => entry.section_id === sectionId) : entries, [entries, sectionId]);
  const periodLabels = selected?.period_labels?.length ? selected.period_labels : periods;

  useEffect(() => {
    if (sectionId && !matchingSections.some(section => section.id === sectionId)) setSectionId("");
  }, [matchingSections, sectionId]);

  async function generate() {
    if (!termId || !departmentId) { setError("Create an academic term and department before generating a timetable."); return; }
    setBusy(true); setError(""); setNotice("");
    try {
      const result = await request("/campus/timetables/generate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ term_id: termId, department_id: departmentId, section_id: sectionId || null, name, days: weekdaysToSchedule.length, weekdays: weekdaysToSchedule, periods_per_day: periodsToSchedule }) });
      const info: TimetableInfo = { id: result.id, name: result.name, status: result.status, approval_status: result.approval_status ?? "not_requested", version: result.version, term_id: termId, department_id: departmentId, days: weekdaysToSchedule.length, weekdays: weekdaysToSchedule, periods_per_day: periodsToSchedule, period_labels: result.period_labels, score: result.score };
      setSelected(info); setEntries(result.entries); setVersions(current => [info, ...current]);
      setNotice(`Version ${result.version} saved as a draft with ${result.entries.length} sessions. Check the schedule, then publish when ready.`);
    } catch (e) { setError(e instanceof Error ? e.message : "The solver could not build a timetable."); }
    finally { setBusy(false); }
  }

  async function loadVersion(id: string) {
    const info = versions.find(item => item.id === id);
    setSelected(info ?? null); setError("");
    setSuggestions(null);
    if (info) {
      setTermId(info.term_id); setDepartmentId(info.department_id);
      setWeekdaysToSchedule(info.weekdays ?? Array.from({ length: info.days ?? 5 }, (_, index) => index)); setPeriodsToSchedule(info.periods_per_day ?? 8);
    }
  }

  async function moveEntry(entry: Entry, day: number, period: number, room?: { id: string; name: string }, recordHistory = true): Promise<boolean> {
    if (!selected || entry.is_locked || selected.status !== "draft" || selected.approval_status === "pending") return false;
    setBusy(true); setError(""); setNotice(""); setSuggestions(null);
    const from: MoveLocation = { day: entry.day, period: entry.period, room_id: entry.room_id, room: entry.room };
    try {
      const result = await request(`/campus/timetables/${selected.id}/entries/${entry.id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ day, period, ...(room ? { room_id: room.id } : {}) }) });
      setEntries(current => current.map(item => item.id === entry.id ? { ...item, day, period, room: result.room, room_id: result.room_id } : item));
      if (recordHistory) {
        setUndoHistory(current => [...current.slice(-49), { entryId: entry.id, from, to: { day, period, room_id: result.room_id, room: result.room } }]);
        setRedoHistory([]);
      }
      setNotice(`${entry.subject} moved to ${dayNames[selected?.weekdays?.[day] ?? day]} at ${periodLabels[period] ?? `Period ${period + 1}`}${room ? ` in ${room.name}` : ""}. The API checked room, faculty, section, availability and campus-break conflicts.`);
      return true;
    } catch (e) {
      setError(e instanceof Error ? e.message : "That move could not be saved.");
      const apiError = e instanceof ApiError ? e : null;
      if (selected && apiError?.status === 409 && typeof apiError.detail === "object" && apiError.detail !== null && "conflicts" in apiError.detail) {
        try {
          const result = await request(`/campus/timetables/${selected.id}/entries/${entry.id}/suggestions`);
          setSuggestions({ entry, slots: result.suggestions });
        } catch { setSuggestions(null); }
      }
      return false;
    }
    finally { setBusy(false); setDragging(null); }
  }

  async function findRepairOptions(entry: Entry) {
    if (!selected || selected.status !== "draft" || selected.approval_status === "pending" || entry.is_locked || busy) return;
    setBusy(true); setError(""); setSuggestions(null);
    try {
      const result = await request(`/campus/timetables/${selected.id}/entries/${entry.id}/suggestions`);
      setSuggestions({ entry, slots: result.suggestions });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not find a valid repair for this session.");
    } finally { setBusy(false); }
  }

  async function repairTimetable() {
    if (!selected || selected.status !== "draft" || selected.approval_status === "pending" || busy || !issues.length) return;
    setBusy(true); setError(""); setNotice(""); setSuggestions(null);
    try {
      const result = await request(`/campus/timetables/${selected.id}/repair`, { method: "POST" });
      setEntries(result.entries);
      setIssues(result.conflicts ?? []);
      setUndoHistory([]); setRedoHistory([]);
      setNotice(result.moved_count ? `The optimizer repaired the timetable by rescheduling ${result.moved_count} session${result.moved_count === 1 ? "" : "s"}. Review the updated draft before publishing.` : "The timetable is conflict-free; no sessions needed to move.");
    } catch (e) { setError(e instanceof Error ? e.message : "The optimizer could not repair this timetable. Review the individual issue suggestions."); }
    finally { setBusy(false); }
  }

  async function undoMove() {
    const history = undoHistory[undoHistory.length - 1];
    if (!history || busy) return;
    const entry = entries.find(item => item.id === history.entryId);
    if (!entry) { setError("This timetable changed. The undo history has been cleared."); setUndoHistory([]); setRedoHistory([]); return; }
    if (entry.day !== history.to.day || entry.period !== history.to.period || entry.room_id !== history.to.room_id) {
      setError("This session changed since the move. The undo history has been cleared to protect the current schedule.");
      setUndoHistory([]); setRedoHistory([]); return;
    }
    const restored = await moveEntry(entry, history.from.day, history.from.period,
      history.from.room_id ? { id: history.from.room_id, name: history.from.room } : undefined, false);
    if (restored) {
      setUndoHistory(current => current.slice(0, -1));
      setRedoHistory(current => [...current.slice(-49), history]);
      setNotice(`Undid the move for ${entry.subject}. The API rechecked schedule constraints.`);
    }
  }

  async function redoMove() {
    const history = redoHistory[redoHistory.length - 1];
    if (!history || busy) return;
    const entry = entries.find(item => item.id === history.entryId);
    if (!entry) { setError("This timetable changed. The redo history has been cleared."); setUndoHistory([]); setRedoHistory([]); return; }
    if (entry.day !== history.from.day || entry.period !== history.from.period || entry.room_id !== history.from.room_id) {
      setError("This session changed since the undo. The redo history has been cleared to protect the current schedule.");
      setUndoHistory([]); setRedoHistory([]); return;
    }
    const restored = await moveEntry(entry, history.to.day, history.to.period,
      history.to.room_id ? { id: history.to.room_id, name: history.to.room } : undefined, false);
    if (restored) {
      setRedoHistory(current => current.slice(0, -1));
      setUndoHistory(current => [...current.slice(-49), history]);
      setNotice(`Redid the move for ${entry.subject}. The API rechecked schedule constraints.`);
    }
  }

  async function publish() {
    if (!selected) return;
    setBusy(true); setError(""); setNotice(""); setSuggestions(null);
    try {
      const result = await request(`/campus/timetables/${selected.id}/publish`, { method: "POST" });
      setSelected(current => current ? { ...current, status: result.status, approval_status: result.approval_status, approval_note: null } : current);
      setVersions(current => current.map(item => item.id === result.id ? { ...item, status: result.status, approval_status: result.approval_status, approval_note: null } : item));
      setNotice(`Version ${result.version} is now published for this department and term.`);
      setRefresh(value => value + 1);
    } catch (e) { setError(e instanceof Error ? e.message : "The timetable could not be published."); }
    finally { setBusy(false); }
  }

  async function requestApproval() {
    if (!selected) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const result = await request(`/campus/timetables/${selected.id}/request-approval`, { method: "POST" });
      setSelected(current => current ? { ...current, approval_status: result.approval_status, approval_note: null } : current);
      setVersions(current => current.map(item => item.id === selected.id ? { ...item, approval_status: result.approval_status, approval_note: null } : item));
      setNotice("Timetable sent to the college admin for review. Editing is locked until they decide.");
    } catch (e) { setError(e instanceof Error ? e.message : "Could not request approval."); }
    finally { setBusy(false); }
  }

  async function decideApproval(approval: ApprovalInfo, decision: "approve" | "reject") {
    const note = decision === "reject" ? window.prompt("Add a short reason so the department head knows what to change:") : "";
    if (decision === "reject" && (note === null || note.trim().length < 2)) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const result = await request(`/campus/timetables/${approval.id}/approval`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ decision, note }) });
      setApprovals(current => current.filter(item => item.id !== approval.id));
      setVersions(current => current.map(item => item.id === approval.id ? { ...item, status: result.status, approval_status: result.approval_status, approval_note: decision === "reject" ? note : null } : item));
      setSelected(current => current?.id === approval.id ? { ...current, status: result.status, approval_status: result.approval_status, approval_note: decision === "reject" ? note : null } : current);
      setNotice(decision === "approve" ? `${approval.name} approved and published.` : `${approval.name} returned to ${approval.requested_by_name} for changes.`);
      setRefresh(value => value + 1);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not review this timetable."); }
    finally { setBusy(false); }
  }

  function exportCsv() {
    const csv = ["Day,Period,Subject,Section,Faculty,Room", ...visibleEntries.map(entry => `${dayNames[selected?.weekdays?.[entry.day] ?? entry.day]},${periodLabels[entry.period] ?? `Period ${entry.period + 1}`},${entry.subject},${entry.section},${entry.faculty},${entry.room}`)].join("\n");
    const anchor = document.createElement("a"); anchor.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" })); anchor.download = `${selected?.name ?? "timetable"}-v${selected?.version ?? 1}.csv`; anchor.click(); URL.revokeObjectURL(anchor.href);
  }

  return <section className="timetable-workspace">
    <div className="timetable-heading"><div><span className="panel-kicker">SCHEDULE STUDIO</span><h2><CalendarDays size={21}/> Timetable planner</h2><p>Build a conflict-free draft from your campus records, review it, and publish it when ready.</p></div><div className="timetable-heading-actions">{selected && <button className="button button-quiet" onClick={exportCsv}><Download size={15}/> Export CSV</button>}{selected?.status === "draft" && selected.approval_status !== "pending" && <><button className="button button-quiet" onClick={() => void undoMove()} disabled={busy || !undoHistory.length} title="Undo last saved move"><Undo2 size={15}/> Undo</button><button className="button button-quiet" onClick={() => void redoMove()} disabled={busy || !redoHistory.length} title="Redo last undone move"><Redo2 size={15}/> Redo</button></>}{selected?.status === "draft" && userRole === "hod" && selected.approval_status !== "pending" && <button className="button button-primary" onClick={() => void requestApproval()} disabled={busy}><Check size={15}/>{selected.approval_status === "rejected" ? "Resubmit for approval" : "Request approval"}</button>}{selected?.status === "draft" && ["college_admin", "super_admin"].includes(userRole) && selected.approval_status !== "pending" && <button className="button button-primary" onClick={() => void publish()} disabled={busy}><Check size={15}/> Publish draft</button>}</div></div>
    {error && <div className="notice error-notice" role="alert">{error}{error.includes("Sign in") && <a href="/sign-in">Sign in <ChevronDown size={12}/></a>}</div>}{notice && <div className="notice" role="status" aria-live="polite"><Check size={16}/><span>{notice}</span><button onClick={() => setNotice("")}>×</button></div>}
    {["college_admin", "super_admin"].includes(userRole) && approvals.length > 0 && <div className="approval-queue panel"><div className="approval-queue-title"><div><span className="panel-kicker">REVIEW QUEUE</span><h3>Timetables awaiting approval</h3></div><span>{approvals.length} pending</span></div>{approvals.map(item => <div className="approval-item" key={item.id}><div><b>{item.name} · v{item.version}</b><small>{item.department} · {item.term} · submitted by {item.requested_by_name}</small></div><div className="approval-actions"><button className="button button-quiet" disabled={busy} onClick={() => { void loadVersion(item.id); window.scrollTo({ top: 0, behavior: "smooth" }); }}>Review</button><button className="button button-quiet" disabled={busy} onClick={() => void decideApproval(item, "reject")}>Return</button><button className="button button-primary" disabled={busy} onClick={() => void decideApproval(item, "approve")}>Approve & publish</button></div></div>)}</div>}
    <div className="planner-layout"><div className="planner-controls panel"><div className="panel-kicker">BUILD A DRAFT</div><h3><WandSparkles size={16}/> Constraint optimizer</h3><p>Uses weekly teaching assignments, faculty availability, workload limits, room capacity and lab requirements.</p>
      <label>Academic term<select value={termId} onChange={e => setTermId(e.target.value)}><option value="">{terms.length ? "Choose a term" : busy ? "Loading terms…" : "No terms yet"}</option>{terms.map(item => <option key={item.id} value={item.id}>{item.name} · {item.academic_year}</option>)}</select></label>
      <label>Department<select value={departmentId} onChange={e => setDepartmentId(e.target.value)}><option value="">{departments.length ? "Choose a department" : busy ? "Loading departments…" : "No departments yet"}</option>{departments.map(item => <option key={item.id} value={item.id}>{item.name} · {item.code}</option>)}</select></label>
      <label>Section <span className="optional-label">Optional · all department sections</span><select value={sectionId} onChange={e => setSectionId(e.target.value)}><option value="">All sections</option>{matchingSections.map(item => <option key={item.id} value={item.id}>{item.name} · Semester {item.semester_number}</option>)}</select></label>
      {!busy && (!terms.length || !departments.length) && <div className="setup-next-step" role="status"><span><b>Set up your campus first</b><br/>{!departments.length ? "Add a department" : "Add an academic term"} in Academics; it will appear in this list.</span><button type="button" onClick={() => onNavigate("Academics")}>Open Academics</button></div>}
      <div className="calendar-dimension-fields"><fieldset className="weekday-picker"><legend>Teaching days · {weekdaysToSchedule.length} selected</legend><div className="day-presets"><button type="button" aria-pressed={weekdaysToSchedule.join(",") === "0,1,2,3,4"} onClick={() => setWeekdaysToSchedule([0,1,2,3,4])}>Weekdays</button><button type="button" aria-pressed={weekdaysToSchedule.join(",") === "0,1,2,3,4,5,6"} onClick={() => setWeekdaysToSchedule([0,1,2,3,4,5,6])}>All 7 days</button></div><div>{dayNames.map((day, index) => <label key={day}><input type="checkbox" checked={weekdaysToSchedule.includes(index)} aria-label={day} onChange={() => setWeekdaysToSchedule(current => current.includes(index) ? (current.length > 1 ? current.filter(item => item !== index) : current) : [...current, index].sort((a, b) => a - b))}/>{day}</label>)}</div></fieldset><label>Periods per day<select value={periodsToSchedule} onChange={event => setPeriodsToSchedule(Number(event.target.value))}>{Array.from({ length: maximumPeriods }, (_, index) => index + 1).map(count => <option key={count} value={count}>{count} periods</option>)}</select></label></div>
      <label>Draft name<input value={name} onChange={e => setName(e.target.value)} maxLength={140}/></label>
      <button className="generate-action" disabled={busy || !terms.length || !departments.length} onClick={generate}><Sparkles size={16}/>{busy ? "Working…" : "Generate a new version"}<span>CP-SAT</span></button>
      <div className="planner-note"><Clock3 size={14}/> Generating saves a new draft version. Published timetables stay available while you review changes.</div>
    </div>
    <div className="planner-result panel"><div className="planner-result-head"><div><div className="panel-kicker">SAVED SCHEDULE</div><h3>{selected?.name ?? "Your timetable will appear here"}</h3></div>{selected && <div className={`status-pill ${selected.approval_status === "pending" ? "approval-pending" : selected.approval_status === "rejected" ? "approval-rejected" : selected.status}`}>● {selected.approval_status === "pending" ? "awaiting approval" : selected.approval_status === "rejected" ? "returned for changes" : `${selected.status} · v${selected.version}`}</div>}</div>
      {selected?.approval_status === "rejected" && selected.approval_note && <div className="approval-note">Admin feedback: {selected.approval_note}</div>}
      {issues.length > 0 && <div className="notice error-notice" role="status"><div><b>{issues.length} schedule issue{issues.length === 1 ? "" : "s"} found</b>{selected?.status === "draft" && selected.approval_status !== "pending" && <button className="button button-quiet" disabled={busy} onClick={() => void repairTimetable()}><WandSparkles size={13}/>{busy ? "Repairing…" : "Repair timetable with optimizer"}</button>}<ul>{issues.map((issue, index) => {
        const affectedEntries = issue.entry_ids.map(id => entries.find(entry => entry.id === id)).filter((entry): entry is Entry => Boolean(entry));
        return <li key={`${issue.category}-${issue.entry_ids.join("-")}-${index}`}>
          {dayNames[issue.weekday ?? selected?.weekdays?.[issue.day] ?? issue.day] ?? `Day ${issue.day + 1}`} · periods {issue.periods.join("–")}: {issue.reason}
          {affectedEntries.map(entry => <button key={entry.id} className="button button-quiet" onClick={() => void findRepairOptions(entry)} disabled={busy || entry.is_locked || selected?.status !== "draft" || selected.approval_status === "pending"}>Find a fix for {entry.subject} · {entry.section}</button>)}
        </li>;
      })}</ul></div></div>}
      {versions.length > 0 && <div className="version-row"><label>Version<select value={selected?.id ?? ""} onChange={e => void loadVersion(e.target.value)}>{versions.map(item => <option key={item.id} value={item.id}>{item.name} · v{item.version} · {item.status}</option>)}</select></label><span>{versions.length} saved version{versions.length === 1 ? "" : "s"}</span></div>}
      {suggestions && <div className="slot-suggestions"><div className="slot-suggestions-heading"><div><b>Open alternatives for {suggestions.entry.subject}</b><small>{suggestions.entry.section} · {suggestions.entry.duration_periods} period{suggestions.entry.duration_periods === 1 ? "" : "s"}. These options avoid resource and faculty availability and campus break conflicts.</small></div><button onClick={() => setSuggestions(null)} aria-label="Close suggestions">×</button></div>{suggestions.slots.length ? <div className="suggestion-options">{suggestions.slots.map(slot => <button key={`${slot.day}-${slot.period}-${slot.room_id}`} onClick={() => void moveEntry(suggestions.entry, slot.day, slot.period, { id: slot.room_id, name: slot.room })} disabled={busy}><span>{dayNames[selected?.weekdays?.[slot.day] ?? slot.day]} · {periodLabels[slot.period] ?? `Period ${slot.period + 1}`}</span><small>{slot.room} · {slot.reason}</small></button>)}</div> : <div className="suggestion-empty">No open slot or suitable room fits this session in the current draft. Try generating a new version or changing availability and assignments.</div>}</div>}
      {selected && (() => { const selectedWeekdays = selected.weekdays ?? Array.from({ length: selected.days ?? 5 }, (_, index) => index); return <div className="saved-grid-wrap">{selected.status === "draft" && selected.approval_status !== "pending" && <p className="timetable-keyboard-help">Keyboard editing: focus a session, then use arrow keys to move it by one day or period. The same conflict checks apply.</p>}<div className="saved-grid" style={{ gridTemplateColumns: `59px repeat(${selectedWeekdays.length}, minmax(105px, 1fr))` }}><div className="saved-day-head time">PERIOD</div>{selectedWeekdays.map(day => <div className="saved-day-head" key={day}>{dayNames[day].slice(0, 3)}</div>)}{periodLabels.slice(0, selected.periods_per_day ?? 8).map((period, pi) => <div className="saved-row" key={period}><div className="saved-time">{period}</div>{selectedWeekdays.map((_, di) => <div className="saved-slot" key={di} onDragOver={event => event.preventDefault()} onDrop={event => { event.preventDefault(); if (dragging) void moveEntry(dragging, di, pi); }}>{visibleEntries.filter(entry => entry.day === di && entry.period === pi).map(entry => <button key={entry.id} data-session-id={entry.id} draggable={!entry.is_locked && selected.status === "draft" && selected.approval_status !== "pending"} aria-keyshortcuts={selected.status === "draft" && selected.approval_status !== "pending" && !entry.is_locked ? "ArrowLeft ArrowRight ArrowUp ArrowDown" : undefined} aria-label={`${entry.subject}, ${entry.section}, ${dayNames[selectedWeekdays[entry.day]]}, ${periodLabels[entry.period] ?? `Period ${entry.period + 1}`}, ${entry.room}${selected.status === "draft" && selected.approval_status !== "pending" && !entry.is_locked ? ". Use arrow keys to reschedule." : ""}`} onKeyDown={async event => { if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event.key) || entry.is_locked || selected.status !== "draft" || selected.approval_status === "pending") return; event.preventDefault(); const nextDay = entry.day + (event.key === "ArrowLeft" ? -1 : event.key === "ArrowRight" ? 1 : 0); const nextPeriod = entry.period + (event.key === "ArrowUp" ? -1 : event.key === "ArrowDown" ? 1 : 0); if (nextDay < 0 || nextDay >= selectedWeekdays.length || nextPeriod < 0 || nextPeriod + entry.duration_periods > (selected.periods_per_day ?? 8)) { setNotice("That move would go beyond this timetable’s days or periods."); return; } const moved = await moveEntry(entry, nextDay, nextPeriod); if (moved) window.requestAnimationFrame(() => document.querySelector<HTMLButtonElement>(`[data-session-id="${entry.id}"]`)?.focus()); }} onDragStart={() => setDragging(entry)} onDragEnd={() => setDragging(null)} onClick={() => setNotice(`${entry.subject} · ${entry.section} · ${entry.room} · ${entry.faculty}`)} className="saved-session"><span className="session-title"><GripVertical size={10}/>{entry.subject}{entry.is_locked && <LockKeyhole size={9}/>}</span><small>{entry.section} · {entry.room}</small><small>{entry.faculty}{entry.duration_periods > 1 ? ` · ${entry.duration_periods} periods` : ""}</small></button>)}</div>)}</div>)}</div></div>; })()}
      <div className="planner-result-foot"><span><i/> Hard checks: room, section, faculty, availability and campus breaks</span><span>Soft score: lower is better</span></div>
    </div></div>
  </section>;
}
