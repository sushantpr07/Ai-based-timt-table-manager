"use client";

import Link from "next/link";
import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { ArrowRight, CheckCircle2 } from "lucide-react";
import { AuthLayout } from "../AuthLayout";
import { apiFetch } from "../api-client";

export default function VerifyEmail() {
  return <Suspense fallback={<div className="auth-layout"><div className="auth-right">Loading verification…</div></div>}><VerifyEmailForm /></Suspense>;
}

function VerifyEmailForm() {
  const params = useSearchParams();
  const token = params.get("token") ?? "";
  const [message, setMessage] = useState("");
  const [verified, setVerified] = useState(false);
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setMessage("");
    try {
      const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
      const response = await apiFetch(`${base}/auth/verify-email`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ token }) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "This verification link is invalid or expired.");
      setVerified(true);
    } catch (error) {
      setMessage((error as Error).message.includes("fetch") ? "CampusFlow API is offline. Start the API and try again." : (error as Error).message);
    } finally { setBusy(false); }
  }

  return <AuthLayout><div className="auth-heading"><span className="auth-eyebrow">EMAIL VERIFICATION</span><h1>{verified ? <>You’re all<br/><em>set.</em></> : <>Verify your<br/><em>email.</em></>}</h1><p>{verified ? "Your email address is confirmed. Sign in to open your campus workspace." : "Confirm your work email to activate your CampusFlow account."}</p></div>{verified ? <div className="auth-success"><CheckCircle2 size={17}/> Email verified successfully. <Link href="/sign-in">Sign in to CampusFlow</Link></div> : <><div className="auth-error" style={{ display: message ? "block" : "none" }}>{message}</div><form className="auth-form" onSubmit={submit}><button className="auth-submit" disabled={busy || !token}>{busy ? "Verifying…" : "Verify email address"}<ArrowRight size={16}/></button></form></>}<div className="auth-switch">Need a new link? <Link href="/sign-in">Return to sign in</Link></div></AuthLayout>;
}
