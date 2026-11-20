"use client";

import { useCallback, useEffect, useState } from "react";
import { RefreshCw, ScrollText, UserRound } from "lucide-react";
import { apiFetch } from "./api-client";

type AuditRow = { id: string; action: string; resource_type: string; resource_id: string | null; actor: string; actor_email: string | null; created_at: string };

export default function AuditWorkspace() {
  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
  const [rows, setRows] = useState<AuditRow[]>([]);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    setBusy(true); setError("");
    try {
      const response = await apiFetch(`${base}/audit`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Could not load audit history.");
      setRows(data);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not load audit history."); }
    finally { setBusy(false); }
  }, [base]);
  useEffect(() => { void load(); }, [load]);
  return <section className="audit-workspace panel"><div className="audit-heading"><div><span className="panel-kicker">CAMPUS ACTIVITY</span><h2><ScrollText size={20}/> Audit history</h2><p>Recent administrative changes recorded for your access scope.</p></div><button className="button button-quiet" onClick={() => void load()} disabled={busy}><RefreshCw size={14}/> Refresh</button></div>
    {error && <div className="notice error-notice">{error}</div>}
    {busy && !rows.length ? <div className="personal-empty">Loading audit history…</div> : rows.length ? <div className="audit-table-wrap"><table className="audit-table"><thead><tr><th>Action</th><th>Record</th><th>Changed by</th><th>When</th></tr></thead><tbody>{rows.map(row => <tr key={row.id}><td><span className="audit-action">{row.action}</span></td><td><b>{row.resource_type.replaceAll("_", " ")}</b><small>{row.resource_id?.slice(0, 8) ?? "—"}</small></td><td><span className="audit-actor"><UserRound size={13}/>{row.actor}</span><small>{row.actor_email ?? "Account removed"}</small></td><td>{new Date(row.created_at).toLocaleString()}</td></tr>)}</tbody></table></div> : <div className="personal-empty"><ScrollText size={22}/><b>No audit activity yet</b><small>Administrative changes will appear here as your campus is configured.</small></div>}
    <div className="audit-foot">Showing up to 200 most recent events.</div>
  </section>;
}
