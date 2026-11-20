# CampusFlow operations runbook

This runbook covers the single-host Docker Compose deployment in `compose.production.yml`. It is a starting point for a production operator; use managed PostgreSQL and an HTTPS ingress for multi-instance or higher-availability deployments.

## Deploy and verify

1. Keep the deployment `.env` outside source control. Set strong database credentials, a random `JWT_SECRET` of at least 32 bytes, public HTTPS origins, and `NEXT_PUBLIC_API_URL` ending in `/api/v1`. The API refuses short signing keys, short rotation keys, and obvious placeholder keys when either public origin uses HTTPS.
2. Start or update the stack with `docker compose --env-file .env -f compose.production.yml up --build -d`.
3. Follow startup and migration output with `docker compose --env-file .env -f compose.production.yml logs -f api`.
4. Check service state with `docker compose --env-file .env -f compose.production.yml ps`. The database and API containers must become healthy before the web container starts.
5. Check API readiness from the host with `curl -fsS https://api.example.edu/api/v1/health`. This endpoint runs a database query and returns HTTP 503 if PostgreSQL is unavailable. `/api/v1/health/live` checks only that the API process responds.
6. Check recent failures with `docker compose --env-file .env -f compose.production.yml logs --since 30m api web db`. Alert on unhealthy containers, repeated API 5xx responses, database restarts, and exhausted disk space. API request logs use route templates and omit raw paths, query strings, headers, and bodies; retain the generated request ID when correlating a client report with server logs. Configure `LOG_LEVEL` (`info`, `warning`, or `error`) only as needed and restrict log access.

The Compose stack is a single API instance. Its image startup applies Alembic migrations before launching Uvicorn. For deployments that scale the API beyond one replica, run migrations once as a release job before bringing up new replicas; do not let multiple replicas race to apply schema changes.

### Host Nginx ingress

Production Compose binds the web and API ports to `127.0.0.1` on the host, so they cannot be reached directly from the public network. Configure a host Nginx instance with the TLS certificates and hostnames used by `WEB_ORIGIN`, `API_ORIGIN`, and `NEXT_PUBLIC_API_URL`. Start from [`deploy/nginx/campusflow.conf`](../deploy/nginx/campusflow.conf), replace the example hostnames/certificate paths, then validate with `nginx -t` and reload Nginx. The example routes web traffic to port 3000, API traffic to port 8000, disables buffering for the event stream, and applies source-IP limits to sign-in, sign-up, recovery, and verification endpoints. The account/address-based API limits remain active as a second layer.

Authenticated timetable editors receive server-sent invalidation events after audited campus writes; the event contains no campus data, and clients fetch updates through their normal scoped API routes. The current broker is process-local, which fits the single API instance in this Compose stack. If running multiple API replicas, replace it with a shared Redis pub/sub broker so every replica's connected clients receive changes. The browser retains periodic synchronization as a reconnect and compatibility fallback.

The sample assumes clients connect directly to Nginx. If a CDN or load balancer sits in front, configure Nginx `set_real_ip_from` only for that provider's published proxy CIDRs and use its documented real-IP header; never trust arbitrary forwarded-IP headers. Keep the Nginx host firewall limited to public ports 80/443 and restrict SSH separately.

### Availability alerts

The host monitor checks the public web URL and API readiness URL every minute and sends an alert only when health changes; it sends a recovery message after both checks pass again. The webhook accepts a JSON `text` field, which works with common incoming-webhook integrations. Configure a provider webhook URL in the host secret store; do not commit it:

```sh
sudo install -d -m 0750 /etc/campusflow
sudo install -m 0640 /dev/null /etc/campusflow/monitor.env
sudoedit /etc/campusflow/monitor.env
```

Set `CAMPUSFLOW_WEB_HEALTH_URL=https://campus.example.edu/` and `CAMPUSFLOW_API_HEALTH_URL=https://api.campus.example.edu/api/v1/health`. Set `ALERT_WEBHOOK_URL` to the configured provider endpoint and `CAMPUSFLOW_MONITOR_STATE=/var/lib/campusflow-monitor/state.json`. Install the repository under `/opt/campusflow`, create the dedicated service account, and install/enable the timer:

```sh
sudo useradd --system --home-dir /nonexistent --shell /usr/sbin/nologin campusflow-monitor
sudo chown root:campusflow-monitor /etc/campusflow/monitor.env
sudo chmod 0640 /etc/campusflow/monitor.env
sudo install -m 0644 deploy/systemd/campusflow-monitor.service /etc/systemd/system/
sudo install -m 0644 deploy/systemd/campusflow-monitor.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now campusflow-monitor.timer
sudo systemctl start campusflow-monitor.service
sudo journalctl -u campusflow-monitor.service -n 30 --no-pager
```

The monitor stores only check state under `/var/lib/campusflow-monitor`; failed webhook delivery does not update state, so the next timer run retries the notification. A failed check exits nonzero and is visible in the systemd journal. This is a basic availability signal; also configure provider-side alert delivery monitoring and host/disk/container monitoring for production operations.

## Back up PostgreSQL

Run the backup outside the request path. The script creates a uniquely named plain SQL dump, verifies it is non-empty, promotes it atomically into the host backup folder, and removes only expired files matching its CampusFlow backup naming pattern:

```sh
node scripts/backup-postgres.mjs --env-file /etc/campusflow/.env --backup-dir /var/backups/campusflow --retention-days 30
```

