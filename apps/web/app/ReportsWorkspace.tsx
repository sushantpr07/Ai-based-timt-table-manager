"use client";

import { useCallback, useEffect, useState } from "react";
import { Download, FileBarChart2, LoaderCircle } from "lucide-react";
import { apiFetch } from "./api-client";
import "./reports.css";

type ReportType = "schedule" | "faculty-load" | "room-utilization" | "conflicts";
type Column = { key: string; label: string };
type ReportData = { title: string; description: string; scope: string; columns: Column[]; rows: Record<string, string | number | null>[] };
type Term = { id: string; name: string; academic_year: string; is_current?: boolean };
const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
const reportOptions: { id: ReportType; label: string }[] = [
  { id: "schedule", label: "Published schedule detail" },
  { id: "faculty-load", label: "Faculty teaching load" },
  { id: "room-utilization", label: "Room utilization" },
  { id: "conflicts", label: "Published schedule conflicts" },
];

export default function ReportsWorkspace() {
  const [terms, setTerms] = useState<Term[]>([]);
  const [termId, setTermId] = useState("");
  const [reportType, setReportType] = useState<ReportType>("schedule");
  const [report, setReport] = useState<ReportData | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const query = termId ? `?term_id=${encodeURIComponent(termId)}` : "";
      const response = await apiFetch(`${base}/analytics/reports/${reportType}${query}`);
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail ?? "Could not load this report.");
      setReport(result);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not load this report."); setReport(null); }
    finally { setLoading(false); }
  }, [reportType, termId]);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    apiFetch(`${base}/campus/terms`).then(async response => {
      const result = await response.json();
      if (response.ok) setTerms(result);
    }).catch(() => undefined);
  }, []);

  async function download() {
    if (!report || exporting) return;
    setExporting(true); setError("");
    try {
      const query = termId ? `?term_id=${encodeURIComponent(termId)}` : "";
      const response = await apiFetch(`${base}/analytics/reports/${reportType}/export.csv${query}`);
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail ?? "Could not export this report.");
      }
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement("a");
      link.href = url; link.download = `dayleaf_${reportType.replaceAll("-", "_")}.csv`;
      link.click(); window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not export this report."); }
    finally { setExporting(false); }
  }

  return <section className="reports-center panel">
    <div className="reports-head"><div><span className="panel-kicker">REPORT LIBRARY</span><h3><FileBarChart2 size={17}/> Operational reports</h3><p>Download detailed published schedule, workload, room, and conflict data.</p></div><button className="button button-primary" onClick={() => void download()} disabled={!report || loading || exporting}><Download size={14}/>{exporting ? "Preparing…" : "Download CSV"}</button></div>
    <div className="reports-controls"><label>Report<select value={reportType} onChange={event => setReportType(event.target.value as ReportType)}>{reportOptions.map(option => <option value={option.id} key={option.id}>{option.label}</option>)}</select></label><label>Academic term<select value={termId} onChange={event => setTermId(event.target.value)}><option value="">All published terms</option>{terms.map(term => <option key={term.id} value={term.id}>{term.name} · {term.academic_year}{term.is_current ? " · Current" : ""}</option>)}</select></label><span className="reports-scope">Scope: {report?.scope ?? "your access"}</span></div>
    {error && <div className="notice error-notice">{error}</div>}
    {loading ? <div className="reports-empty"><LoaderCircle size={16} className="reports-spin"/> Loading report…</div> : report && <>
      <div className="reports-description"><b>{report.title}</b><span>{report.description} {report.rows.length} row{report.rows.length === 1 ? "" : "s"}.</span></div>
      {report.rows.length ? <div className="reports-table-wrap"><table className="reports-table"><thead><tr>{report.columns.map(column => <th key={column.key}>{column.label}</th>)}</tr></thead><tbody>{report.rows.slice(0, 10).map((row, index) => <tr key={`${index}-${String(row[report.columns[0]?.key] ?? "")}`}>{report.columns.map(column => <td key={column.key}>{row[column.key] === null || row[column.key] === undefined || row[column.key] === "" ? "—" : String(row[column.key])}</td>)}</tr>)}</tbody></table></div> : <div className="reports-empty">No matching published data in this scope.</div>}
      {report.rows.length > 10 && <small className="reports-preview-note">Showing 10 of {report.rows.length} rows. Download the CSV for the complete report.</small>}
    </>}
  </section>;
}
