import assert from "node:assert/strict";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { monitorProduction } from "./monitor-production.mjs";

function fakeFetch(statuses, messages) {
  let index = 0;
  return async (url, options) => {
    if (options.method === "POST") {
      messages.push(JSON.parse(options.body).text);
      return { ok: true, status: 200 };
    }
    return { ok: statuses[index++], status: statuses[index - 1] ? 200 : 503 };
  };
}

test("sends transition alerts once and reports recovery", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "campusflow-monitor-"));
  try {
    const stateFile = path.join(root, "state", "monitor.json");
    const messages = [];
    const options = { webUrl: "https://campus.example.edu", apiHealthUrl: "https://api.campus.example.edu/api/v1/health", stateFile,
      webhookUrl: "https://hooks.example.edu/alert", fetchImpl: fakeFetch([false, true], messages), now: new Date("2026-11-18T12:00:00Z") };
    await assert.rejects(monitorProduction(options), /Web returned HTTP 503/);
    assert.deepEqual(messages, ["CampusFlow health alert: Web returned HTTP 503."]);
    await assert.rejects(monitorProduction({ ...options, fetchImpl: fakeFetch([false, true], messages) }), /Web returned HTTP 503/);
    assert.equal(messages.length, 1);
    const recovered = await monitorProduction({ ...options, fetchImpl: fakeFetch([true, true], messages) });
    assert.equal(recovered.healthy, true);
    assert.equal(messages.length, 2);
    assert.match(messages[1], /recovered/);
    assert.equal(JSON.parse(await readFile(stateFile, "utf8")).healthy, true);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test("does not record a failed state transition if webhook delivery fails", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "campusflow-monitor-webhook-"));
  try {
    const stateFile = path.join(root, "state.json");
    const fetchImpl = async (_url, options) => options.method === "POST" ? { ok: false, status: 502 } : { ok: false, status: 503 };
    await assert.rejects(monitorProduction({ webUrl: "https://campus.example.edu", apiHealthUrl: "https://api.campus.example.edu/health",
      stateFile, webhookUrl: "https://hooks.example.edu/alert", fetchImpl }), /Alert webhook returned HTTP 502/);
    await assert.rejects(readFile(stateFile));
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test("leaves an outage unacknowledged until a webhook is configured", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "campusflow-monitor-no-webhook-"));
  try {
    const stateFile = path.join(root, "state.json");
    const fetchImpl = async () => ({ ok: false, status: 503 });
    const base = { webUrl: "https://campus.example.edu", apiHealthUrl: "https://api.campus.example.edu/health", stateFile, fetchImpl };
    await assert.rejects(monitorProduction(base), /returned HTTP 503/);
    await assert.rejects(readFile(stateFile));
    const messages = [];
    const withWebhook = async (url, options) => {
      if (options.method === "POST") { messages.push(options.body); return { ok: true, status: 200 }; }
      return { ok: false, status: 503 };
    };
    await assert.rejects(monitorProduction({ ...base, webhookUrl: "https://hooks.example.edu/alert", fetchImpl: withWebhook }), /returned HTTP 503/);
    assert.equal(messages.length, 1);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});
