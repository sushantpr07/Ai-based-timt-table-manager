import Link from "next/link";
import { Sparkles } from "lucide-react";

export function AuthLayout({ children }: { children: React.ReactNode }) {
  return <main className="auth-layout"><section className="auth-left"><Link className="auth-brand" href="/"><span className="dayleaf-brand-icon"><Sparkles size={18} strokeWidth={2.4}/></span><span className="dayleaf-brand-title">Day<span className="dayleaf-brand-leaf">leaf</span></span></Link><div className="auth-promo"><div className="promo-stars">✦ <span>✨</span></div><span className="auth-eyebrow">NEXT-GEN CAMPUS INTELLIGENCE</span><h2>Smarter schedules.<br/>Zero clashes.<br/><em>Pure flow.</em></h2><p>Harmonize faculty, spaces, and academic curriculum in one unified workspace.</p><div className="promo-bottom"><span><i/> Dayleaf Constraint Studio</span><span>2026 Edition</span></div></div><div className="auth-left-footer">© 2026 Dayleaf Technologies <span>Intelligent Campus Systems</span></div></section><section className="auth-right"><div className="auth-card">{children}</div></section></main>;
}
