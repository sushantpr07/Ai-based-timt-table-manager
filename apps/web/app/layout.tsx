import type { Metadata } from "next";
import "./styles.css";
import "./auth.css";
import "./polish.css";
import "./timetable.css";
import "./personal.css";
import "./search.css";
import "./ux-refresh.css";
import "./dayleaf-theme.css";

export const metadata: Metadata = {
  title: "Dayleaf — Next-Gen Campus & Timetable Intelligence",
  description: "High-performance academic scheduling, constraint optimization, and intelligent campus flow.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
