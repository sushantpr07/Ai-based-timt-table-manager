"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, Check, LoaderCircle, Send, Sparkles, WandSparkles } from "lucide-react";
import { apiFetch } from "./api-client";
import "./assistant.css";

type Option = { id: string; name?: string; code?: string; academic_year?: string; is_current?: boolean };
type Proposal = { action: "generate_timetable"; term_id: string; department_id: string; term: string; department: string; name: string };

const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

async function apiRequest(path: string, init?: RequestInit) {
  const response = await apiFetch(`${apiBase}${path}`, init);
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = body?.detail;
    throw new Error(typeof detail === "string" ? detail : detail?.message ?? "The request could not be completed.");
  }
  return body;
}

export default function AssistantWorkspace({ onNavigate }: { onNavigate: (page: string) => void }) {
  const [terms, setTerms] = useState<Option[]>([]);
  const [departments, setDepartments] = useState<Option[]>([]);
  const [termId, setTermId] = useState("");
  const [departmentId, setDepartmentId] = useState("");
  const [message, setMessage] = useState("");
  const [lastPrompt, setLastPrompt] = useState("");
  const [reply, setReply] = useState("");
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [assistantMode, setAssistantMode] = useState<"llm" | "guided" | null>(null);
  const [assistantModeReason, setAssistantModeReason] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([apiRequest("/campus/terms"), apiRequest("/campus/departments")])
      .then(([termRows, departmentRows]) => {
        setTerms(termRows);
        setDepartments(departmentRows);
        setTermId(termRows.find((term: Option) => term.is_current)?.id ?? termRows[0]?.id ?? "");
        setDepartmentId(departmentRows[0]?.id ?? "");
      })
      .catch(e => setError(e instanceof Error ? e.message : "Sign in to connect the planner to your campus."))
      .finally(() => setLoading(false));
  }, []);

  async function ask(event: FormEvent) {
    event.preventDefault();
    if (!message.trim() || busy) return;
    setBusy(true); setError(""); setNotice(""); setProposal(null); setAssistantMode(null); setAssistantModeReason("");
    setLastPrompt(message.trim());
    try {
      const result = await apiRequest("/assistant/chat", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: message.trim(), term_id: termId || null, department_id: departmentId || null }),
      });
      setReply(result.reply);
      setAssistantMode(result.mode === "llm" ? "llm" : "guided");
      setAssistantModeReason(result.reason ?? "");
      setProposal(result.proposal ?? null);
      setMessage("");
    } catch (e) { setError(e instanceof Error ? e.message : "The assistant could not respond."); }
    finally { setBusy(false); }
  }

  async function confirmProposal() {
    if (!proposal || busy) return;
    setBusy(true); setError("");
    try {
      const result = await apiRequest("/assistant/confirm", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: proposal.action, term_id: proposal.term_id, department_id: proposal.department_id, name: proposal.name }),
      });
      setProposal(null);
      setNotice(`Draft created: ${result.name}, version ${result.version}, with ${result.entries.length} scheduled sessions. The optimizer checked the campus constraints.`);
    } catch (e) { setError(e instanceof Error ? e.message : "The draft could not be generated."); }
    finally { setBusy(false); }
  }

  return <div className="assistant-workspace">
    <section className="assistant-hero">
      <span className="assistant-hero-icon"><Sparkles size={18}/></span>
      <div><span className="assistant-kicker">DAYLEAF AI · CONSTRAINT AWARE</span><h2>Plan with Dayleaf Intelligence.</h2><p>Describe your scheduling goal in natural language. Review proposed actions before passing them to the Dayleaf constraint optimizer.</p></div>
    </section>
    <div className="assistant-columns">
      <section className="assistant-conversation panel">
        <div className="assistant-section-head"><div><span className="panel-kicker">PLANNING SESSION</span><h3>What would you like to work on?</h3></div><div className="assistant-head-status"><span className={`assistant-mode-pill ${assistantMode ?? "unknown"}`} role="status" aria-live="polite"><i/>{assistantMode === "llm" ? "Dayleaf AI Online" : assistantMode === "guided" ? "Dayleaf Guided Mode" : "AI status shown after message"}</span><span className="assistant-secure"><i/> Changes need your confirmation</span></div></div>
        {assistantMode === "guided" && <div className="assistant-mode-note" role="note">{assistantModeReason === "insufficient_quota" ? <><b>Dayleaf Guided Assistant Active.</b> External LLM quota is exhausted, but Dayleaf internal scheduling intelligence and constraint optimizer are running at full speed.</> : assistantModeReason === "not_configured" ? <><b>Dayleaf Guided Mode Active.</b> Connect your Google Gemini or OpenAI key in <code>.env</code> to activate live neural chat. The constraint optimizer is fully operational.</> : <><b>Dayleaf Guided Copilot Active.</b> Answering with built-in timetable constraints and scheduling logic. Drafts are validated by the campus constraint optimizer.</>}</div>}
        <div className="assistant-context">
          <label>Academic term<select value={termId} onChange={e => { setTermId(e.target.value); setProposal(null); }} disabled={loading || busy}><option value="">{loading ? "Loading terms…" : terms.length ? "Select term" : "No terms yet"}</option>{terms.map(term => <option key={term.id} value={term.id}>{term.name}{term.academic_year ? ` · ${term.academic_year}` : ""}</option>)}</select></label>
          <label>Department<select value={departmentId} onChange={e => { setDepartmentId(e.target.value); setProposal(null); }} disabled={loading || busy}><option value="">{loading ? "Loading departments…" : departments.length ? "Select department" : "No departments yet"}</option>{departments.map(department => <option key={department.id} value={department.id}>{department.name} {department.code ? `· ${department.code}` : ""}</option>)}</select></label>
        </div>
        {!loading && (!terms.length || !departments.length) && <div className="setup-next-step" role="status"><span><b>Set up your campus first</b><br/>{!departments.length ? "Add a department" : "Add an academic term"} in Academics to use these choices.</span><button type="button" onClick={() => onNavigate("Academics")}>Open Academics</button></div>}
        <div className="assistant-chat" role="log" aria-label="Dayleaf AI conversation" aria-live="polite" aria-relevant="additions" aria-atomic="false">
          <div className="assistant-chat-row"><span className="assistant-chat-avatar"><Sparkles size={14}/></span><div className="assistant-chat-bubble">Hello! I am Dayleaf AI. I can explain scheduling constraints, check room availability, and prepare timetable drafts. Try “Generate a timetable for this term” or ask any question.</div></div>
          {lastPrompt && <div className="assistant-user-row"><div className="assistant-user-bubble">{lastPrompt}</div></div>}
          {reply && <div className="assistant-chat-row"><span className="assistant-chat-avatar"><Sparkles size={14}/></span><div className="assistant-chat-bubble">{reply}</div></div>}
          {notice && <div className="assistant-result" role="status"><Check size={16}/><span>{notice}</span><button onClick={() => onNavigate("Timetable")}>Open timetable <ArrowRight size={13}/></button></div>}
          {proposal && <div className="assistant-proposal"><div className="assistant-proposal-title"><span><WandSparkles size={15}/></span><div><b>Draft generation proposal</b><small>Nothing has been scheduled yet.</small></div></div><dl><div><dt>Department</dt><dd>{proposal.department}</dd></div><div><dt>Term</dt><dd>{proposal.term}</dd></div><div><dt>Action</dt><dd>Run the Dayleaf constraint optimizer and save a new draft</dd></div></dl><button className="button button-primary" onClick={() => void confirmProposal()} disabled={busy}><Check size={15}/>{busy ? "Generating draft…" : "Confirm and generate draft"}</button></div>}
          {error && <div className="assistant-error" role="alert">{error}{error.toLowerCase().includes("sign in") && <> <Link href="/sign-in">Sign in</Link></>}</div>}
        </div>
        <form className="assistant-prompt" onSubmit={ask}><textarea value={message} onChange={e => setMessage(e.target.value)} placeholder="Ask Dayleaf AI or request a timetable draft…" aria-label="Message Dayleaf AI" rows={2} disabled={busy}/><button aria-label="Send request" type="submit" disabled={busy || !message.trim()}>{busy ? <LoaderCircle size={16} className="assistant-spin"/> : <Send size={16}/>}</button></form>
        <p className="assistant-footnote">Dayleaf AI suggestions are advisory. Saved drafts are generated and validated by the campus constraint optimizer.</p>
      </section>
      <aside className="assistant-guidance panel"><span className="panel-kicker">HOW IT WORKS</span><h3>Your schedule stays in control.</h3><div className="assistant-step"><b>01</b><span><strong>Choose context</strong><small>Select the term and department for your request.</small></span></div><div className="assistant-step"><b>02</b><span><strong>Describe the goal</strong><small>Ask naturally. The assistant can propose a new draft or explain scheduling concepts.</small></span></div><div className="assistant-step"><b>03</b><span><strong>Review and confirm</strong><small>Generation uses the same hard constraints, permissions, audit trail, and draft workflow as the timetable planner.</small></span></div><button className="assistant-open-planner" onClick={() => onNavigate("Timetable")}>Open timetable planner <ArrowRight size={14}/></button></aside>
    </div>
  </div>;
}
