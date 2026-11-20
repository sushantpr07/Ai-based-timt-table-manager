import assert from "node:assert/strict";
import { mkdtemp, mkdir, readFile, readdir, rm, utimes, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { runBackup } from "./backup-postgres.mjs";

test("creates a verified dump, prunes only expired CampusFlow dumps, and removes its container temp file", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "campusflow-backup-"));
  try {
    const envFile = path.join(root, ".env");
    const composeFile = path.join(root, "compose.yml");
    const backupDirectory = path.join(root, "backups");
    await writeFile(envFile, "test");
    await writeFile(composeFile, "test");
    await mkdir(backupDirectory);
    const expired = path.join(backupDirectory, "campusflow-20200101T000000000Z-00000000-0000-4000-8000-000000000000.sql");
    const unrelated = path.join(backupDirectory, "keep.sql");
    await writeFile(expired, "old");
    await writeFile(unrelated, "keep");
    await utimes(expired, new Date("2020-01-01"), new Date("2020-01-01"));
    const calls = [];
    const docker = async args => {
      calls.push(args);
      if (args.includes("cp")) await writeFile(args.at(-1), "-- database dump\n");
    };

    const result = await runBackup({ envFile, composeFile, backupDirectory, retentionDays: 30, now: new Date("2026-11-18T12:00:00Z"), docker });

    assert.equal(result.removed, 1);
    assert.match(path.basename(result.destination), /^campusflow-20261118T120000000Z-[a-f0-9-]+\.sql$/);
    assert.equal(await readFile(result.destination, "utf8"), "-- database dump\n");
    await assert.rejects(readFile(expired));
    assert.equal(await readFile(unrelated, "utf8"), "keep");
    assert.equal(calls.length, 3);
    assert.ok(calls[0].some(argument => argument.includes("pg_dump")));
    assert.ok(calls[2].includes("rm"));
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test("does not leave a partial host dump when copying fails", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "campusflow-backup-failure-"));
  try {
    const envFile = path.join(root, ".env");
    const composeFile = path.join(root, "compose.yml");
    const backupDirectory = path.join(root, "backups");
    await writeFile(envFile, "test");
    await writeFile(composeFile, "test");
    await assert.rejects(runBackup({ envFile, composeFile, backupDirectory, docker: async args => {
      if (args.includes("cp")) throw new Error("copy failed");
    } }), /copy failed/);
    assert.deepEqual(await readdir(backupDirectory), []);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test("uploads the verified dump before pruning and keeps local data if upload fails", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "campusflow-backup-s3-"));
  try {
    const envFile = path.join(root, ".env");
    const composeFile = path.join(root, "compose.yml");
    const backupDirectory = path.join(root, "backups");
    await writeFile(envFile, "test");
    await writeFile(composeFile, "test");
    await mkdir(backupDirectory);
    const expired = path.join(backupDirectory, "campusflow-20200101T000000000Z-00000000-0000-4000-8000-000000000000.sql");
    await writeFile(expired, "old");
    await utimes(expired, new Date("2020-01-01"), new Date("2020-01-01"));
    const docker = async args => { if (args.includes("cp")) await writeFile(args.at(-1), "verified dump\n"); };
    let uploaded;
    const result = await runBackup({ envFile, composeFile, backupDirectory, now: new Date("2026-11-18T12:00:00Z"), docker, s3Uri: "s3://campus-backups/db", s3KmsKeyId: "kms-key", uploader: async (file, uri, options) => { uploaded = { file, uri, options }; } });
    assert.equal(result.uploaded, true);
    assert.equal(uploaded.uri, "s3://campus-backups/db");
    assert.equal(uploaded.options.kmsKeyId, "kms-key");
    await assert.rejects(readFile(expired));

    const stillExpired = path.join(backupDirectory, path.basename(expired));
    await writeFile(stillExpired, "old");
    await utimes(stillExpired, new Date("2020-01-01"), new Date("2020-01-01"));
    await assert.rejects(runBackup({ envFile, composeFile, backupDirectory, now: new Date("2026-11-18T12:00:00Z"), docker, s3Uri: "s3://campus-backups/db", uploader: async () => { throw new Error("upload unavailable"); } }), /upload unavailable/);
    assert.equal(await readFile(stillExpired, "utf8"), "old");
    assert.ok((await readdir(backupDirectory)).some(name => name.endsWith(".sql") && name !== path.basename(stillExpired)));
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});
