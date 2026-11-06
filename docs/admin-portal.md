# Admin portal

The portal has its own router, templates and page stylesheet, and reuses the public
site's CSS tokens and reset. The public landing page keeps its existing layout; its login dialog now opens the real respondent or administrator sign-in flow.
Visit `/portal` directly to use administrator login.

## Setup

1. Add `ADMIN_ROLE_NAME` and `PORTAL_COOKIE_SECURE` from `.env.example` to your local
   `.env`. Set `DATABASE_URL` to the existing DEDC Docker MySQL database.
   For the local `dedc` container exposing port 3307, use
   `mysql+pymysql://dedc:dedc@127.0.0.1:3307/dedc`.
   When the app runs in Docker on the same network, use the database service's
   hostname and internal port 3306 instead of `127.0.0.1:3307`.
2. Confirm the `dedc` container is running with `docker ps`.
   Run `uv run python -m app.portal_auth`. Enter an administrator username, then
   enter and confirm a password with at least 8 characters. This creates an
   active account in DEDC's existing `user` table and creates the `Admin` role in
   `userrole` if necessary. Existing accounts are never overwritten.
3. Start the app with `uv run uvicorn app.main:app --reload` and visit
   `http://localhost:8000/portal`.

No default password is provided. Login checks the existing `user` and `userrole`
tables, requires `isActive`, and requires a role matching `ADMIN_ROLE_NAME`
(default `Admin`). Accounts created by the setup command use the supported
`pbkdf2_sha256$600000$salt$hash` password format. Unsupported password formats fail
authentication. Role changes and deactivation also revoke access on the next
portal request. Sessions are stored in private files referenced by metadata in existing SQL text columns. Startup creates no extra SQL tables or columns. The supplied ten-table database works directly without conversion; see [the table guide](database-tables.md).

| Method | Route | Behavior |
| --- | --- | --- |
| GET | `/portal` | Login page; signed-in admins redirect to `/dashboard` |
| GET | `/portal/login` | Login page; signed-in admins redirect to `/dashboard` |
| POST | `/portal/login` | Validate credentials, rotate the session, redirect to `/dashboard`; signed-in admins redirect without logging in again |
| GET | `/dashboard` | Admin workspace; signed-out or unauthorized visitors redirect to `/portal` |
| POST | `/portal/logout` | Validate CSRF, delete the session, clear the cookie, redirect to `/portal` |

Passwords use salted PBKDF2-SHA256 with 600,000 iterations. Session cookies contain
random tokens; only hashes are stored in private session records. Anonymous forms expire
after 15 minutes, and authenticated sessions after eight hours. Login and logout
require a session-bound CSRF token. Portal pages use `Cache-Control: no-store`.
The cookie uses path `/` so the session is available to both `/portal` and
`/dashboard`.
Server-side deletion invalidates a logged-out token, including copied cookies.

Use HTTPS and set `PORTAL_COOKIE_SECURE=true` in production. Apply login rate
limiting at your reverse proxy before exposing the portal publicly. The current
form and administration APIs enforce their existing session and CSRF requirements. The original `/surveys`, `/questions`, and `/responses` API was
retired in migration `0005`; see [the table guide](database-tables.md).

Run the portal checks with `.venv/bin/python -m unittest discover -s tests -v`.

## Department directory and appearance

The Department directory combines universities and ministries in one searchable
list. **Add department** opens a single dialog: **Type** first, then **Name**.
Both fields are visible immediately. Choosing a type updates the name label;
university category is optional under **University details**. Editing keeps the
organization type fixed. Duplicate-name errors stay inside the same dialog.

Admin colors come from the homepage palette in `static/css/base/tokens.css`
(`--home-*`). The home page and workspace share the same primary blue,
`#1556a6`. Dashboard routes use `static/css/admin/dashboard.css`: white navigation,
a neutral working canvas, compact controls, and task-specific layouts. Login and
respondent pages keep `workspace.css`. Report and workbook export options are
grouped in menus; advanced report filters and audit details remain expandable.

