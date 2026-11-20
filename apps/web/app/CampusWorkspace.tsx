"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ArrowRight, BookOpen, Building2, Check, Clock3, DoorOpen, Download, FileSpreadsheet, Pencil, Plus, RefreshCw, Save, Sparkles, Trash2, Users, X } from "lucide-react";
import { apiFetch } from "./api-client";

type Row = Record<string, string | number | boolean>;
type InstitutionOption = { id: string; name: string };
type Field = { key: string; label: string; type?: string; options?: string; defaultValue?: string };
type Resource = { key: string; title: string; endpoint: string; fields: Field[]; columns: { key: string; label: string }[] };

const academicResources: Resource[] = [
  { key: "departments", title: "Departments", endpoint: "departments", fields: [{ key: "name", label: "Department name" }, { key: "code", label: "Short code" }], columns: [{ key: "name", label: "Department" }, { key: "code", label: "Code" }] },
  { key: "terms", title: "Academic terms", endpoint: "terms", fields: [{ key: "name", label: "Term name" }, { key: "academic_year", label: "Academic year" }, { key: "is_current", label: "Current term", type: "checkbox" }], columns: [{ key: "name", label: "Term" }, { key: "academic_year", label: "Academic year" }, { key: "is_current", label: "Current" }] },
  { key: "subjects", title: "Subjects", endpoint: "subjects", fields: [{ key: "code", label: "Subject code" }, { key: "name", label: "Subject name" }, { key: "department_id", label: "Department", options: "departments" }, { key: "weekly_sessions", label: "Sessions / week", type: "number", defaultValue: "3" }, { key: "room_type", label: "Room type", options: "roomTypes" }], columns: [{ key: "code", label: "Code" }, { key: "name", label: "Subject" }, { key: "weekly_sessions", label: "Sessions / week" }] },
  { key: "semesters", title: "Semesters", endpoint: "semesters", fields: [{ key: "department_id", label: "Department", options: "departments" }, { key: "term_id", label: "Academic term", options: "terms" }, { key: "number", label: "Semester number", type: "number" }], columns: [{ key: "number", label: "Semester" }, { key: "department_id", label: "Department ID" }, { key: "term_id", label: "Term ID" }] },
  { key: "sections", title: "Sections", endpoint: "sections", fields: [{ key: "semester_id", label: "Semester", options: "semesters" }, { key: "name", label: "Section name" }, { key: "strength", label: "Student count", type: "number" }], columns: [{ key: "name", label: "Section" }, { key: "strength", label: "Students" }, { key: "semester_id", label: "Semester ID" }] },
  { key: "teaching-assignments", title: "Teaching assignments", endpoint: "teaching-assignments", fields: [{ key: "subject_id", label: "Subject", options: "subjects" }, { key: "section_id", label: "Section", options: "sections" }, { key: "faculty_id", label: "Faculty member", options: "people/faculty" }, { key: "sessions_per_week", label: "Sessions per week", type: "number", defaultValue: "3" }, { key: "duration_periods", label: "Period length", options: "durations" }], columns: [{ key: "subject", label: "Subject" }, { key: "section", label: "Section" }, { key: "faculty", label: "Faculty" }, { key: "sessions_per_week", label: "Sessions / week" }] },
];
const peopleResources: Resource[] = [
  { key: "faculty", title: "Faculty", endpoint: "people/faculty", fields: [{ key: "full_name", label: "Full name" }, { key: "email", label: "Work email", type: "email" }, { key: "department_id", label: "Department", options: "departments" }, { key: "max_weekly_periods", label: "Max periods / week", type: "number", defaultValue: "18" }], columns: [{ key: "full_name", label: "Faculty member" }, { key: "email", label: "Email" }, { key: "department_id", label: "Department" }, { key: "max_weekly_periods", label: "Weekly limit" }] },
  { key: "students", title: "Students", endpoint: "people/students", fields: [{ key: "full_name", label: "Full name" }, { key: "email", label: "Student email", type: "email" }, { key: "student_number", label: "Student number" }, { key: "section_id", label: "Section", options: "sections" }], columns: [{ key: "full_name", label: "Student" }, { key: "student_number", label: "Student number" }, { key: "email", label: "Email" }, { key: "section_id", label: "Section" }] },
  { key: "hods", title: "Department heads", endpoint: "people/hods", fields: [{ key: "full_name", label: "Full name" }, { key: "email", label: "Work email", type: "email" }, { key: "department_id", label: "Department", options: "departments" }], columns: [{ key: "full_name", label: "Department head" }, { key: "email", label: "Email" }, { key: "department_id", label: "Department" }] },
];
const roomResource: Resource = { key: "rooms", title: "Classrooms & labs", endpoint: "rooms", fields: [{ key: "name", label: "Room name" }, { key: "capacity", label: "Capacity", type: "number" }, { key: "room_type", label: "Room type", options: "roomTypes" }], columns: [{ key: "name", label: "Room" }, { key: "room_type", label: "Type" }, { key: "capacity", label: "Seats" }] };
const csvColumns: Record<string, string[]> = {
  departments: ["name", "code", "institution_id"],
  terms: ["name", "academic_year", "is_current", "institution_id"],
  rooms: ["name", "capacity", "room_type", "institution_id"],
  subjects: ["code", "name", "department_code", "weekly_sessions", "room_type", "institution_id"],
  semesters: ["department_code", "term_name", "academic_year", "number", "institution_id"],
  sections: ["department_code", "term_name", "academic_year", "semester_number", "name", "strength", "institution_id"],
  "teaching-assignments": ["department_code", "term_name", "academic_year", "semester_number", "section_name", "subject_code", "faculty_email", "sessions_per_week", "duration_periods", "institution_id"],
};
const weekDays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const periodTimes = ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00", "20:00", "21:00", "22:00"];

