# DEDC Survey Administration

A database-driven survey application built with FastAPI, SQLAlchemy, Jinja2 and plain JavaScript. The administrator workspace uses the ministry logo at `static/img/logo.png`, a restrained navy/gold palette, responsive layouts and light/dark themes.

## Run locally

Requires Python 3.12+, uv and the configured MySQL database.

```bash
uv sync
# Configure DATABASE_URL and portal settings in your existing .env.
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Use `.env.example` for configuration names. Do not overwrite existing credentials or commit secrets. If no administrator exists, create one interactively with `uv run python -m app.portal_auth`.

- Administrator login: `http://localhost:8000/portal`
- Dashboard: `http://localhost:8000/dashboard`
- Respondent login/surveys: `http://localhost:8000/survey`
- API documentation: `http://localhost:8000/docs`

## Form workflow

Create a form or import an Excel workbook in **Data management**. Edit sections/questions/options/conditions, save the draft, preview it, then explicitly publish. Published definitions are immutable; subsequent changes require a new draft version. Archive forms to stop new responses while preserving history.

Respondents enter the **From/To reporting dates first**, then complete the dynamic sections. Preview uses the same renderer and supports width/language controls. Normal respondent accounts cannot access administrator APIs.

## Excel formats

The supplied DEDC workbook contains four periods with 25 original question rows each. Every row has presence, quantity and details components. Imported source answers are preserved separately from new submissions and are never used as defaults.

**Data management → Original format** exports the full reference workbook as questions only or questions+original answers. The latter is byte-identical to the archived source. Questions-only exports clear answer cells while retaining worksheet names, original wording, merges, fonts, borders, alignment, row heights and column widths.

**Form builder → Export Excel** exports the selected version. Submitted answers use the same six columns and include the selected reporting period in the heading. Each response gets its own sheet. New/edited structures reuse the reference styles while reflecting the current sections and question order.

Reports also have separate filtered CSV, XLSX and PDF exports with metadata. PDFs embed the bundled Myanmar font and use HarfBuzz shaping.

An explicit, idempotent CLI import is available:

```bash
uv run python scripts/import_reference_workbook.py "/path/to/workbook.xlsx" --actor-id 1
# After reviewing the printed sheets/counts, add --confirm to save drafts.
```

## Organization

- `app/models/`: existing database mappings and normalized versioned form entities.
- `app/services/`: form transactions, logic/validation, workbook import/export, reports and attachments.
- `app/routers/`: preserved legacy APIs, protected admin APIs, public published schemas and authenticated submissions.
- `templates/admin/`, `templates/survey/`: administrator shell and respondent experience.
- `static/js/admin/`: shared API/UI, editor, conditions, renderer, reports and import screens.
- `static/css/admin/`: scoped design tokens and responsive components.
- `migrations/`: frozen, create-only baseline/additive migrations. Destructive downgrade is deliberately disabled.
- `tests/`: standard-library unittest integration, API, migration and exact-workbook checks.
- `context/`: specification, design system, audits and implementation progress.

## Verification

```bash
uv run python -m unittest discover -s tests -v
uv run --with playwright playwright install firefox
DEDC_FULL_WORKSPACE=1 uv run --with playwright python scripts/check_admin_session_browser.py
```

Browser tests start their own server and disposable SQLite database. Exact reference-workbook tests require the original local file; they are skipped when unavailable. Never point test fixtures at production data.

See [implementation progress](context/IMPLEMENTATION_PLAN.md), [implementation report](context/IMPLEMENTATION_REPORT.md), [workbook audit](context/WORKBOOK_AUDIT.md), [design resources](context/DESIGN_RESOURCES.md), and [collaboration guidance](docs/admin-portal.md). Advanced response save/resume, report table controls and geographic analytics remain pending; do not treat this checkpoint as completion of every product requirement.
