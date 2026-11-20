"use client";
import Link from "next/link";
import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { ArrowRight } from "lucide-react";
import { AuthLayout } from "../AuthLayout";
import { apiFetch } from "../api-client";

export default function ResetPassword() { return <Suspense fallback={<div className="auth-layout"><div className="auth-right">Loading reset form…</div></div>}><ResetPasswordForm /></Suspense>; }

function ResetPasswordForm() {
  const params = useSearchParams(); const token = params.get("token") ?? ""; const [message, setMessage] = useState(""); const [done, setDone] = useState(false);
  async function submit(event: React.FormEvent<HTMLFormElement>) { event.preventDefault(); setMessage(""); const password = new FormData(event.currentTarget).get("password");
    try { const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1"; const res = await apiFetch(`${base}/auth/reset-password`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ token, new_password: password }) }); if (!res.ok) throw new Error((await res.json()).detail ?? "This reset link is invalid or expired."); setDone(true); }
    catch (e) { setMessage((e as Error).message.includes("fetch") ? "CampusFlow API is offline. Start the API and try again." : (e as Error).message); }
  }
  return <AuthLayout><div className="auth-heading"><span className="auth-eyebrow">ACCOUNT RECOVERY</span><h1>Choose a new<br/><em>password.</em></h1><p>Use at least 12 characters for your new password.</p></div>{done ? <div className="auth-success" role="status" aria-live="polite">Password updated. <Link href="/sign-in">Sign in to CampusFlow</Link></div> : <><div className="auth-error" role="alert" style={{display:message?"block":"none"}}>{message}</div><form className="auth-form" onSubmit={submit}><label>New password<input name="password" type="password" autoComplete="new-password" minLength={12} required placeholder="At least 12 characters"/></label><button className="auth-submit">Update password<ArrowRight size={16}/></button></form></>}</AuthLayout>;
}
