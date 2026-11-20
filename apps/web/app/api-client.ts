export function getApiBase(): string {
  if (typeof window !== "undefined") {
    const host = window.location.hostname || "127.0.0.1";
    if (host.endsWith(".trycloudflare.com") || window.location.protocol === "https:") {
      return `${window.location.origin}/api/v1`;
    }
    return `http://${host}:8000/api/v1`;
  }
  return process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api/v1";
}

export function resolveApiUrl(raw: RequestInfo | URL): string {
  const urlStr = raw instanceof Request ? raw.url : String(raw);
  if (typeof window !== "undefined") {
    const host = window.location.hostname || "127.0.0.1";
    if (host.endsWith(".trycloudflare.com") || window.location.protocol === "https:") {
      return urlStr
        .replace(/^https?:\/\/localhost:8000\/api\/v1/, `${window.location.origin}/api/v1`)
        .replace(/^https?:\/\/127\.0\.0\.1:8000\/api\/v1/, `${window.location.origin}/api/v1`)
        .replace(/^https?:\/\/dayleaf-api\.onrender\.com\/api\/v1/, `${window.location.origin}/api/v1`);
    }
    return urlStr
      .replace(/^http:\/\/localhost:8000/, `http://${host}:8000`)
      .replace(/^http:\/\/127\.0\.0\.1:8000/, `http://${host}:8000`);
  }
  return urlStr;
}

let refreshInFlight: Promise<boolean> | null = null;

function skipsRefresh(input: RequestInfo | URL): boolean {
  const raw = input instanceof Request ? input.url : String(input);
  try {
    const path = new URL(raw, "http://localhost").pathname;
    return /\/auth\/(sign-in|sign-up|sign-out|forgot-password|reset-password|refresh)$/.test(path);
  } catch {
    return false;
  }
}

async function readCsrfToken(): Promise<string | null> {
  try {
    const base = getApiBase();
    const response = await fetch(`${base}/auth/csrf`, { method: "GET", credentials: "include", cache: "no-store" });
    if (!response.ok) return null;
    const result = await response.json();
    return typeof result.csrf_token === "string" ? result.csrf_token : null;
  } catch { return null; }
}

async function rotateRefreshCookie(): Promise<boolean> {
  if (!refreshInFlight) {
    const base = getApiBase();
    refreshInFlight = readCsrfToken().then(token => token ? fetch(`${base}/auth/refresh`, {
      method: "POST", credentials: "include", headers: { "X-CSRF-Token": token },
    }) : null)
      .then(response => Boolean(response?.ok))
      .catch(() => false)
      .finally(() => { refreshInFlight = null; });
  }
  return refreshInFlight;
}

export async function apiFetch(input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> {
  const targetUrl = resolveApiUrl(input);
  const method = (init.method ?? (input instanceof Request ? input.method : "GET")).toUpperCase();
  const headers = new Headers(init.headers ?? (input instanceof Request ? input.headers : undefined));
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    const csrfToken = await readCsrfToken();
    if (csrfToken) headers.set("X-CSRF-Token", csrfToken);
  }
  const options: RequestInit = { ...init, headers, credentials: "include" };
  const response = await fetch(targetUrl, options);
  if (response.status !== 401 || skipsRefresh(input)) return response;
  if (!await rotateRefreshCookie()) return response;
  const retryHeaders = new Headers(options.headers);
  const csrfToken = await readCsrfToken();
  if (csrfToken) retryHeaders.set("X-CSRF-Token", csrfToken);
  return fetch(targetUrl, { ...options, headers: retryHeaders });
}
