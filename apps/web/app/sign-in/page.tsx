"use client";
import Link from "next/link";
import { useState } from "react";
import { ArrowLeft, ArrowRight, Sparkles } from "lucide-react";
import { AuthLayout } from "../AuthLayout";
import { apiFetch } from "../api-client";

export default function SignIn() {
  const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  const [verificationNeeded, setVerificationNeeded] = useState(false); const [email, setEmail] = useState(""); const [resent, setResent] = useState(false);
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("");
    const form = new FormData(event.currentTarget);
    try { const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
      const res = await apiFetch(`${base}/auth/sign-in`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email: form.get("email"), password: form.get("password") }) });
      if (!res.ok) throw new Error((await res.json()).detail ?? "Could not sign in."); window.location.href = "/";
    } catch (e) { const message = (e as Error).message.includes("fetch") ? "Dayleaf API is offline. Start the API and try again." : (e as Error).message; setError(message); setVerificationNeeded(message.startsWith("Verify your email")); } finally { setBusy(false); }
  }
  async function resendVerification() { setResent(false); try { const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1"; const response = await apiFetch(`${base}/auth/resend-verification`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email }) }); if (!response.ok) throw new Error("Could not request a verification link."); setResent(true); } catch { setError("Could not request a verification link. Please try again."); } }
  return <AuthLayout><Link className="back-link" href="/"><ArrowLeft size={14}/> Back to overview</Link><div className="auth-heading"><span className="auth-eyebrow"><Sparkles size={13}/> WELCOME BACK</span><h1>Good to see you<br/><em>again.</em></h1><p>Sign in to your Dayleaf workspace.</p></div>{error && <div className="auth-error" role="alert">{error}</div>}{resent && <div className="auth-success" role="status" aria-live="polite">If an unverified account matches that address, a verification link will be sent.</div>}<form className="auth-form" onSubmit={submit}><label>Email address<input name="email" type="email" autoComplete="email" placeholder="you@university.edu" value={email} onChange={event => setEmail(event.target.value)} required/></label><label>Password<div className="password-wrap"><input name="password" type="password" autoComplete="current-password" placeholder="Your password" required/><Link href="/forgot-password">Forgot?</Link></div></label><button className="auth-submit" disabled={busy}>{busy ? "Signing in…" : "Sign in to Dayleaf"}<ArrowRight size={16}/></button></form>{verificationNeeded && <button type="button" className="table-action" onClick={() => void resendVerification()}>Resend verification email</button>}<div className="auth-switch">New to Dayleaf? <Link href="/sign-up">Create an account</Link></div><div className="auth-terms">By continuing, you agree to Dayleaf&apos;s <a href="#terms">Terms</a> and <a href="#privacy">Privacy Policy</a>.</div></AuthLayout>;
}

