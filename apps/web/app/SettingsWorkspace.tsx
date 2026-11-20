"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { Building2, Check, Clock3, Save, UserRound } from "lucide-react";
import { apiFetch } from "./api-client";
import NotificationPreferences from "./NotificationPreferences";
import "./calendar-settings.css";

type CalendarBreak = { weekday: number; start_time: string; end_time: string };
const weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
type Settings = { profile: { full_name: string; email: string; role: string }; institution: { name: string; timezone: string; timetable_period_start: string; timetable_period_minutes: number; timetable_breaks: CalendarBreak[] } | null; can_manage_institution: boolean };
type ManagedAdmin = { id: string; full_name: string; email: string; is_active: boolean; email_verified: boolean };
type ManagedInstitution = { id: string; name: string; timezone: string; timetable_period_start: string; timetable_period_minutes: number; timetable_breaks: CalendarBreak[]; department_count: number; admins: ManagedAdmin[] };

function CalendarBreakEditor({ breaks, onChange }: { breaks: CalendarBreak[]; onChange: (items: CalendarBreak[]) => void }) {
  return <div className="calendar-break-editor"><div><b>Recurring campus breaks</b><small>Breaks block overlapping sessions on these weekdays in the campus timezone.</small></div>{breaks.map((item, index) => <div className="calendar-break-row" key={`${index}-${item.weekday}`}><select aria-label="Break weekday" value={item.weekday} onChange={event => onChange(breaks.map((row, i) => i === index ? { ...row, weekday: Number(event.target.value) } : row))}>{weekdays.map((day, weekday) => <option key={day} value={weekday}>{day}</option>)}</select><input aria-label="Break starts" type="time" required value={item.start_time} onChange={event => onChange(breaks.map((row, i) => i === index ? { ...row, start_time: event.target.value } : row))}/><span>to</span><input aria-label="Break ends" type="time" required value={item.end_time} onChange={event => onChange(breaks.map((row, i) => i === index ? { ...row, end_time: event.target.value } : row))}/><button type="button" className="button button-quiet" onClick={() => onChange(breaks.filter((_, i) => i !== index))}>Remove</button></div>)}<button type="button" className="button button-quiet" onClick={() => onChange([...breaks, { weekday: 0, start_time: "12:00", end_time: "13:00" }])}>Add recurring break</button></div>;
}

