# CampusFlow architecture and implementation plan

## Product decisions

- **Audience:** colleges and universities, including multiple departments, semesters, sections, and campuses.
- **Experience:** hybrid UI; a calm, light administrative workspace and a dark AI planning workspace.
- **Scheduling:** deterministic constraint optimization with Google OR-Tools. The LLM may interpret requests and explain options, but it never decides whether a timetable is valid.
- **Roles:** super admin, college admin, HOD, faculty, and student. Authorization is checked by the API against both role and institution/department scope.

## System shape

```text
Next.js / React / Tailwind
  ├── dashboard and authenticated workspaces
  ├── timetable editor and reports
  └── typed API client
         │ HTTPS, HttpOnly session cookie
FastAPI service
  ├── auth and role/scope policies
  ├── institution, academic, and people modules
  ├── timetable lifecycle and conflict service
  ├── OR-Tools scheduling adapter
  ├── LLM provider interface (optional)
  └── audit and notification events
         │ SQLAlchemy / psycopg
PostgreSQL 15+
```

For production, deploy the web and API separately behind TLS, keep secrets in a managed secret store, run Alembic migrations as a release step, and use a managed PostgreSQL service with backups. Add a queue (Redis-backed worker) for long generation and notification jobs once campus size requires asynchronous work. The initial service keeps interfaces modular so this can be added without changing domain contracts.

## Domain model

- `Institution` owns academic years and policy settings, including the default first-period start time and period length.
- `Department` belongs to an institution; HOD access is scoped here.
- `AcademicTerm` identifies year/term/date range. `Semester` and `Section` organize cohorts.
- `Subject` has lecture/lab requirements, duration, and weekly frequency.
- `Faculty` links a user to qualifications and availability; `Student` belongs to a section.
- `Room` records campus, capacity, and room type (classroom/lab).
- `Timetable` is a versioned draft or published plan. `ScheduleEntry` binds a subject, section, faculty member, room, day, start, and duration.
- `Constraint` captures availability, workload, room suitability, locked periods, and institution rules. Hard constraints must hold; soft constraints are scored and explained.
- `AuditEvent`, `Notification`, and `GenerationRun` record changes and operational outcomes.

## Access and security

Use short-lived signed access tokens carried only in Secure, HttpOnly, SameSite cookies, plus rotating refresh sessions stored hashed in PostgreSQL. Reuse of a consumed refresh token revokes its token family; sign-out, password reset, and account deactivation also revoke refresh sessions. The web API client refreshes once on an expired access token and retries the original request. Passwords use Argon2id. Forgot-password flows use single-use, expiring tokens and do not reveal whether an email exists. The API validates issuer, audience, expiry, browser origin, role, and resource scope. Super admins manage institutions; college admins manage all campus data; HODs manage their department; faculty read assigned schedules and submit availability; students read published schedules for their section. Every write carries an audit record.

Sign-in, sign-up, verification-resend, and password-reset throttles use an atomic Redis sliding window when `RATE_LIMIT_REDIS_URL` is configured; local development falls back to a per-process limiter, while production Compose provides a private shared Redis service and fails auth-limited requests closed if it becomes unavailable. Source-IP limiting remains an ingress responsibility. Planned JWT key rotation supports a bounded overlap with explicitly configured previous signing keys; retention policies and key-storage/rotation operations remain deployment responsibilities. API request logs use route templates, omit raw paths, query strings, headers, and bodies, and return correlation IDs for support. Email verification can be required by deployment configuration. Secure, HttpOnly session cookies, same-site CSRF double-submit tokens, and browser-origin checks are in place.

## Scheduling and AI boundary

The scheduling service first validates input completeness, then builds an OR-Tools CP-SAT model. Hard rules include no faculty/section/room overlap, availability, room capacity/type, locked entries, and required session counts. Soft objectives can favor faculty preferences, spread subjects, avoid gaps, and balance daily load. The solver returns feasible/optimal status, a score, schedule entries, and diagnostics. Infeasible requests return named constraints and the relevant entities where possible.

The assistant is an adapter with a provider-neutral response contract. An explicit timetable-generation request is paired with a user-selected term and department to create a scoped proposal; the user must confirm before the server invokes the existing generation path. When a manager selects a term and department, general planning questions can use a bounded read-only summary of that department's latest published schedule and the institution's room list. HOD context is limited to their own department, and the assistant is instructed not to infer campus-wide room availability from department-only data. Without an LLM key, deterministic guidance explains which planner checks are available. The LLM cannot bypass permissions, solver constraints, or publish approvals.

