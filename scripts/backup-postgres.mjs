import { spawnSync } from "node:child_process";
import { randomUUID } from "node:crypto";
import { access, mkdir, readdir, rename, rm, stat, lstat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { parseArgs } from "node:util";

const scriptPath = fileURLToPath(import.meta.url);
export const projectRoot = path.resolve(path.dirname(scriptPath), "..");

function runDocker(args) {
  const result = spawnSync(process.env.CAMPUSFLOW_DOCKER_BIN ?? "docker", args, {
    cwd: projectRoot,
    encoding: "utf8",
    windowsHide: true,
  });
  if (result.error) throw result.error;
  if (result.status !== 0) {
    const details = (result.stderr || result.stdout || "").trim();
    throw new Error(`docker compose ${args.join(" ")} failed${details ? `: ${details}` : ""}`);
  }
  return result.stdout;
}

function uploadToS3(file, uri, { endpointUrl, kmsKeyId } = {}) {
  const args = ["s3", "cp", file, `${uri.replace(/\/$/, "")}/${path.basename(file)}`, "--sse", kmsKeyId ? "aws:kms" : "AES256"];
  if (kmsKeyId) args.push("--sse-kms-key-id", kmsKeyId);
  if (endpointUrl) args.push("--endpoint-url", endpointUrl);
  const result = spawnSync(process.env.CAMPUSFLOW_AWS_BIN ?? "aws", args, {
    cwd: projectRoot,
    encoding: "utf8",
    windowsHide: true,
  });
  if (result.error) throw result.error;
  if (result.status !== 0) {
    const details = (result.stderr || result.stdout || "").trim();
    throw new Error(`aws s3 cp failed${details ? `: ${details}` : ""}`);
  }
}

function utcStamp(date) {
  return date.toISOString().replace(/[-:]/g, "").replace(/\.(\d{3})Z$/, "$1Z");
}

export async function pruneBackups(directory, retentionDays, now = Date.now()) {
  const cutoff = now - retentionDays * 24 * 60 * 60 * 1000;
  const names = await readdir(directory, { withFileTypes: true });
  let removed = 0;
  for (const item of names) {
    if (!item.isFile() || !/^campusflow-\d{8}T\d{9}Z-[a-f0-9-]+\.sql$/.test(item.name)) continue;
    const filePath = path.join(directory, item.name);
    const info = await lstat(filePath);
    if (!info.isFile() || info.mtimeMs >= cutoff) continue;
    await rm(filePath);
    removed += 1;
  }
  return removed;
}

export async function runBackup({ envFile, composeFile, backupDirectory, retentionDays = 30, now = new Date(), docker = runDocker, s3Uri, s3EndpointUrl, s3KmsKeyId, uploader = uploadToS3 }) {
  if (!Number.isInteger(retentionDays) || retentionDays < 1 || retentionDays > 3650) {
    throw new Error("Retention days must be an integer from 1 to 3650.");
  }
  if (s3Uri && !/^s3:\/\/[^/]+(?:\/[^\s]*)?$/.test(s3Uri)) throw new Error("--s3-uri must be an S3 bucket URI (s3://bucket/prefix).");
  if ((s3EndpointUrl || s3KmsKeyId) && !s3Uri) throw new Error("--s3-endpoint-url and --s3-kms-key-id require --s3-uri.");
  await access(envFile);
  await access(composeFile);
  await mkdir(backupDirectory, { recursive: true });

  const stamp = utcStamp(now);
  const runId = randomUUID();
  const dumpName = `campusflow-${stamp}-${runId}.sql`;
  const destination = path.join(backupDirectory, dumpName);
  const partial = `${destination}.partial`;
  const containerDump = `/tmp/${dumpName}`;
  const composeArgs = ["compose", "--env-file", envFile, "-f", composeFile];
  const dumpCommand = `pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-privileges -f "${containerDump}"`;

  try {
    await docker([...composeArgs, "exec", "-T", "db", "sh", "-c", dumpCommand]);
    await docker([...composeArgs, "cp", `db:${containerDump}`, partial]);
    const dumpInfo = await stat(partial);
    if (!dumpInfo.isFile() || dumpInfo.size === 0) throw new Error("PostgreSQL returned an empty backup file.");
    await rename(partial, destination);
    // Keep the verified local copy and expired backups if off-site upload fails.
    if (s3Uri) {
      await uploader(destination, s3Uri, { endpointUrl: s3EndpointUrl, kmsKeyId: s3KmsKeyId });
    }
    const removed = await pruneBackups(backupDirectory, retentionDays, now.getTime());
    return { destination, removed, uploaded: Boolean(s3Uri) };
  } catch (error) {
    await rm(partial, { force: true }).catch(() => undefined);
    throw error;
  } finally {
    try {
      await docker([...composeArgs, "exec", "-T", "db", "rm", "-f", containerDump]);
    } catch (error) {
      console.warn(`Could not remove the temporary database dump ${containerDump}: ${error.message}`);
    }
  }
}

async function main() {
  const { values } = parseArgs({
    options: {
      help: { type: "boolean", short: "h" },
      "env-file": { type: "string", default: ".env" },
      "compose-file": { type: "string", default: "compose.production.yml" },
      "backup-dir": { type: "string", default: "backups" },
      "retention-days": { type: "string", default: "30" },
      "s3-uri": { type: "string" },
      "s3-endpoint-url": { type: "string" },
      "s3-kms-key-id": { type: "string" },
    },
    strict: true,
  });
  if (values.help) {
    console.log("Usage: node scripts/backup-postgres.mjs [--env-file PATH] [--compose-file PATH] [--backup-dir PATH] [--retention-days DAYS] [--s3-uri s3://bucket/prefix] [--s3-endpoint-url URL] [--s3-kms-key-id KEY]");
    return;
  }
  const retentionDays = Number(values["retention-days"]);
  if (!Number.isInteger(retentionDays)) throw new Error("--retention-days must be an integer.");
  const envFile = path.resolve(projectRoot, values["env-file"]);
  const composeFile = path.resolve(projectRoot, values["compose-file"]);
  const backupDirectory = path.resolve(projectRoot, values["backup-dir"]);
  const result = await runBackup({ envFile, composeFile, backupDirectory, retentionDays, s3Uri: values["s3-uri"], s3EndpointUrl: values["s3-endpoint-url"], s3KmsKeyId: values["s3-kms-key-id"] });
  console.log(`Created ${result.destination}${result.uploaded ? ` and uploaded to ${values["s3-uri"]}` : ""}${result.removed ? `; removed ${result.removed} expired backup(s)` : ""}.`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  main().catch(error => {
    console.error(error.message);
    process.exitCode = 1;
  });
}
