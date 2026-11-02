# Database Table Guide

This guide explains the tables registered by the application and migrations. The database schema audit at `context/database-schema-audit.json` is a snapshot of the original local MySQL schema **before** the new form-system migrations; it lists 11 tables. Migrations `0001`–`0004` add the tables described below. Use `uv run alembic current` and `uv run alembic heads` to check the migration state of a configured database.

The configured local MySQL database was inspected read-only on 2026-11-02. It has 29 tables including Alembic's migration bookkeeping table. Several legacy workflow tables are empty, but their API routes remain active. The four imported forms, 100 original source-answer rows, and existing account/question records are present; there are no new survey submissions yet.

## Existing accounts and organization data

| Table | Purpose |
|---|---|
| `userrole` | Role names assigned to accounts. |
| `user` | Login accounts, password hashes, active state, and optional organization membership. |
| `university`, `ministry` | Organization records used by accounts and the legacy survey API. |
| `year` | Reporting-period records referenced by legacy question definitions. |
| `questiontitle` | Shared category/title for legacy questions and imported form sections. |
| `uniquestion`, `ministryquestion` | Legacy question definitions for each audience. Imported dynamic fields link back to these records. |
| `unisurvey`, `ministrysurvey` | Legacy answer records submitted by the Flutter-compatible university and ministry workflows. Keep these while those clients or records are in use. |

## Legacy survey API

| Table | Purpose |
|---|---|
| `surveys` | Parent records for the original generic `/surveys` API. |
| `questions` | Questions belonging to a generic survey. |
| `options` | Choice options belonging to a generic question. |
| `responses` | Respondent submissions to a generic survey. |
| `answers` | Individual answer values linked to a response and question. |

These tables are separate from `unisurvey` and `ministrysurvey`. The original API routers and CRUD modules still use them; dropping them would break those endpoints. They are created by the baseline migration if absent.

## Dynamic forms and reporting

| Table | Purpose |
|---|---|
| `survey_forms` | Stable identity and audience for a form across versions. |
| `survey_form_versions` | Versioned title, language, publication state, availability, and reporting-period defaults. |
| `survey_sections` | Ordered sections, visibility conditions, and optional imported category link. |
| `survey_fields` | Ordered question/input definitions, validation and conditional configuration, and legacy source links. |
| `survey_field_options` | Ordered choice values for a field. |
| `survey_submissions` | Respondent, form version, completion state, reporting dates, timestamps, and location. |
| `survey_field_answers` | One stored answer value per field and submission. |
| `survey_answer_files` | Uploaded response attachments, ownership, metadata, and binary file content. |
| `survey_workbook_imports` | Import digest, worksheet, target draft version, importing user, and timestamp; prevents duplicate imports. |
| `survey_workbook_answers` | Original workbook answer observations retained separately from new respondent submissions. |
| `survey_workbook_templates` | Original workbook bytes keyed by digest so exact-layout Excel exports remain available. |
| `audit_logs` | Administrative and authentication actions, actor, target, and safe change metadata. |
| `admin_sessions` | Hashes and expiry times for revocable admin browser sessions; raw session tokens are not stored. |
| `alembic_version` | Alembic's single current migration revision; required to know which schema upgrades have run. |

## Which tables can be removed?

No table is currently confirmed safe to remove. The empty generic API tables (`surveys`, `questions`, `options`, `responses`, `answers`) are still used by the original `/surveys`, `/questions`, and `/responses` routes. The empty university/ministry response tables are reserved for the existing Flutter workflows. Empty file or attachment tables are part of implemented form features. In particular, workbook/source-answer tables preserve information needed for exact exports and provenance. Do not drop tables based only on their names or row counts. Before any future retirement, identify all application/client references, take and verify a database backup, migrate any required records, and remove the associated routes/models in a reviewed migration. The migrations in this project are intentionally additive and do not delete existing data.
