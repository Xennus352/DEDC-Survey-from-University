# Data usability audit

## Live database observations

The configured Docker MySQL database was inspected using a read-only session.
No live records, tables or columns were changed. It contains 110 universities,
31 ministries, one account and one role, 25 university source questions, and no
native university or ministry submission rows. All eleven declared foreign-key
relationships were checked; no orphan references were found.

The application has one imported form/version, four sections, 75 answer fields,
and 25 preserved workbook answer rows. These are separate from new submissions:
there are currently no submitted responses. The 30 `questiontitle` rows are four
categories, 25 application question mappings and one feature-metadata fragment.
They are not 30 survey questions. Metadata and private files were retained.

The existing form and native source period both run from 2010-01-01 to 2015-12-31.
A general import-code issue was found: source periods used the worksheet years
rather than exact dates from the detected form definition. Future imports now
use the definition dates. Existing periods were not rewritten.

## Implemented fixes

- The department UI previously loaded at most 50 records per organization type
  and offered no pagination. This left 60 of the live universities unreachable.
  A combined, globally sorted directory endpoint now paginates both types with
  accurate counts, type filters and search. Existing organization APIs remain.
- Answer details and report CSV/XLSX/PDF exports share readable representations:
  choice labels, Yes/No, zero, explicit empty text, missing answers, repeated-row
  labels and attachment filenames. Raw answer values remain in API responses and
  storage. Distribution labels resolve against the filtered historical versions;
  ambiguous cross-version labels are identified rather than silently guessed.
- Optional explicit empty text and empty selection/row lists survive future
  saves. Required, disabled and conditional-question checks still apply. Previously
  discarded empty values cannot be reconstructed from the current database.
- Audit lists show account names, readable actions and structured change details.
  Technical JSON remains available in an expandable detail. Reporting dates and
  timestamps handle date-only values, UTC and explicit offsets correctly.
- The overview's 30-day interval now starts at midnight, so early responses on
  the first included date are counted.

## Removed files and evidence

| Removed path | Evidence |
|---|---|
| `templates/portal/base.html` | No template extends/imports it, and no route renders it. Login is standalone; dashboard extends `admin/layout.html`. |
| `static/css/pages/portal.css` | Loaded only by that unused base template. Active login/respondent pages use `admin/workspace.css`; dashboard uses `admin/dashboard.css`. The obsolete asset-existence test and documentation references were updated. |

No additional directory was proven wholly unnecessary. Historical migrations,
conversion/recovery scripts, reference data, dependency manifests, useful tests,
configuration, skills, dumps, backups, private files and uploads were retained.
A missing text reference alone was not treated as proof that a file was obsolete.

## Verification

Run `uv run python -m unittest discover -s tests -v` and
`uv run --with playwright python scripts/check_dashboard_redesign.py`.
Tests use isolated SQLite databases for both supported storage layouts; browser
checks use a temporary ten-table database. They cover save/reopen/detail/export
agreement, directory pagination and authorization, dates, workbook periods,
attachment names, false/zero/empty/missing values and existing workflows.

Review screenshots are saved under `/tmp/dedc-data-usability/after`; the broader
responsive review uses `/tmp/dedc-redesign-review/after`. The sanitized local
MySQL count/relationship audit is `/tmp/dedc-data-usability/mysql-audit.json`.

## Limits

Unmanaged native survey rows, if added externally, remain in SQL without invented
respondent ownership or form/version history. They are not automatically included
in application submission reports. Encoded metadata is intentionally retained in
existing text columns; readable application reports do not make direct SQL dumps
human-readable. Backups must include both MySQL and the private-file directory.
