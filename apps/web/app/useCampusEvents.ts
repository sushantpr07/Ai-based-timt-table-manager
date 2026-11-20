"use client";

import { useEffect, useRef } from "react";

const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export function useCampusEvents(onUpdate: () => void, enabled = true) {
  const update = useRef(onUpdate);
  useEffect(() => { update.current = onUpdate; }, [onUpdate]);

  useEffect(() => {
    if (!enabled) return;
    let connected = false;
    const refresh = () => {
      if (document.visibilityState === "visible") update.current();
    };
    const source = typeof EventSource === "undefined" ? null : new EventSource(`${apiBase}/events`, { withCredentials: true });
    if (source) {
      source.onopen = () => { connected = true; };
      source.onerror = () => { connected = false; };
      source.addEventListener("campus.refresh", refresh);
    }
    const fallback = window.setInterval(() => { if (!connected) refresh(); }, 8000);
    const onVisibilityChange = () => { if (!connected && document.visibilityState === "visible") refresh(); };
    document.addEventListener("visibilitychange", onVisibilityChange);
    return () => {
      source?.close();
      window.clearInterval(fallback);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [enabled]);
}
