"""Run real-browser authentication checks against a temporary SQLite database.

Usage: uv run --with playwright python scripts/check_admin_session_browser.py
Install the matching browser first with: uv run --with playwright playwright install firefox
Set DEDC_TEST_FIREFOX to an existing Playwright Firefox executable if needed.
"""

import os
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    from playwright.sync_api import sync_playwright
    import uvicorn

    with tempfile.TemporaryDirectory(prefix="dedc-browser-") as directory:
        # Must be set before importing the application; never touch the user's DB.
        os.environ["DATABASE_URL"] = f"sqlite:///{directory}/test.db"
        os.environ["PORTAL_COOKIE_SECURE"] = "false"
        os.environ["ADMIN_ROLE_NAME"] = "Admin"
        from app.database import Base, engine, SessionLocal
        from app.main import app
        from app.models.user import User, UserRole
        from app.models.admin_session import AdminSession
        from app.portal_auth import hash_password

        Base.metadata.create_all(engine)
        with SessionLocal() as db:
            role = UserRole(name="Admin")
            db.add(UserRole(name="University"))
            db.add(role)
            db.flush()
            db.add(User(username="browser-admin", password_hash=hash_password("browser-test-password"), role_id=role.id))
            db.commit()

        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        deadline = time.monotonic() + 10
        while not server.started:
            if not thread.is_alive() or time.monotonic() > deadline:
                raise RuntimeError("Test server failed to start")
            time.sleep(.05)
        base = f"http://127.0.0.1:{port}"
        try:
            with sync_playwright() as playwright:
                options = {"headless": True}
                if os.environ.get("DEDC_TEST_FIREFOX"):
                    options["executable_path"] = os.environ["DEDC_TEST_FIREFOX"]
                browser = playwright.firefox.launch(**options)
                context = browser.new_context(viewport={"width": 1440, "height": 900})
                # External branding/font requests are irrelevant to auth tests.
                context.route("**/*", lambda route: route.continue_() if route.request.url.startswith(base) else route.abort())
                errors = []
                page = context.new_page()
                page.on("pageerror", lambda error: errors.append(str(error)))

                def login():
                    page.goto(base + "/portal")
                    page.get_by_label("Username", exact=True).fill("browser-admin")
                    page.get_by_label("Password", exact=True).fill("browser-test-password")
                    page.get_by_role("button", name="Sign in to workspace").click()
                    page.wait_for_url(base + "/dashboard")
                    page.get_by_role("heading", name="Overview", exact=True).wait_for(state="visible")

                # Direct nested entry and refresh must redirect before displaying content.
                page.goto(base + "/dashboard/forms")
                page.wait_for_url(base + "/portal")
                page.reload()
                assert page.get_by_role("heading", name="Welcome back.").is_visible()
                login()
                if os.environ.get('DEDC_FULL_WORKSPACE'):
                    from workspace_browser_checks import check
                    check(page, context, base)
                    page.goto(base + '/dashboard')
                    page.get_by_role('heading', name='Overview', exact=True).wait_for(state='visible')
                saved_cookies = context.cookies()
                assert any(c["httpOnly"] and c["sameSite"] == "Strict" for c in saved_cookies if c["name"] == "dedc_portal_session")
                second = context.new_page()
                second.on("pageerror", lambda error: errors.append(str(error)))
                second.goto(base + "/dashboard")
                second.get_by_role("heading", name="Overview", exact=True).wait_for(state="visible")
                page.bring_to_front()
                page.route("**/portal/logout", lambda route: route.abort())
                page.get_by_role("button", name="Sign out", exact=True).click()
                page.locator('[data-session-error]').wait_for(state="visible")
                assert page.locator('[data-session-error]').evaluate('(element) => element === document.activeElement')
                assert page.get_by_role("button", name="Sign out", exact=True).is_enabled()
                assert page.url == base + "/dashboard"
                assert second.url == base + "/dashboard"
                page.unroute("**/portal/logout")
                print("PASS: failed logout retains session, restores button, and focuses an accessible error")
                page.get_by_role("button", name="Sign out", exact=True).click()
                page.wait_for_url(base + "/portal")
                second.wait_for_url(base + "/portal")
                page.go_back()
                page.wait_for_url(base + "/portal")
                assert page.locator('[data-admin-workspace]:visible').count() == 0
                context.add_cookies(saved_cookies)
                for path in ("/dashboard", "/dashboard/forms"):
                    page.goto(base + path)
                    page.wait_for_url(base + "/portal")
                    page.reload()
                    assert page.locator('[data-admin-workspace]:visible').count() == 0
                print("PASS: login, HttpOnly cookie, logout, cross-tab logout, back navigation, copied cookie, nested URL, refresh")

                login()
                with SessionLocal() as db:
                    db.query(AdminSession).update({AdminSession.expires_at: int(time.time()) - 1})
                    db.commit()
                page.reload()
                page.wait_for_url(base + "/portal")
                print("PASS: expired session cannot refresh a protected page")
                assert not errors, errors
                browser.close()
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            engine.dispose()


if __name__ == "__main__":
    main()
