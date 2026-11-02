# Architecture Audit

This document records the initial audit. For the current implementation, migrations and test results, see `IMPLEMENTATION_REPORT.md` and `IMPLEMENTATION_PLAN.md`.

Inspected 2026-11-02 against `AdminSketch.md`. Database inventory was read-only; no live records or schemas were changed.

## Existing application

- Python 3.12+, FastAPI, SQLAlchemy, Pydantic Settings, Jinja2, plain JavaScript and CSS. Dependencies use uv. No React/Flutter source, JavaScript build pipeline, chart library, browser-test runner, or configured linter exists in this repository.
- `app/main.py` mounts static assets and registers API and web routers. `app/dependencies.py` owns request-scoped database sessions. Templates and static files are resolved from the repository root.
- Public APIs currently declared: survey CRUD/list/year queries under `/surveys`, question create/list under `/questions/survey/{id}`, response create/read/list under `/responses`. Public HTML is `/`; administrator login is `/portal`, dashboard is `/dashboard`.
- Public landing-page login dialog is explicitly a disconnected demo. Preserve layout while connecting it to the real portal in the dashboard/UI phase; do not extend its fake behavior.

## Authentication findings and implemented repair

Existing logout already deleted the server session and both legacy `/portal` and root cookies; password validation, CSRF, session rotation, expiry and account-role checks existed. Protection was implemented only inside the root dashboard handler. The dashboard had no history/tab revalidation script.

`app/admin_auth.py` now guards the whole `/dashboard` and `/api/admin` namespaces before dispatch, including nonexistent and future paths. Pages redirect unauthorized visitors to login; APIs return 401 for absent/expired sessions and 403 for unauthorized accounts. Unsafe admin requests require `X-CSRF-Token`. A shared dependency exposes the verified administrator identity. Every protected request checks the current active account and role against the database; authenticated identities are never cached across requests.

`GET /api/admin/session` supports browser revalidation without returning credentials. The dashboard hides on page departure/history restoration/tab suspension and checks the backend before revealing itself again. Confirmed logout broadcasts a credential-free signal across tabs; errors retain the session and show a focused, accessible retry message. Protected responses forbid caching.

There are no refresh tokens, client-side credentials, authenticated WebSockets, service workers, or user-data caches to invalidate. Admin WebSocket upgrades are denied until a revocation-aware connection implementation exists. Test server and browser fixtures use disposable SQLite, never the configured MySQL.

## Critical database mismatch

The live local MySQL database has **11 tables** (full columns, keys, indexes: `database-schema-audit.json`):

- `user`, `userrole`, `admin_sessions` — mapped by current portal models.
- `university`, `ministry`, `year` — organization and reporting-period dimensions.
- `questiontitle` — shared question categories/sections.
- `uniquestion`, `ministryquestion` — question text, category and year foreign keys.
- `unisurvey`, `ministrysurvey` — organization/question answers with `hasItem`, `itemCount`, `surveyDescription`, `remark`, `submittedAt`, `updatedAt`.

The separate Python `Survey`, `Question`, `Option`, `Response`, `Answer` models reference `surveys`, `questions`, `options`, `responses`, `answers`, which **do not exist in this database**. Their package exports are empty; `Response` also references an unimported `String`. Existing portal tests never exercise these routes. These are pre-existing defects, not evidence that mobile APIs work. There is no Flutter client or external integration contract here to verify against.

Alembic is installed but there is no configuration, migration directory, or version table. The session table currently bootstraps at application startup.

## Required database strategy for the next phase

1. Register/fix existing ORM imports and add legacy API contract tests before extending routers.
2. Map the actual university/ministry/year/category/question/answer tables. Preserve identifiers, foreign keys and historical records.
3. Establish a non-destructive Alembic baseline with explicit detection of existing tables; test on disposable MySQL and SQLite. Do not autogenerate a migration that drops the live tables because they are absent from ORM metadata.
4. Add form/version metadata, section/question configuration, normalized options/rules, submission grouping, files and audit logs only where the existing entities cannot represent them. Link legacy question/answer IDs explicitly; do not copy answers into a disconnected replacement system.
5. Keep old endpoint paths and payloads stable through adapters and regression tests. Published versions must be immutable, and historic answers must resolve their original question version.

## Validation at this checkpoint

- Baseline: 17 portal tests passed.
- Expanded suite: 24 portal/auth tests passed against isolated SQLite.
- Headless Firefox: login, logout, direct nested entry, refresh, copied cookie, cross-tab logout, browser Back and expired session checks passed. Failed-logout recovery, retained session, restored button and accessible error focus also passed.
- No migrations or form/report CRUD changes have been made yet. Production readiness and Flutter compatibility remain unverified.
