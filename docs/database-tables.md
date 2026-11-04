# DEDC eight-table database

The configured MySQL database uses exactly the eight tables supplied in the
November 2026 `dedc.sql`. The repository's `dedc.sql` is that original, empty
schema. A populated, private `dedc.sql` is generated under `backups/` during
conversion. The original file in Downloads is never overwritten.

| Table | Persistent records |
|---|---|
| `university` | University organizations, referenced by accounts and responses. |
| `ministry` | Ministry organizations, referenced by accounts and responses. |
| `userrole` | Account roles. |
| `user` | Accounts, existing password hashes, active state and organization membership. |
| `uniquestion` | University source questions and custom questions; JSON form metadata in `description`. |
| `ministryquestion` | Ministry questions and their metadata in `description`. |
| `unisurvey` | University responses, including native presence/count columns and JSON answer values. |
| `ministrysurvey` | Ministry responses using the same presence/count/JSON representation. |

The table name is **`uniquestion`**, singular, exactly as in the supplied SQL.
University fields imported from a workbook share their original source question:
the presence, quantity and detail controls do not create three copies of it.
Custom fields are stored in the appropriate audience's question table.

## JSON and private files

The supplied schema has no columns for form sections, multiple input types,
options, rules, drafts, immutable published versions, workbook provenance, review
status or reporting-period dates. These features are preserved using versioned
JSON envelopes in existing text columns, without adding SQL tables or columns.

`uniquestion` reserves **negative IDs** for clearly labelled application metadata
records. They are not respondent questions and no survey references them. Their
`description` contains a JSON envelope with a format identifier, fragment number,
SHA-256 checksum and compressed/base64 JSON payload. Normal questions have
positive IDs. Exclude negative IDs when counting university questions directly
in SQL (`WHERE uQId > 0`). Large metadata is split across records to respect the
64 KiB `TEXT` limit.

The metadata preserves form/field IDs, sections, options, versions, source
categories and periods, imports, verbatim workbook observations, and submission
history. Normal question and answer rows are also materialized in the native
university/ministry tables. `surveyDescription` contains keyed answer JSON;
`remark` contains the submission/user/field links and lossless answer values.
Compound quantity text remains JSON instead of being truncated into `itemCount`.

`PRIVATE_STORAGE_DIR` (default `private/dedc`) contains hashed session records,
audit history, attachment bytes and original workbook bytes. Files are immutable
and named by their SHA-256 content hash. SQL metadata commits their references
atomically. Files are written with private permissions, checked for integrity
when read, and are never mounted as static assets. Existing session expiry,
logout revocation, CSRF, role checks and authorized file downloads still apply.
Back up **both MySQL and this directory**. A SQL-only restore cannot recover
private sessions, audit data or uploaded bytes. Unreferenced files from rolled
back operations are harmless and are retained; automatic garbage collection is
not implemented.

Existing accounts with no organization retain null membership. On their first
submission for an audience, the application creates an organization labelled
`Account <id>: <username>` with university type `Unspecified`, where needed.
Replace these placeholders with the real organization names in the native
organization tables. No real institution name is invented.

## Runtime query model

The existing SQLAlchemy models in `app/models/` describe **disposable in-memory
query projections**, not additional persistent tables. Each unit of work loads
the JSON feature data into an isolated memory-only SQLite engine so the existing
builder, validation, reporting filters and export queries keep their behavior.
The configured MySQL database contains only the eight supplied tables; no query
projection or SQLite database file is persisted by the running application.

`app/storage/schema.py` is the authoritative persistent schema.
`app/storage/compact.py` reads/writes it. Do not run `Base.metadata.create_all`
against `DATABASE_URL`. Native account rows are read directly on each request,
so role changes/deactivation take effect immediately. The native response rows
and question descriptions are application-managed; edit forms and answers
through the application so their version metadata stays consistent.

MySQL advisory locks serialize units of work across workers. The entire feature
metadata is loaded per unit of work, making this suitable for the current small
survey workspace, not a high-throughput or unbounded reporting system. All
workers must use the same database endpoint and shared private-file directory.
Missing/corrupted private files or incomplete metadata fail explicitly instead
of silently dropping data. Read-only sessions do not rewrite storage.

## Conversion and recovery

Stop application writes, then run:

```bash
uv run python scripts/convert_eight_tables.py          # backup + stage + verify
uv run python scripts/convert_eight_tables.py --apply  # repeat backup, verify and activate
```

The converter accepts the previous complete 19-table schema. It refuses unknown
source tables or unresolved organization references, saves a lossless source
snapshot plus its DDL, and constructs a separate eight-table SQLite staging copy.
It verifies every feature row, including bytes and Burmese text, survives a
round trip; it also checks foreign keys. With `--apply`, it copies those eight
tables to staged MySQL tables, verifies them, rechecks the source has not changed,
then switches names with one atomic MySQL `RENAME TABLE`. Only after another
lossless verification does it drop the old tables. Private SQL and JSON backups
remain under `backups/`. A failure after switching leaves the previous tables
available for recovery instead of deleting them.

The resulting database deliberately has no `alembic_version` table. Historical
Alembic revisions describe the previous storage design and must not be applied
to the eight-table database. For a fresh workspace, import `dedc.sql`, configure
`DATABASE_URL` and `PRIVATE_STORAGE_DIR`, then create an administrator with
`uv run python -m app.portal_auth`. Empty supplied schemas work without conversion;
populated external eight-table databases without feature metadata are explicitly
rejected, because ownership and version history cannot safely be inferred.

To recover the previous application version, stop writes, restore the saved
`source-schema.sql` and `source.json.gz` into a separate database using their
preserved SQL types, compare the verification manifest, and point the previous
application checkout at that database. Keep the private directory intact when
restoring an eight-table backup. Never run an empty schema dump over live data.

## Validation

```bash
uv run python -m unittest discover -s tests -v
```

Portal/API tests use isolated eight-table databases and reopen the real storage
adapter between HTTP requests. Storage tests cover both audiences, native
question/answer placement, attachments, reporting, session revocation, rollback,
foreign keys and corrupt-file detection. Historical migration tests continue to
test the older Alembic chain separately; their temporary 19-table schemas are not
the application's persistent schema.