Run the isolated redesign review with
`uv run --with playwright python scripts/check_dashboard_redesign.py`.
It creates temporary ten-table data, checks every dashboard view at 1440, 1024,
768 and 390 pixels, exercises the administration and workbook workflows, and saves
screenshots under `/tmp/dedc-redesign-review/after`. Use `--interactions` to check
only workflows, or `--before` to capture a visual baseline. The configured MySQL
database is never used. The workbook portion uses the existing local reference
file when available.

## Reusing questions

In the form builder, choose **Add question** and type a title. Suggestions below
it search saved library questions and questions already used in forms, including
Burmese titles. Choosing a suggestion copies its answer type, choices and
validation settings. The form gets its own question key.

**Save question** saves the definition to the reusable library and adds it to the
local draft. **Save changes** persists the form itself. Typing or cancelling a
question does not create a library entry. Equivalent titles and definitions reuse
one entry; different answer settings remain separate and never overwrite an
existing template. Existing form visibility rules are kept when editing; rules
that reference other questions are not copied between forms.

The authenticated `/api/admin/question-library` GET and POST endpoints use the
same session and CSRF protections as the other admin APIs. Library definitions,
including answer choices, persist through the existing SQL feature
metadata; no extra persistent SQL table or schema migration is needed.

Run the isolated browser checks with
`DEDC_EDITOR_FIXES=1 uv run --with playwright python scripts/check_admin_session_browser.py`.

## Working with a landing-page contributor

Commit order alone does not cause conflicts. Conflicts generally happen when Git
cannot combine overlapping changes to the same lines, or a file is deleted on
one branch and edited on another.

Use separate feature branches from your shared integration branch (`main` below;
substitute your team's branch name):

```bash
git switch main
git pull --ff-only origin main
git switch -c feature/admin-portal
# Make and commit the portal changes.
git add app/config.py app/database.py app/main.py app/portal_auth.py app/models/admin_session.py app/models/user.py app/crud/admin_session.py app/crud/user.py app/routers/web/portal.py templates/portal static/css/admin/dashboard.css static/js/portal.js tests/test_portal.py docs/admin-portal.md .env.example .gitignore pyproject.toml uv.lock requirements.txt README.md
git commit -m "Add administrator portal login and logout"
git push -u origin feature/admin-portal
```

Your partner should use a separate branch such as `feature/landing-page`. Open
pull requests into the shared branch. Agree that your work owns `templates/portal/`,
`static/css/admin/dashboard.css`, and `app/routers/web/portal.py`, while your partner
owns `templates/index.html` and the home-page styles. Coordinate changes to shared
files such as `app/main.py`, `app/config.py`, and CSS tokens.

After your partner's work is merged, commit your pending changes and bring the
shared branch into your feature branch:

```bash
git fetch origin
git switch feature/admin-portal
git merge origin/main
```

If conflicts occur, run `git status`, open each conflicted file, and combine both
intended changes. Remove the `<<<<<<<`, `=======`, and `>>>>>>>` markers. Do not
choose an entire side blindly. For example, keep both router registrations when
both contributors add a router to `app/main.py`. Then:

```bash
git add path/to/resolved-file
git commit
.venv/bin/python -m unittest discover -s tests -v
git push
```

Check `/`, `/portal`, and `/dashboard` before merging the pull request. You can use
`git merge --abort` to abandon an unresolved merge and return to your pre-merge
state. Avoid force-pushing the shared integration branch.

The repository already tracks `.env`. Adding it to `.gitignore` does not untrack
it. Agree with your partner to remove it from tracking once, while keeping your
local copy:

```bash
git rm --cached .env
git commit -m "Stop tracking local environment configuration"
```

Use `.env.example` for shared variable names. If real credentials have ever been
committed to `.env`, rotate them; removing the file does not remove Git history.

## Current administration workspace

The dynamic builder, versioned forms, reporting-period-first respondent experience, original-format workbook exports and reporting/user/audit pages are documented in [the implementation report](../context/IMPLEMENTATION_REPORT.md). The application detects the supplied ten-table schema and the previous eight-table layout automatically; see [the table guide](database-tables.md). Back up the SQL database and private files together. Do not apply historical Alembic migrations to these databases.
