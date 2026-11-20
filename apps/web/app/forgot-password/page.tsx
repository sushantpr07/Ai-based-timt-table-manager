"use client";
import Link from "next/link";
import { useState } from "react";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { AuthLayout } from "../AuthLayout";
import { apiFetch } from "../api-client";

export default function ForgotPassword() {
  const [sent, setSent] = useState(false); const [error, setError] = useState("");
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); const email = new FormData(event.currentTarget).get("email");
    try { const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1"; const res = await apiFetch(`${base}/auth/forgot-password`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email }) }); if (!res.ok) throw new Error("We couldn't submit that request. Please try again."); setSent(true); }
    catch (e) { setError((e as Error).message.includes("fetch") ? "CampusFlow API is offline. Start the API and try again." : (e as Error).message); }
  }
  return <AuthLayout><Link className="back-link" href="/sign-in"><ArrowLeft size={14}/> Back to sign in</Link><div className="auth-heading"><span className="auth-eyebrow">ACCOUNT RECOVERY</span><h1>Forgot your<br/><em>password?</em></h1><p>Enter your work email and we’ll send a secure reset link.</p></div>{sent ? <div className="auth-success" role="status" aria-live="polite">If an account matches that address, a password reset link will be sent. Check your inbox.</div> : <><div className="auth-error" role="alert" style={{display:error?"block":"none"}}>{error}</div><form className="auth-form" onSubmit={submit}><label>Email address<input name="email" type="email" autoComplete="email" placeholder="you@university.edu" required/></label><button className="auth-submit">Send reset link<ArrowRight size={16}/></button></form></>}</AuthLayout>;
}