## API boundaries

- `/api/v1/auth`: sign-up, sign-in, sign-out, refresh, email verification/resend, forgot/reset password, current user.
- `/api/v1/superadmin/institutions`: platform institution directory, institution settings, college-admin invitation/setup resend, and account activation controls. Bootstrap the first super admin only through `python -m app.bootstrap_super_admin` from a trusted operator terminal.
- `/api/v1/institutions`, `/departments`, `/terms`, `/semesters`, `/sections`, `/subjects`, `/people`, `/rooms`: scoped CRUD and imports.
- `/api/v1/campus/timetables`: generate saved drafts from term/department teaching assignments, list versions, read entries, check conflicts, run an atomic optimizer repair for interacting conflicts, edit draft periods, request HOD approval, review/publish, or return a draft with a reason.
- `/api/v1/campus/teaching-assignments`: bind subjects, sections, and faculty with weekly frequency and consecutive-period length.
- `/api/v1/assistant/chat`, `/assistant/confirm`: answer planning requests, propose timetable generation, and run the optimizer only after explicit confirmation.
- `/api/v1/analytics/summary`, `/analytics/reports/{report_type}` and `/export.csv`: scoped dashboard metrics and detailed schedule, faculty-load, room-utilization, and conflict reports.
- `/api/v1/me/notifications`, `/settings/notifications`, `/audit`: in-app notices, user notification preferences, and auditable operations.

## Step-by-step implementation plan

1. **Foundation (current slice):** monorepo layout, responsive product shell, architecture, environment contract, API health/auth scaffolding, SQL models, and solver contract.
2. **Identity and onboarding:** email verification, reset flow, secure super-admin bootstrap, institution directory and college-admin setup, RBAC policies, scoped seed data, and login integration.
3. **Campus data management:** validated CRUD/import screens and API for academic structure, people, subjects, rooms, and availability.
4. **Generation:** CP-SAT model, constraint diagnostics, saved generation runs, version compare, and publish approvals.
5. **Editing and AI:** accessible drag/drop editor, server-validated undo/redo, assistant provider adapters, confirmed draft generation, and conflict resolution suggestions.
6. **Operations:** student/faculty dashboards, notifications, analytics, exports, audit viewer, and settings.
7. **Release:** migrations, automated unit/API/UI checks, accessibility pass, container health checks, CI, monitoring, backups, and deployment guide.

## Current implementation status

This workspace started empty. Foundation work includes the architecture and project scaffolds, responsive dashboard, sign-in/sign-up and password reset screens, cookie-based sessions, PostgreSQL core records, a CP-SAT generation endpoint, optional OpenAI-compatible assistant calls with a guided fallback, local timetable drag-and-drop, and CSV export. The campus setup slice adds institution-scoped create/list/update/delete and CSV import flows for departments, terms, rooms, subjects, semesters, sections, and teaching assignments. Import templates use readable department, term, section, subject, and faculty identifiers; each row is validated and failures are reported without discarding successful rows. Deletes are blocked while dependent records or saved timetable entries refer to the record. Faculty, student, and HOD invitations create scoped role records and send single-use password setup links through configured SMTP; admins can resend links, deactivate/reactivate accounts, and set faculty unavailable periods. Resending invalidates earlier outstanding password links, and account actions are audited. Teaching assignments generate persisted timetable drafts and versions. Drafts are editable through API-validated drag/drop and can be published by a college admin after conflict checks. The unauthenticated dashboard preview uses labeled sample data; signed-in operational dashboards read scoped campus metrics.