function parseCsv(text: string): { headers: string[]; rows: Record<string, string>[] } {
  const parsed: string[][] = [];
  let row: string[] = [], field = "", quoted = false;
  for (let index = 0; index < text.length; index++) {
    const char = text[index];
    if (quoted && char === '"' && text[index + 1] === '"') { field += '"'; index++; }
    else if (char === '"') quoted = !quoted;
    else if (char === "," && !quoted) { row.push(field); field = ""; }
    else if ((char === "\n" || char === "\r") && !quoted) {
      if (char === "\r" && text[index + 1] === "\n") index++;
      row.push(field); if (row.some(cell => cell.trim())) parsed.push(row);
      row = []; field = "";
    } else field += char;
  }
  if (quoted) throw new Error("This CSV has an unclosed quoted field.");
  if (field || row.length) { row.push(field); if (row.some(cell => cell.trim())) parsed.push(row); }
  if (!parsed.length) throw new Error("This CSV file is empty.");
  const headers = parsed[0].map(header => header.replace(/^\uFEFF/, "").trim().toLowerCase());
  if (headers.some(header => !header) || new Set(headers).size !== headers.length) throw new Error("The CSV header row has a blank or duplicate column.");
  const rows = parsed.slice(1).map((cells, index) => {
    if (cells.length !== headers.length) throw new Error(`Row ${index + 2} has ${cells.length} values; expected ${headers.length}.`);
    return Object.fromEntries(headers.map((header, cellIndex) => [header, cells[cellIndex].trim()]));
  });
  if (!rows.length) throw new Error("The CSV must include a header and at least one data row.");
  return { headers, rows };
}