For off-host storage, install and configure the AWS CLI with an instance role or another credential provider (never put cloud credentials in the repository). Add `--s3-uri s3://YOUR-BUCKET/campusflow` to the command. The script uploads each verified dump with server-side encryption (AES256 by default); use `--s3-kms-key-id KEY_ID` for AWS KMS encryption. S3-compatible services can use `--s3-endpoint-url https://OBJECT-STORE-ENDPOINT`. Expired local backups are pruned only after upload succeeds. If upload fails, the verified local dump and existing backups remain, and the command exits with an error so cron can alert on it. Configure bucket-side access restrictions, lifecycle retention, and encryption policy with the institution.

Example daily cron entry with S3 upload:

```cron
15 2 * * * cd /opt/campusflow && /usr/bin/node scripts/backup-postgres.mjs --env-file /etc/campusflow/.env --backup-dir /var/backups/campusflow --retention-days 30 --s3-uri s3://YOUR-BUCKET/campusflow --s3-kms-key-id YOUR-KMS-KEY-ID >> /var/log/campusflow-backup.log 2>&1
```

Schedule it on the Compose host. For example, a Linux cron entry runs every day at 02:15; replace the project path and Node path with the installed values, and ensure the operator account can read the environment file and write to the backup directory:

```cron
15 2 * * * cd /opt/campusflow && /usr/bin/node scripts/backup-postgres.mjs --env-file /etc/campusflow/.env --backup-dir /var/backups/campusflow --retention-days 30 >> /var/log/campusflow-backup.log 2>&1
```

Restrict backup access and define retention with the institution. A database volume is persistence, not a backup. Back up deployment configuration and the secret store separately; never put secrets in the SQL dump or source control. Schedule and document restore drills.

## Restore a backup

Practice restores into an isolated staging deployment first. A plain `pg_dump` restore requires an empty target database. These commands assume a fresh, empty PostgreSQL instance (for Compose, start with an empty database volume); do not point them at a database that contains data. Stop API writes, start the database, copy the dump into its container, then restore with `ON_ERROR_STOP` enabled:

```sh
docker compose --env-file .env -f compose.production.yml stop api
docker compose --env-file .env -f compose.production.yml up -d db
docker compose --env-file .env -f compose.production.yml cp ./backups/campusflow-backup.sql db:/tmp/campusflow.sql
docker compose --env-file .env -f compose.production.yml exec -T db sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /tmp/campusflow.sql'
docker compose --env-file .env -f compose.production.yml exec -T db rm -f /tmp/campusflow.sql
docker compose --env-file .env -f compose.production.yml up -d api web
```

Do not run the restore against a database containing data you need to retain. Take a fresh backup before any production recovery and verify user sign-in, timetable reads, and reports after the restore.

## Schema changes and rollback

- Review migration scripts and test both `alembic upgrade head` on a copy of production data and application startup before release.
- The API image applies migrations on startup. Keep a verified database backup before deploying schema changes.
- Prefer forward fixes. An older application image may not work against a newer schema; restore a backup only under an approved recovery plan.
- Check the active migration revision with `docker compose --env-file .env -f compose.production.yml exec -T api alembic current`.

## Rotate JWT signing keys

For a planned rotation, deploy the new random key as `JWT_SECRET` and place the prior key in `JWT_PREVIOUS_SECRETS`. The API signs all new access tokens with `JWT_SECRET` and accepts both current and previous keys for verification. Keep the previous key configured for at least the maximum access-token lifetime plus deployment propagation time, then remove it and restart every API instance. Use the same key set on every replica during the overlap. For a suspected key compromise, omit the compromised key from `JWT_PREVIOUS_SECRETS` immediately; affected access tokens stop working, while users can obtain new access tokens through their database-backed refresh sessions if those remain valid. Store both variables in the secret manager and never put real values in source control or logs.

## Security and availability checklist

- Terminate TLS at a maintained reverse proxy or managed ingress. Expose only web/API routes publicly; keep PostgreSQL private.
- Use a unique production secret and managed secret storage. Rotate credentials after suspected exposure.
- Configure SMTP before enabling required email verification, invitations, and password recovery. Keep the LLM key optional and scoped to the provider account.
- When an LLM key is configured, assistant requests that include a selected term and department send the authorized department's published schedule summary and the institution room directory to the configured provider. Do not include sensitive student information in assistant prompts; without an LLM key, CampusFlow uses local guided responses.
- The API throttles sign-in (10 per account per 5 minutes), sign-up (5 per address per 15 minutes), and verification resend/password-reset requests (3 per address per 15 minutes). Keys are hashed. Production Compose uses a private Redis service for atomic shared sliding windows; if that store is unavailable, auth-limited requests fail closed and API readiness returns 503. Local development without `RATE_LIMIT_REDIS_URL` uses the per-process fallback. Add source-IP limits at the trusted ingress; every API replica must point at the same secured Redis service.
- The Compose Redis service has no persistence because the limiter stores only short-lived windows; a Redis restart clears active counters. It has no host-published port and is attached to a private network shared only with the API.
- Apply host security updates, enable the availability monitor and alert delivery, monitor container and disk health, and test backup restoration on a schedule.
- Session-authenticated writes require the CSRF cookie value in the `X-CSRF-Token` header; keep the web and API origins in the configured CORS allowlist and verify the cookie/header flow through the production ingress.
- Before a campus-wide rollout, configure ingress source-IP limits, run a staged key-rotation exercise, complete accessibility review, and perform an institution-specific privacy/security assessment.
