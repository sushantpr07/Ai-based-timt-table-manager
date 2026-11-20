# CampusFlow — AI Timetable Manager

CampusFlow is a college and university timetable platform built around a React dashboard, a FastAPI service, PostgreSQL, and an OR-Tools scheduling engine. The UI uses a light workspace for daily operations and a dark workspace for AI planning.

## Architecture

See [docs/architecture.md](docs/architecture.md) for the system boundaries, data model, access model, and implementation sequence.
See [docs/operations.md](docs/operations.md) for deployment checks, API readiness, database backup/restore, migration operations, and security hardening guidance.

## Local setup

Prerequisites: Node.js 20+, Python 3.11+, Docker Desktop (or PostgreSQL 15+), and an optional LLM API key.

1. Copy `.env.example` to `.env` and set a long `JWT_SECRET`. The example enables local table creation and leaves email verification optional; set `AUTO_CREATE_SCHEMA=false` and `REQUIRE_EMAIL_VERIFICATION=true` outside local development. Set `LLM_PROVIDER=openai` or `LLM_PROVIDER=gemini`, then add the matching server-side API key in `LLM_API_KEY`; without a key, the assistant uses guided mode. Configure SMTP fields to enable email verification, invitations, and password reset delivery.
2. Start PostgreSQL: `docker compose up -d db`.
3. Start the API from `apps/api`: `python -m venv .venv`, activate it, `pip install -r requirements.txt`, then `uvicorn app.main:app --reload --no-access-log --port 8000`.
4. Start the web app from `apps/web`: `npm install`, then `npm run dev`.
5. Open `http://localhost:3000`. API docs are at `http://localhost:8000/docs`.

The local `.env.example` enables table creation for convenience. The API also has an Alembic baseline; production uses `AUTO_CREATE_SCHEMA=false` and applies migrations before starting. Never commit `.env` or real API keys. The first dashboard currently has a labeled sample preview so the interface is useful before a college is configured.

## Bootstrap the platform super admin

The first super-admin account is created from a trusted operator terminal; there is no public endpoint that can grant this role. Apply database migrations first, then run `python -m app.bootstrap_super_admin` from `apps/api` and enter the account email, name, and password at the prompts. In a running production Compose deployment, run `docker compose --env-file .env -f compose.production.yml exec -it api python -m app.bootstrap_super_admin`. The command refuses to create a second super admin. Sign in with that account, open **Settings → Institution directory**, create institutions, and invite their college administrators. The super admin can also open **Academics**, **People**, or **Classrooms**, choose a working institution, and set up or import its campus records. SMTP must be configured to deliver admin setup links.

The current development slice has working sign-in/sign-up/password recovery, rotating refresh sessions with replay detection, create/list/edit/delete and CSV import for academic structure and rooms, people invitations with resendable setup links and scoped account activation controls, persisted timetable drafts and versions generated from teaching assignments, server-checked draft editing with open time/room suggestions and undo/redo, an AI workspace that receives access-scoped published schedule context and proposes draft generation only after user confirmation, role-specific dashboards, faculty/student published schedules, configurable in-app notification preferences, scoped analytics and term-filtered schedule/faculty-load/room-utilization/conflict reports with CSV exports, audit history, and editable profile/institution settings, including configurable bell times.

## Generate the first timetable

1. Sign up to create the initial college admin account. The web UI defaults to the API at `http://localhost:8000`.
2. In **Academics**, create departments and an academic term, then create semesters, sections, and subjects. Invite faculty in **People**; SMTP must be configured for their one-time password links.
3. Add rooms in **Classrooms**. In **People → Faculty**, set blocked teaching periods for each faculty member. In **Academics → Teaching assignments**, assign a subject, section, faculty member, weekly frequency, and period length.
4. Open **Timetable**, choose the term and department, and generate a draft. Drag sessions to move them; the API rejects moves that create room, section, or faculty conflicts and offers open time/room alternatives. Use **Undo** and **Redo** to reverse or replay saved moves; each replay is checked by the API against current constraints. A college admin can publish a conflict-free draft.

Department heads can submit a conflict-free draft for approval. Submitted drafts become read-only until a college admin approves and publishes them or returns them with a reason. College admins can also publish their own conflict-free drafts directly.

New timetable drafts default to Monday-to-Friday and eight periods, with controls for selecting any combination of one to seven weekdays and one to fourteen periods per day. The selected weekday mapping is saved with each version and used by generation, availability checks, diagnostics, personal schedules, and CSV reports. College admins can configure the first-period start time, period length, and recurring weekday break windows in Settings. Breaks are hard constraints during generation, editing, repair, and publishing; each generated version keeps its own period labels and length.

## Checks

Web: `npm run lint` and `npm run build` from `apps/web`.

API: `pytest` from `apps/api`. Operational scripts: `node --test scripts/backup-postgres.test.mjs scripts/monitor-production.test.mjs`. CI also applies Alembic migrations on SQLite and builds both production container images without publishing them.

## Production container deployment

The `compose.production.yml` file builds the web and API containers, PostgreSQL, and a private Redis service for shared authentication rate limits. Both application containers run as unprivileged users; their host ports bind only to localhost, and Redis is not published. Copy `.env.example` to a deployment-only `.env`, set a unique random `JWT_SECRET` (at least 32 bytes), strong database credentials, and the public HTTPS origins. For planned JWT-key rotation and Nginx ingress setup, see [the operations runbook](docs/operations.md); keep `JWT_PREVIOUS_SECRETS` empty during normal operation. Set `DATABASE_URL` to the internal `db` hostname, with URL-encoded credentials, and set `NEXT_PUBLIC_API_URL` to the public API address ending in `/api/v1`; that web setting is embedded when the image is built. Email verification is enabled by default in production Compose, so configure SMTP for verification, invitations, and password reset. An LLM provider key is optional. Then run `docker compose -f compose.production.yml up --build -d`. The API container applies Alembic migrations before serving traffic. Configure public TLS ingress, scheduled backups, and the optional host availability monitor before campus rollout. Do not use the sample values from `.env.example` in production.

For an existing local database created with `AUTO_CREATE_SCHEMA=true`, verify it matches the current models, then from `apps/api` run `alembic stamp 0001_initial` to begin tracking it. For a new database, `alembic upgrade head` creates the schema. Review every generated migration before applying it to shared data.

## Delivery sequence

1. Architecture and foundations: dashboard shell, API health, core schema, secure authentication boundaries.
2. Institution setup: academic years, departments, semesters, sections, rooms, subjects, students, faculty, and role assignments.
3. Scheduling: hard/soft constraints, OR-Tools generation, conflict explanations, versioning, and publish workflow.
4. Operations: drag-and-drop editor, AI assistant, notifications, analytics, reports, exports, audit history, and settings.
5. Production readiness: migrations, integration/accessibility checks, observability, container deployment, backups, and security review.

The application is being developed incrementally. The plan and current implementation status live in `docs/architecture.md`.
