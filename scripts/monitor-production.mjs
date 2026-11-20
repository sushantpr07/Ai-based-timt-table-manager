import { mkdir, readFile, rename, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

async function readState(stateFile) {
  try {
    const value = JSON.parse(await readFile(stateFile, "utf8"));
    return typeof value.healthy === "boolean" ? value : null;
  } catch (error) {
    if (error.code === "ENOENT" || error instanceof SyntaxError) return null;
    throw error;
  }
}

async function writeState(stateFile, state) {
  await mkdir(path.dirname(stateFile), { recursive: true });
  const temporary = `${stateFile}.${process.pid}.partial`;
  await writeFile(temporary, `${JSON.stringify(state, null, 2)}\n`, { mode: 0o600 });
  try {
    await rename(temporary, stateFile);
  } catch (error) {
    await rm(temporary, { force: true }).catch(() => undefined);
    throw error;
  }
}

async function checkEndpoint(name, url, fetchImpl, timeoutMs) {
  try {
    const response = await fetchImpl(url, { method: "GET", redirect: "manual", signal: AbortSignal.timeout(timeoutMs) });
    return response.ok ? null : `${name} returned HTTP ${response.status}`;
  } catch (error) {
    return `${name} is unreachable (${error.name === "TimeoutError" ? "timeout" : "connection error"})`;
  }
}

export async function monitorProduction({ webUrl, apiHealthUrl, stateFile, webhookUrl, fetchImpl = fetch,
  timeoutMs = 8000, now = new Date() }) {
  if (!webUrl || !apiHealthUrl || !stateFile) throw new Error("Web URL, API health URL, and state file are required.");
  const failures = (await Promise.all([
    checkEndpoint("Web", webUrl, fetchImpl, timeoutMs),
    checkEndpoint("API readiness", apiHealthUrl, fetchImpl, timeoutMs),
  ])).filter(Boolean);
  const healthy = failures.length === 0;
  const previous = await readState(stateFile);
  const changed = previous ? previous.healthy !== healthy || JSON.stringify(previous.failures) !== JSON.stringify(failures) : !healthy;

  if (changed && webhookUrl) {
    const message = healthy ? "CampusFlow recovered: web and API readiness checks are passing." :
      `CampusFlow health alert: ${failures.join("; ")}.`;
    const response = await fetchImpl(webhookUrl, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ text: message }),
      signal: AbortSignal.timeout(timeoutMs),
    });
    if (!response.ok) throw new Error(`Alert webhook returned HTTP ${response.status}.`);
  } else if (changed && !healthy) {
    console.error("ALERT_WEBHOOK_URL is not configured; the health check failed and no alert was delivered.");
  }

  if (!(changed && !healthy && !webhookUrl)) {
    await writeState(stateFile, { healthy, failures, checked_at: now.toISOString() });
  }
  if (!healthy) throw new Error(failures.join("; "));
  return { healthy, changed, failures };
}

async function main() {
  const webUrl = process.env.CAMPUSFLOW_WEB_HEALTH_URL;
  const apiHealthUrl = process.env.CAMPUSFLOW_API_HEALTH_URL;
  const stateFile = path.resolve(process.env.CAMPUSFLOW_MONITOR_STATE ?? path.join(projectRoot, ".monitor-state.json"));
  const webhookUrl = process.env.ALERT_WEBHOOK_URL;
  const result = await monitorProduction({ webUrl, apiHealthUrl, stateFile, webhookUrl });
  console.log(result.changed ? "CampusFlow health state changed; notification sent if configured." : "CampusFlow is healthy; no state change.");
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  main().catch(error => {
    console.error(error.message);
    process.exitCode = 1;
  });
}