export default function CampusWorkspace({ active, onNavigate }: { active: string; onNavigate: (page: string) => void }) {
  const catalog = active === "People" ? peopleResources : academicResources;
  const [resourceKey, setResourceKey] = useState(active === "People" ? "faculty" : active === "Classrooms" ? "rooms" : "departments");
  const resource = active === "Classrooms" ? roomResource : catalog.find(item => item.key === resourceKey) ?? catalog[0];
  const [rows, setRows] = useState<Row[]>([]);
  const [editing, setEditing] = useState<Row | null>(null);
  const [lookups, setLookups] = useState<Record<string, Row[]>>({});
  const [values, setValues] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [busy, setBusy] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const [userRole, setUserRole] = useState("");
  const [institutions, setInstitutions] = useState<InstitutionOption[]>([]);
  const [institutionId, setInstitutionId] = useState("");
  const [availabilityFaculty, setAvailabilityFaculty] = useState<Row | null>(null);
  const [blockedSlots, setBlockedSlots] = useState<Set<string>>(new Set());
  const [availabilityPeriods, setAvailabilityPeriods] = useState(8);
  const [availabilityPeriodTimes, setAvailabilityPeriodTimes] = useState(periodTimes);
  const [availabilityBusy, setAvailabilityBusy] = useState(false);
  const [importBusy, setImportBusy] = useState(false);
  const importInput = useRef<HTMLInputElement>(null);
  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

  const loadRows = useCallback(async (endpoint: string) => {
    const response = await apiFetch(`${base}/campus/${endpoint}`);
    if (!response.ok) throw new Error(response.status === 401 ? "Sign in to manage campus data." : (await response.json()).detail ?? "Could not load campus records.");
    return response.json() as Promise<Row[]>;
  }, [base]);

  useEffect(() => {
    apiFetch(`${base}/auth/me`).then(response => response.ok ? response.json() : null)
      .then(data => { if (data?.role) setUserRole(data.role); }).catch(() => undefined);
  }, [base]);

  useEffect(() => {
    if (userRole !== "super_admin") return;
    let activeRequest = true;
    apiFetch(`${base}/superadmin/institutions`).then(async response => {
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Could not load institutions.");
      return data as InstitutionOption[];
    }).then(data => {
      if (!activeRequest) return;
      setInstitutions(data);
      setInstitutionId(current => current || data[0]?.id || "");
    }).catch(e => { if (activeRequest) setError(e instanceof Error ? e.message : "Could not load institutions."); });
    return () => { activeRequest = false; };
  }, [base, userRole]);

  useEffect(() => {
    setError(""); setSuccess(""); setValues(Object.fromEntries(resource.fields.map(field => [field.key, field.defaultValue ?? ""])));
    setBusy(true);
    Promise.all([loadRows(resource.endpoint), ...resource.fields.filter(field => field.options && !["roomTypes", "durations"].includes(field.options)).map(field => loadRows(field.options!))])
      .then(([data, ...lookupsData]) => {
        setRows(data);
        const names = resource.fields.filter(field => field.options && !["roomTypes", "durations"].includes(field.options)).map(field => field.options!);
        setLookups(Object.fromEntries(names.map((name, index) => [name, lookupsData[index] as Row[]])));
      }).catch(e => setError(e instanceof Error ? e.message : "Could not load campus records."))
      .finally(() => setBusy(false));
  }, [base, resource.endpoint, resource.fields, loadRows, refresh]);

  function lookupOptions(name: string): Row[] {
    const candidates = lookups[name] ?? [];
    if (userRole !== "super_admin") return candidates;
    if (!institutionId) return [];
    if (name === "departments" || name === "terms") {
      return candidates.filter(item => String(item.institution_id ?? "") === institutionId);
    }
    const departmentIds = new Set((lookups.departments ?? [])
      .filter(item => String(item.institution_id ?? "") === institutionId).map(item => String(item.id)));
    if (["subjects", "semesters", "sections", "people/faculty", "people/hods"].includes(name)) {
      return candidates.filter(item => departmentIds.has(String(item.department_id ?? "")));
    }
    return candidates;
  }

  const displayRows = useMemo(() => {
    if (userRole !== "super_admin") return rows;
    if (!institutionId) return [];
    const departmentIds = new Set((lookups.departments ?? [])
      .filter(item => String(item.institution_id ?? "") === institutionId).map(item => String(item.id)));
    const sectionIds = new Set((lookups.sections ?? [])
      .filter(item => departmentIds.has(String(item.department_id ?? ""))).map(item => String(item.id)));
    if (["departments", "terms", "rooms"].includes(resource.endpoint)) {
      return rows.filter(item => String(item.institution_id ?? "") === institutionId);
    }
    if (["subjects", "semesters", "sections", "people/faculty", "people/hods"].includes(resource.endpoint)) {
      return rows.filter(item => departmentIds.has(String(item.department_id ?? "")));
    }
    if (["people/students", "teaching-assignments"].includes(resource.endpoint)) {
      return rows.filter(item => sectionIds.has(String(item.section_id ?? "")));
    }
    return rows;
  }, [rows, userRole, institutionId, lookups, resource.endpoint]);

  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(""); setSuccess("");
    const payload: Record<string, unknown> = {};
    const editablePeopleFields: Record<string, string[]> = {
      faculty: ["full_name", "department_id", "max_weekly_periods"],
      students: ["full_name", "section_id", "student_number"],
      hods: ["full_name", "department_id"],
    };
    const includedFields = editing && active === "People"
      ? editablePeopleFields[resource.key] ?? []
      : resource.fields.map(field => field.key);
    for (const field of resource.fields.filter(item => includedFields.includes(item.key))) {
      const value = values[field.key] ?? "";
      payload[field.key] = field.type === "number" ? Number(value) : field.type === "checkbox" ? value === "true" : value;
    }
    if (!editing && userRole === "super_admin" && ["departments", "terms", "rooms"].includes(resource.endpoint)) {
      if (!institutionId) { setError("Create or choose an institution before adding this record."); setBusy(false); return; }
      payload.institution_id = institutionId;
    }
    try {
      const path = editing
        ? active === "People" ? `${base}/campus/people/${resource.key}/${editing.id}` : `${base}/campus/records/${resource.endpoint}/${editing.id}`
        : `${base}/campus/${resource.endpoint}`;
      const response = await apiFetch(path, { method: editing ? "PATCH" : "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      const data = response.status === 204 ? null : await response.json();
      if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : data.detail?.message ?? "Could not save this record.");
      if (editing) { setEditing(null); setRefresh(value => value + 1); setSuccess(`${resource.title.slice(0, -1) || resource.title} updated.`); }
      else { setRows(current => [data, ...current]); setSuccess(`${resource.title.slice(0, -1) || resource.title} added.`); }
      setValues(Object.fromEntries(resource.fields.map(field => [field.key, field.defaultValue ?? ""])));
    } catch (e) { setError(e instanceof Error && e.message.includes("fetch") ? "Dayleaf API is offline. Start the API and try again." : (e as Error).message); }
    finally { setBusy(false); }
  }

  function beginEdit(row: Row) {
    setEditing(row); setError(""); setSuccess("");
    setValues(Object.fromEntries(resource.fields.map(field => [field.key, String(row[field.key] ?? field.defaultValue ?? "")] )));
  }

  async function removeRecord(row: Row) {
    if (!window.confirm(`Delete this ${resource.title.toLowerCase().replace(/s$/, "")}? Records in use cannot be deleted.`)) return;
    setError(""); setSuccess(""); setBusy(true);
    try {
      const response = await apiFetch(`${base}/campus/records/${resource.endpoint}/${row.id}`, { method: "DELETE" });
      const data = response.status === 204 ? null : await response.json();
      if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : data.detail?.message ?? "Could not delete this record.");
      setRows(current => current.filter(item => item.id !== row.id)); setSuccess(`${resource.title.slice(0, -1) || resource.title} deleted.`);
      if (editing?.id === row.id) { setEditing(null); setValues(Object.fromEntries(resource.fields.map(field => [field.key, field.defaultValue ?? ""]))); }
    } catch (e) { setError(e instanceof Error ? e.message : "Could not delete this record."); }
    finally { setBusy(false); }
  }

  async function resendSetup(row: Row) {
    setError(""); setSuccess(""); setBusy(true);
    try {
      const response = await apiFetch(`${base}/campus/people/accounts/${row.user_id}/resend-setup`, { method: "POST" });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Could not send a setup link.");
      setSuccess(`A new setup link was sent to ${String(row.email)}. Earlier links have been invalidated.`);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not send a setup link."); }
    finally { setBusy(false); }
  }

  async function changeAccountStatus(row: Row) {
    const nextActive = !Boolean(row.is_active);
    if (!nextActive && !window.confirm(`Deactivate ${String(row.full_name)}? Their next API request will require an active account.`)) return;
    setError(""); setSuccess(""); setBusy(true);
    try {
      const response = await apiFetch(`${base}/campus/people/accounts/${row.user_id}/status`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ is_active: nextActive }) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Could not update account access.");
      setRows(current => current.map(item => item.user_id === row.user_id ? { ...item, is_active: data.is_active } : item));
      setSuccess(`${String(row.full_name)} ${nextActive ? "reactivated" : "deactivated"}.`);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not update account access."); }
    finally { setBusy(false); }
  }

  function downloadTemplate() {
    const headers = csvColumns[resource.endpoint];
    if (!headers) return;
    const blobUrl = URL.createObjectURL(new Blob([`${headers.join(",")}\r\n`], { type: "text/csv;charset=utf-8" }));
    const anchor = document.createElement("a"); anchor.href = blobUrl; anchor.download = `dayleaf-${resource.endpoint}-template.csv`; anchor.click(); URL.revokeObjectURL(blobUrl);
  }

  async function importCsv(file?: File) {
    if (!file) return;
    setError(""); setSuccess(""); setImportBusy(true);
    try {
      if (file.size > 2_000_000) throw new Error("CSV files must be smaller than 2 MB.");
      const parsed = parseCsv(await file.text());
      const allowed = csvColumns[resource.endpoint] ?? [];
      const unknown = parsed.headers.filter(header => !allowed.includes(header));
      if (unknown.length) throw new Error(`Unknown column${unknown.length === 1 ? "" : "s"}: ${unknown.join(", ")}. Download the template for this record type.`);
      let importRows = parsed.rows;
      if (userRole === "super_admin") {
        if (!institutionId) throw new Error("Create or choose an institution before importing campus records.");
        if (parsed.rows.some(row => row.institution_id && row.institution_id !== institutionId)) throw new Error("This import includes an institution ID outside the selected institution.");
        importRows = parsed.rows.map(row => ({ ...row, institution_id: institutionId }));
      }
      const response = await apiFetch(`${base}/campus/import/${resource.endpoint}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ rows: importRows }) });
      const result = await response.json();
      if (!response.ok) throw new Error(typeof result.detail === "string" ? result.detail : result.detail?.message ?? "Could not import these rows.");
      setSuccess(`${result.created_count} row${result.created_count === 1 ? "" : "s"} imported${result.error_count ? `; ${result.error_count} need attention` : " successfully"}.`);
      if (result.error_count) setError([...result.errors.slice(0, 8).map((item: { row: number; message: string }) => `Row ${item.row}: ${item.message}`), ...(result.error_count > 8 ? [`Showing 8 of ${result.error_count} row errors.`] : [])].join("\n"));
      if (result.created_count) setRefresh(value => value + 1);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not import this CSV file."); }
    finally { setImportBusy(false); if (importInput.current) importInput.current.value = ""; }
  }

  async function editAvailability(faculty: Row) {
    setError(""); setSuccess(""); setAvailabilityBusy(true);
    try {
      const response = await apiFetch(`${base}/campus/people/faculty/${faculty.id}/availability`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Could not load faculty availability.");
      setAvailabilityFaculty(faculty);
      setBlockedSlots(new Set(data.unavailable.map((slot: { day: number; period: number }) => `${slot.day}:${slot.period}`)));
      const labels = Array.isArray(data.period_labels) && data.period_labels.length ? data.period_labels : periodTimes;
      setAvailabilityPeriodTimes(labels);
      setAvailabilityPeriods(Math.min(8, labels.length));
    } catch (e) { setError(e instanceof Error ? e.message : "Could not load faculty availability."); }
    finally { setAvailabilityBusy(false); }
  }

  async function saveAvailability() {
    if (!availabilityFaculty) return;
    setError(""); setSuccess(""); setAvailabilityBusy(true);
    const unavailable = [...blockedSlots].map(value => { const [day, period] = value.split(":").map(Number); return { day, period }; });
    try {
      const response = await apiFetch(`${base}/campus/people/faculty/${availabilityFaculty.id}/availability`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ unavailable }) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Could not save faculty availability.");
      setSuccess(`Availability saved for ${availabilityFaculty.full_name}.`); setAvailabilityFaculty(null);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not save faculty availability."); }
    finally { setAvailabilityBusy(false); }
  }

  function displayValue(row: Row, key: string) {
    const value = row[key];
    if (key.endsWith("_id") && typeof value === "string") {
      const listKey = key === "department_id" ? "departments" : key === "term_id" ? "terms" : key === "section_id" ? "sections" : key === "faculty_id" ? "people/faculty" : key === "subject_id" ? "subjects" : "semesters";
      const related = lookups[listKey]?.find(item => item.id === value);
      return related?.name ?? (related?.number ? `Semester ${related.number}` : `${value.slice(0, 8)}…`);
    }
    if (typeof value === "boolean") return value ? "Yes" : "No";
    return value ?? "—";
  }

  const title = active === "Classrooms" ? "Classrooms & labs" : active === "People" ? "People & access" : "Academic structure";
  const displayTitle = resource.title.toLowerCase().includes("classroom") ? "Classroom / lab" : resource.title.endsWith("s") ? resource.title.slice(0, -1) : resource.title;
  return <section className="workspace-card panel">
    <div className="workspace-heading"><div className="workspace-icon"><Building2 size={18}/></div><div><div className="panel-kicker">CAMPUS SETUP</div><h2>{title}</h2><p>Manage the campus records used by timetable planning.</p></div><button className="square-button refresh-button" aria-label="Refresh records" onClick={() => { setRefresh(value => value + 1); setSuccess(""); }}><RefreshCw size={15}/></button></div>
    <div className="workspace-body">
      {active !== "Classrooms" && <div className="resource-tabs">{catalog.filter(item => item.key !== "hods" || userRole === "college_admin" || userRole === "super_admin").map(item => <button key={item.key} className={resource.key === item.key ? "active" : ""} onClick={() => { setEditing(null); setResourceKey(item.key); }}>{item.title}</button>)}</div>}
      {userRole === "super_admin" && <div className="institution-context"><Building2 size={15}/><label>Working institution<select value={institutionId} onChange={event => { setInstitutionId(event.target.value); setEditing(null); setValues(Object.fromEntries(resource.fields.map(field => [field.key, field.defaultValue ?? ""]))); setError(""); }}><option value="">Choose an institution</option>{institutions.map(institution => <option key={institution.id} value={institution.id}>{institution.name}</option>)}</select></label><small>Records and related choices are scoped to this institution.</small></div>}
      <div className="resource-layout">
        <div className="resource-form-wrap">
          <h3>{editing ? <Pencil size={15}/> : <Plus size={15}/>} {editing ? `Edit ${displayTitle}` : `Add ${displayTitle}`}</h3>
          <form className="resource-form" onSubmit={submit}>
            {resource.fields.map(field => {
              const dynamicOptions = field.options && !["roomTypes", "durations"].includes(field.options) ? lookupOptions(field.options) : [];
              const needsLookup = Boolean(field.options && !["roomTypes", "durations"].includes(field.options));
              const prerequisite = field.options === "departments" ? "department in Academics" : field.options === "terms" ? "term in Academics" : field.options === "sections" ? "section in Academics" : field.options === "subjects" ? "subject in Academics" : field.options?.startsWith("people/") ? "faculty or staff member in People" : "related campus record";
              const targetWorkspace = field.options?.startsWith("people/") ? "People" : "Academics";
              return <div className="resource-field" key={field.key}>
                <label>{field.label}
                  {field.options === "roomTypes" ? <select required value={values[field.key] ?? "classroom"} onChange={e => setValues(current => ({ ...current, [field.key]: e.target.value }))}><option value="classroom">Classroom</option><option value="lab">Laboratory</option><option value="lecture_hall">Lecture hall</option></select>
                    : field.options === "durations" ? <select required value={values[field.key] ?? "1"} onChange={e => setValues(current => ({ ...current, [field.key]: e.target.value }))}><option value="1">1 period</option><option value="2">2 consecutive periods (lab)</option><option value="3">3 consecutive periods</option></select>
                      : field.options ? <select required disabled={needsLookup && (busy || dynamicOptions.length === 0)} value={values[field.key] ?? ""} onChange={e => setValues(current => ({ ...current, [field.key]: e.target.value }))}><option value="">{needsLookup && busy ? `Loading ${field.label.toLowerCase()}…` : needsLookup && dynamicOptions.length === 0 ? `No ${field.label.toLowerCase()} available yet` : `Choose ${field.label.toLowerCase()}`}</option>{dynamicOptions.map(item => <option key={String(item.id)} value={String(item.id)}>{String(item.full_name ?? item.name ?? `${field.label} ${item.number ?? ""}`)}{item.code ? ` · ${item.code}` : ""}</option>)}</select>
                        : field.type === "checkbox" ? <select value={values[field.key] ?? "false"} onChange={e => setValues(current => ({ ...current, [field.key]: e.target.value }))}><option value="false">No</option><option value="true">Yes</option></select>
                          : <input required type={field.type ?? "text"} min={field.type === "number" ? 1 : undefined} disabled={active === "People" && Boolean(editing) && field.key === "email"} value={values[field.key] ?? ""} onChange={e => setValues(current => ({ ...current, [field.key]: e.target.value }))} placeholder={field.label}/>}
                </label>
                {needsLookup && !busy && !error && dynamicOptions.length === 0 && <small className="lookup-empty">Add a {prerequisite} first.<button type="button" onClick={() => onNavigate(targetWorkspace)}>Open {targetWorkspace}</button></small>}
              </div>;
            })}
            <div className="resource-form-actions"><button className="button button-primary" type="submit" disabled={busy || (userRole === "super_admin" && ["departments", "terms", "rooms"].includes(resource.endpoint) && !institutionId)}>{editing ? <Save size={14}/> : <Plus size={14}/>} {busy ? "Saving…" : editing ? "Save changes" : active === "People" ? "Invite with setup link" : "Add record"}</button>{editing && <button className="button button-quiet" type="button" onClick={() => { setEditing(null); setValues(Object.fromEntries(resource.fields.map(field => [field.key, field.defaultValue ?? ""]))); setError(""); }}>Cancel</button>}</div>
          </form>
          {error && <div className="workspace-error">{error}{error.includes("Sign in") && <a href="/sign-in">Sign in <ArrowRight size={12}/></a>}</div>}
          {success && <div className="workspace-success"><Check size={14}/>{success}</div>}
        </div>
        <div className="records-wrap">
          <div className="records-title"><span><BookOpen size={15}/> {resource.title}</span><div className="records-title-actions"><small>{displayRows.length} records</small>{active !== "People" && csvColumns[resource.endpoint] && <><button className="table-action" onClick={downloadTemplate}><Download size={12}/> Template</button><button className="table-action" onClick={() => importInput.current?.click()} disabled={importBusy || (userRole === "super_admin" && !institutionId)}><FileSpreadsheet size={12}/>{importBusy ? "Importing…" : "Import CSV"}</button><input ref={importInput} type="file" accept=".csv,text/csv" hidden onChange={event => void importCsv(event.target.files?.[0])}/></>}</div></div>
          {busy && displayRows.length === 0 ? <div className="empty-records">Loading campus records…</div> : displayRows.length ? <div className="records-table-wrap"><table className="records-table"><thead><tr>{resource.columns.map(column => <th key={column.key}>{column.label}</th>)}{resource.key === "faculty" && <th>Availability</th>}{active !== "People" && <th>Actions</th>}{active === "People" && <th>Actions & access</th>}</tr></thead><tbody>{displayRows.map(row => <tr key={String(row.id)}>{resource.columns.map(column => <td key={column.key}>{displayValue(row, column.key)}</td>)}{resource.key === "faculty" && <td><button className="table-action" onClick={() => void editAvailability(row)}><Clock3 size={12}/> Set hours</button></td>}{active !== "People" && <td><div className="record-actions"><button className="table-action" onClick={() => beginEdit(row)} aria-label={`Edit ${String(row.name ?? row.code ?? row.id)}`}><Pencil size={12}/> Edit</button><button className="table-action danger-action" onClick={() => void removeRecord(row)} aria-label={`Delete ${String(row.name ?? row.code ?? row.id)}`} disabled={busy}><Trash2 size={12}/> Delete</button></div></td>}{active === "People" && <td><div className="account-actions"><button className="table-action" onClick={() => beginEdit(row)} aria-label={`Edit ${String(row.full_name)}`}><Pencil size={12}/> Edit</button><span className={`account-state ${row.is_active ? "active" : "inactive"}`}>{row.is_active ? "Active" : "Inactive"}</span><button className="table-action" onClick={() => void resendSetup(row)} disabled={busy || !row.is_active}>Resend setup</button><button className={`table-action ${row.is_active ? "danger-action" : ""}`} onClick={() => void changeAccountStatus(row)} disabled={busy}>{row.is_active ? "Deactivate" : "Reactivate"}</button></div></td>}</tr>)}</tbody></table></div> : <div className="empty-records"><span className="empty-icon">{active === "Classrooms" ? <DoorOpen size={20}/> : <Users size={20}/>}</span><b>No records yet</b><small>Add the first {resource.title.toLowerCase()} record to start planning.</small></div>}
          {resource.key === "faculty" && availabilityFaculty && <div className="availability-editor"><div className="availability-heading"><div><b>Unavailable periods</b><small>{String(availabilityFaculty.full_name)} · mark times they cannot teach</small></div><button onClick={() => setAvailabilityFaculty(null)} aria-label="Close availability editor"><X size={15}/></button></div><div className="availability-dimensions"><label>Periods per day<select value={availabilityPeriods} onChange={event => setAvailabilityPeriods(Number(event.target.value))}>{Array.from({ length: availabilityPeriodTimes.length }, (_, index) => index + 1).map(count => <option key={count} value={count}>{count} periods</option>)}</select></label><small>All seven calendar weekdays are shown. Saved blocks outside the visible period range are preserved.</small></div><div className="availability-grid-scroll"><div className="availability-grid" style={{ gridTemplateColumns: `52px repeat(7, minmax(60px, 1fr))`, minWidth: `${52 + 7 * 60}px` }}><div className="availability-cell heading">PERIOD</div>{weekDays.map(day => <div className="availability-cell heading" key={day}>{day.slice(0, 3)}</div>)}{availabilityPeriodTimes.slice(0, availabilityPeriods).map((time, period) => <div className="availability-row" key={time}><div className="availability-cell time">{time}</div>{weekDays.map((day, dayIndex) => { const key = `${dayIndex}:${period}`; const unavailable = blockedSlots.has(key); return <button type="button" key={day} aria-pressed={unavailable} aria-label={`${day} ${time} ${unavailable ? "unavailable" : "available"}`} className={`availability-cell toggle ${unavailable ? "blocked" : "free"}`} onClick={() => setBlockedSlots(current => { const next = new Set(current); if (next.has(key)) next.delete(key); else next.add(key); return next; })}>{unavailable ? "Unavailable" : "Available"}</button>; })}</div>)}</div></div><div className="availability-actions"><span>{blockedSlots.size} blocked periods saved</span><button className="button button-primary" disabled={availabilityBusy} onClick={() => void saveAvailability()}><Save size={13}/>{availabilityBusy ? "Saving…" : "Save availability"}</button></div></div>}
        </div>
      </div>
    </div>
    <div className="workspace-foot"><Sparkles size={13}/>{active === "People" ? "Invitations use a one-time password setup link sent by your configured mail service." : "These records are scoped to your institution and are checked by the API before saving."}</div>
  </section>;
}
