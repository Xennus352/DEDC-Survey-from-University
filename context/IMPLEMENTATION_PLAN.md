# Implementation Plan

Primary specification: `context/AdminSketch.md`. Read completely before implementation. Updated 2026-11-02 after the working full-stack/form-export checkpoint.

## User decisions and invariants

- Preserve FastAPI, SQLAlchemy, Jinja2, plain JavaScript/CSS and existing mobile endpoint paths/payloads.
- Use `/static/img/logo.png`; match its navy/gold with neutral, minimal surfaces. Animate real state changes, honor reduced motion, support light/dark themes.
- The supplied workbook contains both original questions and historical answers. Preserve wording, order and source cells; do not turn filled answers into defaults or pretend they are new submissions.
- Respondents must enter **From/To reporting dates first**, then navigate sections. Store the period with each submission.
- Provide Excel exports for questions alone and questions plus answers in the **original six-column workbook format**. Archive the original workbook so exports do not depend on Downloads remaining accessible.
- Imported forms remain drafts. Published definitions are immutable. Migrations must not drop tables or delete historical records.

## Phase 1 — Audit: completed

- Inspected backend, frontend, auth, models, APIs and all four Excel worksheets.
- Recorded architecture and actual MySQL schema in `ARCHITECTURE_AUDIT.md` and `database-schema-audit.json`.
- Recorded all original labels/cell references in `workbook-structure.json`; see `WORKBOOK_AUDIT.md`.
- Found empty model/CRUD exports, missing `String` import, no Alembic setup, and a mismatch between generic Python survey models and existing university/ministry tables. These backend registration defects are fixed; existing actual tables are mapped explicitly.

## Phase 2 — Design resources: completed setup, applied to working UI

- Reviewed all ten requested sources. Installed 12 compatible skills from six sources; recorded revisions/licenses and incompatibilities in `DESIGN_RESOURCES.md`.
- Applied task-first density, consistent tokens, semantic markup, visible focus, stateful feedback, responsive layouts and restrained motion in real pages.
- Created `DESIGN_SYSTEM.md`; uses local ministry logo and bundled Myanmar font. Native CSS/Web Animations are sufficient for the implemented interactions; no unnecessary GSAP runtime was introduced.
- Third-party Chrome/Puppeteer design-lint suites have not been run; do not claim their certification.

## Phase 3 — Authentication: completed and regression-tested

- Namespace-level protection for known/future `/dashboard/*` and `/api/admin/*` routes; active-account/role verification on each request.
- HttpOnly cookies, CSRF checks, session rotation/revocation and no-store headers; cross-tab logout and history/tab revalidation.
- Accessible failed-logout recovery; credential-free logout signals.
- Normal respondent login at `/survey/login`; non-admin users can complete surveys but cannot use administrator APIs.
- Public landing dialog now opens real login flows instead of a disconnected demo.
- Authentication actions are audited without passwords/tokens. No authenticated WebSocket feature exists; admin socket upgrades remain denied.

## Phase 4 — Database/backend: implemented core

- [x] Frozen create-only baseline and additive Alembic revisions `0001`–`0004`.
- [x] Actual university/ministry/year/category/question/answer ORM mappings; preserved existing identifiers and records.
- [x] Versioned forms, sections, fields/options, submissions/answers, source observations, audit logs, attachment ownership, archived Excel templates and reporting-period columns.
- [x] Transactional draft edits with revision conflict detection; duplicate/version/archive/delete rules; immutable published versions.
- [x] Database-driven field schema for all 19 requested kinds; required/bounds/length/custom regex validation, choices, conditions, safe calculations, repeating groups and real uploads.
- [x] Conditional AND/OR tree validation, supported comparison operators and circular-reference rejection; backend discards hidden answers.
- [x] File/image ownership, field/version binding, 5 MB file cap, image checks, safe authenticated downloads; 11 MB request-body bound before multipart parsing.
- [x] Legacy survey/question/response payload round-trip regression tests.
- [x] All four migrations tested on disposable SQLite/MySQL, then applied locally. Existing table row counts were checked before and after schema upgrades.

## Phase 5 — Dashboard: implemented core

- [x] Reusable responsive shell, collapsible navigation, breadcrumbs, global form/question/user search, activity link, profile/logout.
- [x] Working overview, forms, question bank, submissions, reports, users/roles, data import/source answers, settings/theme and audit screens.
- [x] Real database counts/trends, loading/empty/error states, dialogs, toasts and pending/duplicate-submit feedback.
- [x] Local logo throughout admin/respondent/login/public branding; navy `#232550`, gold `#b58a35`, restrained surfaces and light/dark themes.
- [x] Browser checks on ten admin routes at 390/768/1024/1440px; no page-level horizontal overflow.

## Phase 6 — Form builder/import/preview: implemented core

