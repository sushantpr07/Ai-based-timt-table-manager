"use client";

import { useEffect, useState } from "react";
import { BellRing, Check } from "lucide-react";
import { apiFetch } from "./api-client";
import "./notification-preferences.css";

type Preferences = { schedule_updates: boolean; approval_updates: boolean };
type PreferenceKey = keyof Preferences;
const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export default function NotificationPreferences() {
  const [preferences, setPreferences] = useState<Preferences | null>(null);
  const [role, setRole] = useState("");
  const [busy, setBusy] = useState<PreferenceKey | "load" | null>("load");
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    apiFetch(`${base}/settings`).then(async response => {
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Could not load notification preferences.");
      setPreferences(data.notification_preferences ?? { schedule_updates: true, approval_updates: true });
      setRole(data.profile?.role ?? "");
    }).catch(e => setError(e instanceof Error ? e.message : "Could not load notification preferences."))
      .finally(() => setBusy(null));
  }, []);

  async function update(key: PreferenceKey, enabled: boolean) {
    if (!preferences || busy) return;
    const next = { ...preferences, [key]: enabled };
    setBusy(key); setError(""); setSaved(false);
    try {
      const response = await apiFetch(`${base}/settings/notifications`, {
        method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(next),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Could not save notification preferences.");
      setPreferences(data.notification_preferences); setSaved(true);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not save notification preferences."); }
    finally { setBusy(null); }
  }

  const visiblePreferences: PreferenceKey[] = role === "student" || role === "faculty"
    ? ["schedule_updates"] : ["approval_updates"];

  return <section className="notification-preferences panel" aria-labelledby="notification-preferences-title">
    <div className="settings-form-heading"><span><BellRing size={17}/></span><div><b id="notification-preferences-title">In-app notifications</b><small>Choose which timetable updates appear in your Dayleaf inbox.</small></div></div>
    {error && <div className="notification-pref-error">{error}</div>}
    {visiblePreferences.map(key => {
      const schedule = key === "schedule_updates";
      const label = schedule ? "Published schedule updates" : "Approval requests and decisions";
      const detail = schedule ? "When a timetable that affects your classes or teaching is published." : "When a timetable is submitted for review, returned, or approved.";
      return <label className="notification-pref-row" key={key}><span><b>{label}</b><small>{detail}</small></span><input type="checkbox" checked={preferences?.[key] ?? true} disabled={!preferences || busy !== null} onChange={event => void update(key, event.target.checked)} aria-label={label}/></label>;
    })}
    <div className="notification-pref-foot">{saved && <span><Check size={13}/> Saved</span>}<small>Applies to new in-app notifications. Existing updates remain in your inbox.</small></div>
  </section>;
}
