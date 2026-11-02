# Repository Guidelines

## Project Structure & Module Organization

This Python 3.12+ application uses FastAPI, SQLAlchemy, and Jinja2. `app/main.py` registers routers and mounts static assets. Put database models in `app/models/`, validation schemas in `app/schemas/`, reusable database operations in `app/crud/`, and API endpoints in `app/routers/`. HTML routes belong in `app/routers/web/`.

Templates live in `templates/`; CSS and JavaScript live in `static/`. Portal functionality has dedicated templates, styles, and scripts. Keep tests in `tests/` and setup documentation in `docs/`. See `docs/admin-portal.md` for administrator setup and collaboration guidance.

## Build, Test, and Development Commands

Run commands from the repository root:

- `uv sync`: install dependencies from `pyproject.toml` and `uv.lock`.
- `uv run uvicorn app.main:app --reload`: start the development server at `http://localhost:8000`.
- `uv run python -m unittest discover -s tests -v`: run the test suite.
- `uv run python -m app.portal_auth`: interactively create an administrator account against the configured database.

The project runs directly from `app/`; there is no separate package build or frontend build step.

## Coding Style & Naming Conventions

Use four-space indentation for Python, `snake_case` for functions and modules, and `PascalCase` for classes. Follow nearby code when editing HTML, CSS, and JavaScript. Keep routers focused on request handling and place shared database logic in CRUD modules. Reuse CSS tokens in `static/css/base/tokens.css`. No formatter or linter is currently configured.

## Testing Guidelines

Tests use standard-library `unittest`, including `IsolatedAsyncioTestCase`. Name files `test_*.py` and methods `test_*`. Portal tests use an isolated SQLite database and override dependencies; do not point tests at production data. Cover changed behavior and relevant authorization failures. No numeric coverage threshold is configured. For UI changes, manually check `/`, `/portal`, and `/dashboard`.

## Commit & Pull Request Guidelines

Existing history uses short, informal subjects and has no enforced convention. Prefer descriptive imperative messages such as `Add administrator portal login`. Use feature branches and open pull requests into `main`. Include a change summary, validation results, linked issues when applicable, and screenshots for visual changes. Coordinate edits to shared configuration and templates; avoid force-pushing `main`.

## Security & Configuration

Use `.env.example` for configuration names and keep credentials local. `.env` is already tracked despite being ignored; inspect staged changes carefully to avoid publishing secrets. Configure `DATABASE_URL` before running the app. Use HTTPS and `PORTAL_COOKIE_SECURE=true` in production.