- [x] Section/question CRUD, enable/disable, duplication, options, keyboard ordering and drag/drop.
- [x] Burmese/English labels, descriptions/help, placeholders, required/defaults, numeric/text limits and custom text patterns.
- [x] Visual simple AND/OR condition editor, plus advanced nested-rule configuration.
- [x] Safe sum/difference/product/average calculations; scalar repeating-group children; real file/image uploads and GPS fields.
- [x] Excel upload → four-sheet detection → editable preview → explicit confirmation → draft save. Source answers remain immutable observations.
- [x] Source question links connect imported definitions to `uniquestion` and `questiontitle` instead of a disconnected replacement.
- [x] Preview/public survey use the same renderer. Reporting period is first, followed by section navigation that preserves entered answers.
- [x] Exact-format questions-only and questions+answers exports. Original full answers export is byte-identical; questions-only is checked cell/style/layout-wise. Edited/new forms expand/reorder using original row styles; new response workbooks use the same answer columns and period heading.
- [x] Desktop/tablet/mobile width controls and language fallback; actual narrow-viewport rendering also tested.
- [ ] Improve advanced calculation/repeating-field editors from JSON configuration to dedicated visual controls.
- [ ] Add a one-click Other/specify convenience control (currently achievable with an Other option and conditional text field).
- [ ] Harden default-value validation/prefill parity for every composite type, and verify iframe/container-based preview fidelity for all viewport-specific rules.

## Phase 7 — Reporting/user management: functional core, advanced work pending

- [x] Server pagination/search; combinable form/version/status/user/date and single answer-predicate filters.
- [x] Real counts, completion/elapsed-time summary, filtered trends/respondent activity and selected-answer distributions.
- [x] Submission details grouped by original version sections; row selection and transactional bulk review.
- [x] Filter-consistent CSV/XLSX/PDF report exports with metadata; Myanmar shaping/font embedding; spreadsheet-formula protection.
- [x] Source-answer table/filter/CSV/XLSX/PDF exports, plus separate exact original-workbook exports.
- [x] User create/edit/activation/role assignment, self-demotion protection, role creation, submission-history links and safe user-directory exports.
- [x] Audit events for auth, form/question/version/publication/archive, imports/uploads, user/role changes, reviews and exports.
- [ ] In-progress response persistence/resume and corresponding workflow/metrics.
- [ ] Multi-question predicate builder, date presets, weekly/monthly aggregation and explicit form-status filtering.
- [ ] Configurable column visibility/resizing and interactive server-side sorting, persistent selection/filter chips.
- [ ] Hierarchical location dimensions/filters and geographic charts when backed by actual geographic data. The reference workbook has no livestock data; do not invent livestock charts.
- [ ] More detailed enumerator performance and organization assignment/history.

## Phase 8 — Verification: checkpoint passed, extended QA pending

- Latest full backend run: **45 tests passed**. Includes migrations, API authorization/CSRF, legacy contracts, version immutability, calculations, repeated rows, file ownership, actual workbook parsing, period validation and exact Excel formatting.
- Firefox: section create/drag/drop/keyboard reorder/delete; save/preview/publish/submit/report/export; actual workbook upload; date-first navigation with retained answers; byte-identical original export; normal respondent restrictions; calculations/repeating rows/files/images; all responsive routes/dark mode; logout/Back/copied cookie/expiry/failure recovery passed.
- JavaScript syntax, Python compilation and Git whitespace checks passed. Temporary Ruff/Prettier tooling formatted new source without adding a frontend build dependency.
- MySQL-specific checks passed: baseline/extension migrations, real numeric answer filter, all four worksheet imports, binary attachments, draft-edit foreign-key preservation and Burmese PDF generation.
- [ ] CI browser fixtures independent of the owner's Downloads path, large-data/load tests, concurrent edit/publish/import stress, accessibility automation, PDF visual regression and full client-device matrix.
- [ ] Validate a real Flutter application end-to-end when its source/API contract is provided. Existing legacy payload tests pass; no Flutter client exists here.

## Local data checkpoint

- Four imported drafts, 16 sections, 100 original question rows represented by 300 presence/quantity/details fields, 100 preserved source-answer rows.
- Original periods: 2010-01-01→2015-12-31; 2016-01-01→2020-12-31; 2021-01-01→2025-03-31; 2021-01-01→2026-03-31.
- No form was automatically published and no fake submissions were seeded. Imported historical answers are separate from newly submitted responses.
- Original workbook is archived once by digest. Reimport is idempotent by digest + worksheet. Existing source rows were not overwritten.

## Next continuation

The core full-stack implementation and the user's logo/date-first/exact-Excel requests are working. **The entire AdminSketch acceptance list is not yet complete.** Continue with the unchecked Phase 6–8 items above, particularly response save/resume and advanced reporting. Re-read this plan and the primary specification first. Do not replace working code or reimport duplicate source data.
