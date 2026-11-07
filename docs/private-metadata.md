# Keep questiontitle for real categories

The SQL metadata mode uses application-generated `questiontitle` rows for native
question mappings and compressed form state. The verified live dry run identified
25 mappings and one state fragment at IDs -26 through -1, plus four genuine
categories. The fragment points to session/audit/upload/workbook files; deleting
it without transferring those references would lose application state.

The explicit private mode moves mappings and feature state to immutable,
SHA-256-verified documents in `PRIVATE_STORAGE_DIR`. `metadata-current.json`
identifies the current document. SQL still contains the original ten tables;
questions, answers, categories, years, users, roles and organizations remain in
their existing business tables. No extra database or SQL column is created.
Genuine category descriptions and IDs, including genuine negative IDs, are kept.
The eight-table compatibility layout is unchanged.

## Dry run and cutover

```bash
uv run python scripts/migrate_private_metadata.py
```

This obtains the normal workspace locks, opens a read-only MySQL transaction,
backs up all ten tables plus their actual DDL and the entire private directory,
checks backup hashes, and runs migration/reopen/rollback checks on an explicitly
named SQLite staging copy. It prints exact candidate IDs and counts, never
credentials, password hashes, tokens or encoded feature payloads. The staging
copy is a test artifact, not runtime storage. Backups are under ignored
`backups/metadata-cleanup-<timestamp>-<id>/`; protect them as private data.

Important backup files:

- `database.sql`: full MySQL schema/data, including original table options/indexes.
- `database.json.gz`: lossless, typed data snapshot verified in staging.
- `private/`: untouched original private-file backup.
- `plan.json`: exact category rows, destination document and SQL precondition.
- `manifest.json`: checksums for the backups, plan, original private files and verification report.
- `verification.json`: isolated migration/rollback results and logical row counts.
- `staging.db` and `staging-private/`: explicit rehearsal copies.

After reviewing the dry run and obtaining approval, stop **all** app workers and
external writers. Keep the upgraded code available on every worker. Apply using
the verified backup directory:

```bash
uv run python scripts/migrate_private_metadata.py --apply --backup backups/metadata-cleanup-<timestamp>-<id>
```

Apply refuses if SQL or original private files changed since the backup, if a
candidate is referenced as a real category, if unknown columns/tables or category
triggers are present, or if backup integrity fails. Repeat the dry run with writes
stopped if its preconditions became stale. Only specifically verified IDs are
deleted. The operation is idempotent.

Set `METADATA_STORAGE=private` in local configuration and restart all workers.
Do not change `DATABASE_URL` or `PRIVATE_STORAGE_DIR` during the cutover. The new
SQL mode refuses to write if a private marker is active. Private mode refuses to
start with missing/corrupt documents, the wrong database identity, or reappearing
SQL metadata. Never run pre-cutover app code against the cleaned database.
The default remains `METADATA_STORAGE=sql` until an explicit approved cutover;
merely installing this code does not migrate the live database.

## Commit and recovery protocol

Every application worker must use the same private directory, SQL endpoint and
workspace locks. MySQL advisory locks plus local file locks serialize units of
work. Private documents and uploaded bytes are immutable, flushed and hash-checked.
The shared volume must honor atomic rename, fsync and process locks; separate
local copies of the private directory are unsupported.

Before committing native SQL changes, the app durably writes a checksummed
`metadata-pending.json` intent containing before/after SQL fingerprints, the prior
pointer and the proposed new pointer. After SQL commits, it atomically publishes
the matching pointer, fsyncs the directory, then removes the intent. Readers use
the same locks and resolve an unfinished intent before loading state:

- SQL matches the recorded after-state: publish the new pointer.
- SQL matches only the before-state: discard the intent and retain the prior pointer.
- SQL matches neither: fail closed for manual recovery instead of guessing.

For a metadata-only change, before/after SQL are identical; a durable intent is
the recovery commit point. A crash can therefore commit an operation whose client
never received success. After an exception, close/reopen the unit of work and
check its resulting state before retrying. The failed unit cannot commit again.
This is recoverable coordination, not a distributed atomic transaction guaranteed
by MySQL alone. External writers that bypass the locks are unsupported; changes
around an interrupted commit may require reconciliation. Whole-workspace
fingerprints also make this suitable for the current small survey workspace,
not a high-throughput database.

## Rollback and restore

Before accepting new application writes after cutover:

```bash
uv run python scripts/migrate_private_metadata.py --rollback --backup backups/metadata-cleanup-<timestamp>-<id>
```

Rollback verifies the current SQL fingerprint and private document match the
migrated backup state, restores only the exact removed category rows, and removes
the active private pointer using the same journal protocol. It is idempotent and
refuses to discard work performed after migration. Then set
`METADATA_STORAGE=sql` and restart all workers with compatible code.

If subsequent work exists, do not force rollback. Stop writers and use a separately
reviewed restore/reconciliation procedure. For full pre-cutover recovery, restore
`database.sql` into an empty database and the paired `private/` copy, validate the
backup manifest and logical counts, and use SQL metadata mode. Never import the
schema dump over a populated database.

Future private-mode backups must capture SQL, the entire private directory and
storage-mode configuration at one stopped/locked point. A SQL-only restore is
incomplete. Restore to the same database identity; a changed endpoint/database
requires an explicitly verified rebinding procedure rather than bypassing the
identity check. Retain the original backups and immutable blobs; no garbage
collection or removal of unrelated negative IDs is performed.

## Verification

```bash
uv run python -m unittest discover -s tests -v
uv run --with playwright python scripts/check_dashboard_redesign.py --private-metadata
```

The suite covers both storage modes, all portal/API contracts, both survey
audiences, versioned forms, options, reports, file/session persistence, original
workbook bytes, category preservation, cross-process locking, corrupt/missing
files, SQL commit/rollback recovery, metadata-only uncertain commits, exact-ID
migration and guarded/idempotent rollback. Browser writes are checked to ensure
no synthetic `questiontitle` row returns.
