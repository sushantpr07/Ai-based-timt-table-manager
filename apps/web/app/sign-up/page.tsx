"use client";
import Link from "next/link";
import { useState } from "react";
import { ArrowRight } from "lucide-react";
import { AuthLayout } from "../AuthLayout";
import { apiFetch } from "../api-client";

export default function SignUp() {
  const [error, setError] = useState(""); const [busy, setBusy] = useState(false); const [pending, setPending] = useState(false);
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError(""); const form = new FormData(event.currentTarget);
    try { const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
      const res = await apiFetch(`${base}/auth/sign-up`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ institution_name: form.get("institution"), full_name: form.get("name"), email: form.get("email"), password: form.get("password") }) });
      if (!res.ok) throw new Error((await res.json()).detail ?? "Could not create account.");
      const data = await res.json();
      if (data.email_verification_required) setPending(true); else window.location.href = "/";
    } catch (e) { setError((e as Error).message.includes("fetch") ? "Dayleaf API is offline. Start the API and try again." : (e as Error).message); } finally { setBusy(false); }
  }
  return <AuthLayout><div className="auth-heading"><span className="auth-eyebrow">YOUR CAMPUS STARTS HERE</span><h1>{pending ? <>Check your<br/><em>inbox.</em></> : <>Make space for<br/><em>better plans.</em></>}</h1><p>{pending ? "Your workspace is ready. Verify your work email to activate sign-in." : "Set up your university workspace in a few steps."}</p></div>{pending ? <div className="auth-success" role="status" aria-live="polite">We sent a one-time verification link to your email. Open it within 60 minutes, then sign in to continue.</div> : <>{error && <div className="auth-error" role="alert">{error}</div>}<form className="auth-form" onSubmit={submit}><label>University or college<input name="institution" placeholder="Northbridge University" required minLength={2}/></label><label>Your name<input name="name" autoComplete="name" placeholder="Arjun Mehra" required minLength={2}/></label><label>Work email<input name="email" type="email" autoComplete="email" placeholder="you@university.edu" required/></label><label>Create password<input name="password" type="password" autoComplete="new-password" placeholder="At least 12 characters" required minLength={12}/></label><button className="auth-submit" disabled={busy}>{busy ? "Creating workspace…" : "Create campus workspace"}<ArrowRight size={16}/></button></form></>}<div className="auth-switch">Already have an account? <Link href="/sign-in">Sign in</Link></div></AuthLayout>;
}