export default function SettingsWorkspace({ onNameChange }: { onNameChange: (name: string) => void }) {
  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
  const [settings, setSettings] = useState<Settings | null>(null);
  const [profileName, setProfileName] = useState("");
  const [institutionName, setInstitutionName] = useState("");
  const [timezone, setTimezone] = useState("");
  const [periodStart, setPeriodStart] = useState("09:00");
  const [periodMinutes, setPeriodMinutes] = useState(60);
  const [institutionBreaks, setInstitutionBreaks] = useState<CalendarBreak[]>([]);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [busy, setBusy] = useState(false);
  const [institutions, setInstitutions] = useState<ManagedInstitution[]>([]);
  const [newInstitution, setNewInstitution] = useState({ name: "", timezone: "Asia/Kolkata", timetable_period_start: "09:00", timetable_period_minutes: 60, timetable_breaks: [] as CalendarBreak[] });
  const [adminDrafts, setAdminDrafts] = useState<Record<string, { full_name: string; email: string }>>({});
  const loadInstitutions = useCallback(async () => {
    const response = await apiFetch(`${base}/superadmin/institutions`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail ?? "Could not load the institution directory.");
    setInstitutions(data);
  }, [base]);
  const load = useCallback(async () => {
    try {
      const response = await apiFetch(`${base}/settings`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Could not load settings.");
      setSettings(data); setProfileName(data.profile.full_name);
      setInstitutionName(data.institution?.name ?? ""); setTimezone(data.institution?.timezone ?? "Asia/Kolkata");
      setPeriodStart(data.institution?.timetable_period_start ?? "09:00"); setPeriodMinutes(data.institution?.timetable_period_minutes ?? 60);
      setInstitutionBreaks(data.institution?.timetable_breaks ?? []);
      if (data.profile.role === "super_admin") await loadInstitutions();
    } catch (e) { setError(e instanceof Error ? e.message : "Could not load settings."); }
  }, [base, loadInstitutions]);
  useEffect(() => { void load(); }, [load]);

  async function submitProfile(event: FormEvent) {
    event.preventDefault(); setError(""); setSuccess(""); setBusy(true);
    try {
      const response = await apiFetch(`${base}/settings/profile`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ full_name: profileName }) });
      const data = await response.json(); if (!response.ok) throw new Error(data.detail ?? "Could not update your profile.");
      onNameChange(data.full_name); setProfileName(data.full_name); setSuccess("Profile saved.");
    } catch (e) { setError(e instanceof Error ? e.message : "Could not update your profile."); }
    finally { setBusy(false); }
  }

  async function submitInstitution(event: FormEvent) {
    event.preventDefault(); setError(""); setSuccess(""); setBusy(true);
    try {
      const response = await apiFetch(`${base}/settings/institution`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: institutionName, timezone, timetable_period_start: periodStart, timetable_period_minutes: periodMinutes, timetable_breaks: institutionBreaks }) });
      const data = await response.json(); if (!response.ok) throw new Error(data.detail ?? "Could not update institution settings.");
      setSettings(current => current ? { ...current, institution: data } : current); setSuccess("Institution settings saved.");
    } catch (e) { setError(e instanceof Error ? e.message : "Could not update institution settings."); }
    finally { setBusy(false); }
  }

  async function createInstitution(event: FormEvent) {
    event.preventDefault(); setError(""); setSuccess(""); setBusy(true);
    try {
      const response = await apiFetch(`${base}/superadmin/institutions`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(newInstitution) });
      const data = await response.json(); if (!response.ok) throw new Error(data.detail ?? "Could not create institution.");
      setNewInstitution({ name: "", timezone: "Asia/Kolkata", timetable_period_start: "09:00", timetable_period_minutes: 60, timetable_breaks: [] }); await loadInstitutions(); setSuccess(`${data.name} created.`);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not create institution."); }
    finally { setBusy(false); }
  }

  async function saveManagedInstitution(institution: ManagedInstitution) {
    setError(""); setSuccess(""); setBusy(true);
    try {
      const response = await apiFetch(`${base}/superadmin/institutions/${institution.id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: institution.name, timezone: institution.timezone, timetable_period_start: institution.timetable_period_start, timetable_period_minutes: institution.timetable_period_minutes, timetable_breaks: institution.timetable_breaks ?? [] }) });
      const data = await response.json(); if (!response.ok) throw new Error(data.detail ?? "Could not update institution.");
      setInstitutions(current => current.map(item => item.id === data.id ? { ...item, ...data } : item)); setSuccess(`${data.name} settings saved.`);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not update institution."); }
    finally { setBusy(false); }
  }

  async function inviteAdmin(event: FormEvent, institutionId: string) {
    event.preventDefault(); setError(""); setSuccess(""); setBusy(true);
    const draft = adminDrafts[institutionId] ?? { full_name: "", email: "" };
    try {
      const response = await apiFetch(`${base}/superadmin/institutions/${institutionId}/admins`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(draft) });
      const data = await response.json(); if (!response.ok) throw new Error(data.detail ?? "Could not invite college admin.");
      setAdminDrafts(current => ({ ...current, [institutionId]: { full_name: "", email: "" } }));
      await loadInstitutions(); setSuccess(`Setup invitation sent to ${data.email}.`);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not invite college admin."); }
    finally { setBusy(false); }
  }

  async function manageAdmin(institutionId: string, admin: ManagedAdmin, action: "resend" | "toggle") {
    setError(""); setSuccess(""); setBusy(true);
    try {
      const path = `${base}/superadmin/institutions/${institutionId}/admins/${admin.id}`;
      const response = action === "resend"
        ? await apiFetch(`${path}/resend-setup`, { method: "POST" })
        : await apiFetch(`${path}/status`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ is_active: !admin.is_active }) });
      const data = await response.json(); if (!response.ok) throw new Error(data.detail ?? "Could not update college admin.");
      await loadInstitutions(); setSuccess(action === "resend" ? `Setup link sent to ${admin.email}.` : `${admin.full_name} ${data.is_active ? "reactivated" : "deactivated"}.`);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not update college admin."); }
    finally { setBusy(false); }
  }

  return <section className="settings-workspace"><div className="settings-page-heading"><div><span className="panel-kicker">CAMPUS PREFERENCES</span><h2>Settings</h2><p>Manage your account and campus defaults.</p></div></div>{error && <div className="notice error-notice">{error}</div>}{success && <div className="settings-success"><Check size={14}/>{success}</div>}
    <form className="settings-form panel" onSubmit={submitProfile}><div className="settings-form-heading"><span><UserRound size={17}/></span><div><b>Your profile</b><small>Update the name shown across Dayleaf.</small></div></div><label>Full name<input required minLength={2} maxLength={160} value={profileName} onChange={event => setProfileName(event.target.value)}/></label><label>Email address<input value={settings?.profile.email ?? ""} disabled/><small>Email changes require account verification.</small></label><div className="settings-form-foot"><span className="role-chip">{settings?.profile.role.replaceAll("_", " ") ?? "Loading account…"}</span><button className="button button-primary" type="submit" disabled={busy || !settings}><Save size={14}/> Save profile</button></div></form>
    {settings?.can_manage_institution && settings.institution && <form className="settings-form panel" onSubmit={submitInstitution}><div className="settings-form-heading"><span><Building2 size={17}/></span><div><b>Institution</b><small>Set the campus label and default timezone.</small></div></div><label>Institution name<input required minLength={2} maxLength={180} value={institutionName} onChange={event => setInstitutionName(event.target.value)}/></label><label><span className="field-with-icon"><Clock3 size={13}/> IANA timezone</span><input required value={timezone} onChange={event => setTimezone(event.target.value)} placeholder="Asia/Kolkata"/><small>Example: Asia/Kolkata, Europe/London, America/New_York</small></label><label>First period starts<input type="time" required value={periodStart} onChange={event => setPeriodStart(event.target.value)}/></label><label>Period length (minutes)<input type="number" min={20} max={180} required value={periodMinutes} onChange={event => setPeriodMinutes(Number(event.target.value))}/></label><CalendarBreakEditor breaks={institutionBreaks} onChange={setInstitutionBreaks}/><div className="settings-form-foot"><span className="settings-hint">Saved to the institution profile.</span><button className="button button-primary" type="submit" disabled={busy}><Save size={14}/> Save institution</button></div></form>}
    {settings?.profile.role === "super_admin" && <div className="superadmin-directory"><div className="settings-form-heading"><span><Building2 size={17}/></span><div><b>Institution directory</b><small>Create campuses, update their defaults, and manage college-admin access.</small></div></div>
      <form className="settings-form panel" onSubmit={createInstitution}><label>Institution name<input required minLength={2} maxLength={180} value={newInstitution.name} onChange={event => setNewInstitution(current => ({ ...current, name: event.target.value }))}/></label><label>IANA timezone<input required value={newInstitution.timezone} onChange={event => setNewInstitution(current => ({ ...current, timezone: event.target.value }))}/></label><label>First period starts<input type="time" required value={newInstitution.timetable_period_start} onChange={event => setNewInstitution(current => ({ ...current, timetable_period_start: event.target.value }))}/></label><label>Period length (minutes)<input type="number" min={20} max={180} required value={newInstitution.timetable_period_minutes} onChange={event => setNewInstitution(current => ({ ...current, timetable_period_minutes: Number(event.target.value) }))}/></label><CalendarBreakEditor breaks={newInstitution.timetable_breaks} onChange={items => setNewInstitution(current => ({ ...current, timetable_breaks: items }))}/><button className="button button-primary" disabled={busy}><Building2 size={14}/> Create institution</button></form>
      {institutions.map(institution => <article className="settings-form panel" key={institution.id}><div className="settings-form-heading"><span><Building2 size={17}/></span><div><b>{institution.name}</b><small>{institution.department_count} departments · {institution.admins.length} college admins</small></div></div><label>Institution name<input value={institution.name} onChange={event => setInstitutions(current => current.map(item => item.id === institution.id ? { ...item, name: event.target.value } : item))}/></label><label>IANA timezone<input value={institution.timezone} onChange={event => setInstitutions(current => current.map(item => item.id === institution.id ? { ...item, timezone: event.target.value } : item))}/></label><label>First period starts<input type="time" value={institution.timetable_period_start} onChange={event => setInstitutions(current => current.map(item => item.id === institution.id ? { ...item, timetable_period_start: event.target.value } : item))}/></label><label>Period length (minutes)<input type="number" min={20} max={180} value={institution.timetable_period_minutes} onChange={event => setInstitutions(current => current.map(item => item.id === institution.id ? { ...item, timetable_period_minutes: Number(event.target.value) } : item))}/></label><CalendarBreakEditor breaks={institution.timetable_breaks ?? []} onChange={items => setInstitutions(current => current.map(item => item.id === institution.id ? { ...item, timetable_breaks: items } : item))}/><button className="button button-quiet" onClick={() => void saveManagedInstitution(institution)} disabled={busy}><Save size={14}/> Save changes</button>
        <div className="managed-admin-list"><b>College administrators</b>{institution.admins.map(admin => <div className="managed-admin-row" key={admin.id}><span>{admin.full_name} · {admin.email} <small>{admin.is_active ? admin.email_verified ? "Active · verified" : "Active · setup pending" : "Deactivated"}</small></span><div><button className="button button-quiet" onClick={() => void manageAdmin(institution.id, admin, "resend")} disabled={busy || !admin.is_active}>Resend setup</button><button className="button button-quiet" onClick={() => void manageAdmin(institution.id, admin, "toggle")} disabled={busy}>{admin.is_active ? "Deactivate" : "Reactivate"}</button></div></div>)}
          <form className="managed-admin-invite" onSubmit={event => void inviteAdmin(event, institution.id)}><label>Admin name<input required minLength={2} maxLength={160} value={adminDrafts[institution.id]?.full_name ?? ""} onChange={event => setAdminDrafts(current => ({ ...current, [institution.id]: { ...current[institution.id], full_name: event.target.value, email: current[institution.id]?.email ?? "" } }))}/></label><label>Admin email<input required type="email" value={adminDrafts[institution.id]?.email ?? ""} onChange={event => setAdminDrafts(current => ({ ...current, [institution.id]: { ...current[institution.id], email: event.target.value, full_name: current[institution.id]?.full_name ?? "" } }))}/></label><button className="button button-primary" disabled={busy}>Invite college admin</button></form>
        </div>
      </article>)}
    </div>}
    <NotificationPreferences/>
  </section>;
}