This is the foundation and campus setup increment, not the full release. Admin/HOD dashboards use live scoped counts; student and faculty dashboards read published schedules and notifications. Detailed reports now cover published schedule entries (including configured start times), faculty session and period load, room utilization, and published schedule conflicts compared on actual clock intervals across timetable versions with different period lengths; each report can be filtered by academic term, previewed, and exported as CSV. Exports are access-scoped and escape spreadsheet formulas. The audit history view exposes recent changes within admin/HOD access scope. Profile settings and admin institution name/timezone settings are editable and audited. Account invite/resend, scoped profile and teaching-detail edits, active-status controls, and configurable email verification are implemented. Super admins can bootstrap from a trusted CLI, create and edit institutions, invite college administrators, resend setup links, deactivate/reactivate accounts, and select an institution context for campus setup/import. Refresh sessions now rotate and revoke on reuse, sign-out, password reset, and deactivation; web requests retry once after refresh. Faculty availability is managed against all seven calendar weekdays and one to fourteen periods, preserving saved blocks outside the visible period range. Timetable drafts use any selected combination of one to seven weekdays and one to fourteen periods. The editor requests ranked open-slot and alternate-room suggestions after a conflicting move; both suggestions and saved moves enforce faculty availability and section, faculty, and room occupancy, and undo/redo replays moves through the same server validation. Draft move transactions lock the timetable row before checking conflicts, serializing simultaneous edits to the same timetable. The conflict diagnostic endpoint and editor now report each resource overlap, faculty unavailability, room capacity/type mismatch, and schedule-bound violation; approval and publishing use the same diagnostics to block invalid schedules. Per-session repair suggestions and an atomic whole-timetable optimizer repair are available; the latter keeps unaffected sessions in place where possible and never moves locked sessions. HODs can submit conflict-free drafts for approval, and college admins can approve and publish them or return them with a reason. The AI workspace proposes timetable generation for a chosen term and department, waits for explicit confirmation, and then invokes the same authorization and OR-Tools scheduling path. Users can enable or disable in-app notifications for published schedules and approval activity; changes are audited. An Alembic baseline and production container configuration are included. The operations runbook documents readiness/liveness checks, Compose diagnostics, migration visibility, PostgreSQL backup/restore and cron scheduling. Production app ports bind to host localhost; an Nginx TLS and source-IP rate-limit example is included for the public ingress. A host monitor and systemd timer now check public web/API readiness and send webhook alerts on health transitions. Remaining release work includes live deployment review, provider-specific alert setup and monitoring, off-host backup configuration and restore drills, accessibility assessment, and institution-specific privacy/security review.

| Phase | Status |
|---|---|
| 1. Architecture and foundations | Implemented; web lint/build pass |
| 2. Institution setup and campus data | Super-admin CLI bootstrap, institution directory/create/update, institution-scoped campus setup/import, college-admin invitations, resend/setup links, and activation controls implemented; create/list/update/delete/import for core academic records and teaching assignments; faculty/student/HOD invitations, scoped person edits, resend/setup links, account activation, 5–7 day/1–14 period faculty availability, and configurable email verification |
| 3. OR-Tools generation and publish lifecycle | Saved drafts persist configurable one-to-seven selected weekdays and one-to-fourteen period dimensions, weekly versions, room/section/faculty overlaps, mapped faculty availability, room eligibility, schedule-bound diagnostics, weekly workload constraints, repeated-subject spreading, and soft compact-day objectives for faculty and sections; HOD approval requests, admin review, return notes, and publish flow implemented; wider institutional policy diagnostics remain |
| 4. Editing and AI assistant | Server-synced draft drag/drop with saved weekday mappings and dimensions, row-locked move transactions, live diagnostics, per-session suggestions, atomic optimizer repair for interacting conflicts that preserves unaffected sessions and locked entries, server-validated undo/redo, keyboard arrow-key rescheduling with focus restoration, authenticated server-sent campus invalidation events with polling fallback, mapped weekday CSV, institution-configurable bell times, period lengths and recurring weekday breaks enforced by generation, editing, repair and publishing; version snapshots and clock-based cross-version conflict detection, plus confirmed AI-assisted draft generation implemented |
| 5. Operations | Live role-scoped dashboards; faculty/student schedules; user-scoped notification inboxes, read state, and server-event refreshes across campus roles; saved notification preferences; scoped analytics; schedule, faculty-load, room-utilization, and conflict reports with term filter and CSV exports; scoped audit viewer; profile/institution settings |
| 6. Production readiness | CI covers backup and health-monitor script checks, web lint/build, SQLite migrations, API tests, Compose validation, and both container builds; Alembic baseline and production Compose include shared Redis-backed auth throttling and localhost-only app ports; Nginx TLS/source-IP limiting example, transition-based webhook health monitor/systemd timer, database/limiter health checks, key-rotation and backup/restore/scheduling runbooks included; optional encrypted S3-compatible off-host backup upload is implemented; live deployment review, provider setup, restore drills, accessibility, and privacy/security review remain |
