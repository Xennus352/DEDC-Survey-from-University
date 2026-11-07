# Existing DEDC database

The application detects and uses the ten-table layout in the supplied `dedc.sql`
directly. No conversion, migration, additional table or additional column is
required. It also supports the previous eight-table application layout.

## Docker setup

Point `DATABASE_URL` in your local `.env` at the existing database. For the local
`dedc` container exposing port 3307, use
`mysql+pymysql://dedc:dedc@127.0.0.1:3307/dedc`. When the app is in the same Docker
network, use the database service hostname and port 3306 instead.

```bash
docker ps
uv run python -m app.portal_auth
uv run uvicorn app.main:app --reload
```

The administrator command inserts an account into `user` and, if needed, an Admin
role into `userrole`. It never replaces an existing account. Use `/portal` to log
in. Import `dedc.sql` only for a new, empty database. An existing database does not
need to be imported again.

## Native tables

| Table | Use |
|---|---|
| `university` | University directory and account/response membership. |
| `ministry` | Ministry directory and account/response membership. |
| `userrole` | Account roles. |
| `user` | Accounts, password hashes, active state and membership. |
| `year` | Question reporting periods; existing status values are preserved. |
| `questiontitle` | Question categories and application metadata in `description`. |
| `uniquestion` | University questions with existing `qTID` and `yID` links. |
| `ministryquestion` | Ministry questions with category and period links. |
| `unisurvey` | University response rows. |
| `ministrysurvey` | Ministry response rows. |

Existing organizations, categories, periods, questions and survey rows are
retained. University source questions are loaded into the workbook query model.
Unmanaged survey rows are preserved in SQL; they are not assigned invented form
versions, respondent accounts or submission ownership in application reports.

## Feature metadata and private files

The explicit [private metadata cutover](private-metadata.md) removes synthetic
`questiontitle` rows without adding tables or columns. In `METADATA_STORAGE=private`
mode, this table contains genuine categories only. Before cutover, SQL metadata
mode retains the representation described below; do not delete those rows manually.

The database has no dedicated columns for dynamic form versions, sections,
choices, rules, or session references. These features use versioned, compressed
JSON metadata in the existing `questiontitle.description` column. Clearly labelled
application records use negative category IDs and are separate from ordinary
categories; do not delete them. Large metadata is split across rows to respect
the MySQL TEXT limit, and checksums detect missing or corrupt fragments.
Question mapping records use this same column without changing a question's
category link. App-created periods may use negative IDs to avoid collisions with
new source periods. Questions and answers use their native audience tables.

`surveyDescription` stores keyed answer JSON, while `remark` preserves submission,
user and field links. New accounts without an organization receive an editable
`Account <id>: <username>` placeholder on their first submission.

`PRIVATE_STORAGE_DIR` (default `private/dedc`) holds content-addressed session,
audit, upload and workbook files. SQL metadata mode commits their references in
the same transaction as form changes. Private mode uses the documented recovery
journal to coordinate SQL and immutable file state. Back up **both MySQL and this directory**;
SQL alone cannot restore uploaded bytes or sessions. All workers must share the
same private directory. Missing or corrupt referenced files fail explicitly.

For the previous eight-table layout, form metadata remains in negative-ID
`uniquestion` rows, and question descriptions retain their existing envelopes.
The application does not convert either layout into the other.

## Runtime and validation

`app/storage/existing.py` maps the ten-table layout, while
`app/storage/schema.py` describes the previous eight-table layout.
`app/storage/compact.py` handles transactions for both. Startup validates
required tables and columns without issuing DDL.

The ORM models in `app/models/` are disposable, in-memory SQLite query
projections. Never run `Base.metadata.create_all` against `DATABASE_URL` or apply
historical Alembic migrations to the existing database. No projection database
file is persisted. MySQL advisory locks serialize units of work across workers.
Feature metadata is loaded per unit of work, suitable for the current small
survey workspace.

```bash
uv run python -m unittest discover -s tests -v
```

Tests use isolated SQLite fixtures for both supported layouts, including portal
authorization, session revocation, forms, submissions, files, rollback, native
record preservation, foreign keys and unchanged table/column structure.
