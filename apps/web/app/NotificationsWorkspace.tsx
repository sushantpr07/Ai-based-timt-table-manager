"use client";

import { useCallback, useEffect, useState } from "react";
import { Bell, Check, RefreshCw } from "lucide-react";
import { apiFetch } from "./api-client";
import { useCampusEvents } from "./useCampusEvents";

type Notice = { id: string; title: string; body: string; read: boolean; created_at: string };

export default function NotificationsWorkspace() {
  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
  const [items, setItems] = useState<Notice[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const unread = items.filter(item => !item.read).length;

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await apiFetch(`${base}/me/notifications`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Could not load notifications.");
      setItems(data);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load notifications.");
    } finally {
      setLoading(false);
    }
  }, [base]);

  useEffect(() => { void load(); }, [load]);
  useCampusEvents(() => { void load(); }, true);

  async function markRead(item: Notice) {
    if (item.read || busy) return;
    setBusy(true);
    setError("");
    try {
      const response = await apiFetch(`${base}/me/notifications/${item.id}/read`, { method: "PATCH" });
      if (!response.ok) throw new Error("Could not update this notification.");
      setItems(current => current.map(row => row.id === item.id ? { ...row, read: true } : row));
      setNotice("Notification marked as read.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not update this notification.");
    } finally {
      setBusy(false);
    }
  }

  async function markAllRead() {
    if (!unread || busy) return;
    setBusy(true);
    setError("");
    try {
      const response = await apiFetch(`${base}/me/notifications/read-all`, { method: "POST" });
      if (!response.ok) throw new Error("Could not mark notifications as read.");
      setItems(current => current.map(item => ({ ...item, read: true })));
      setNotice("All notifications marked as read.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not mark notifications as read.");
    } finally {
      setBusy(false);
    }
  }

  return <section className="personal-panel panel" aria-labelledby="admin-notifications-title">
    <div className="personal-heading">
      <div><span className="panel-kicker">YOUR CAMPUS UPDATES</span><h2 id="admin-notifications-title"><Bell size={20}/> Notifications {unread > 0 && <span className="unread-count">{unread}</span>}</h2><p>Timetable approvals and campus updates sent to your account.</p></div>
      <div className="personal-actions">
        <button className="button button-quiet" onClick={() => void load()} disabled={loading}><RefreshCw size={14}/> Refresh</button>
        {unread > 0 && <button className="button button-quiet" onClick={() => void markAllRead()} disabled={busy}><Check size={14}/> Mark all read</button>}
      </div>
    </div>
    {error && <div className="notice error-notice" role="alert">{error}</div>}
    {notice && <div className="notice" role="status" aria-live="polite">{notice}</div>}
    {loading ? <div className="personal-empty" role="status">Loading notifications…</div> : items.length ? <div className="notification-list">
      {items.map(item => <article key={item.id} className={`notification-item ${item.read ? "read" : "unread"}`}>
        <span className="notification-icon"><Bell size={16}/></span>
        <div><b>{item.title}</b><p>{item.body}</p><small>{new Date(item.created_at).toLocaleString()}</small></div>
        <button aria-label={item.read ? `${item.title}, read` : `Mark ${item.title} as read`} onClick={() => void markRead(item)} disabled={busy || item.read}>{item.read ? <Check size={15}/> : <span className="unread-dot"/>}</button>
      </article>)}
    </div> : <div className="personal-empty"><Bell size={22}/><b>You’re all caught up</b><small>Timetable approvals and campus updates will appear here.</small></div>}
  </section>;
}
