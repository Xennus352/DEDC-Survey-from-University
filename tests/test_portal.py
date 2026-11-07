"""Portal integration checks using the ASGI interface, with no extra test packages."""

import re
import time
import unittest
import tempfile
from http.cookies import SimpleCookie
from unittest.mock import patch
from urllib.parse import urlencode, urlsplit

from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base
from app.storage import schema
from app.storage.compact import CompactSession
from app import admin_auth
from app.dependencies import get_db
from app.main import app
from app.models.admin_session import AdminSession
from app.models.user import User, UserRole
from app.portal_auth import hash_password
from app.routers.web import portal


class PortalFixture(unittest.IsolatedAsyncioTestCase):
    persistent_metadata = schema.metadata
    metadata_storage = 'sql'
    @classmethod
    def setUpClass(cls):
        cls.password = "a-test-password-123"
        cls.password_hash = hash_password(cls.password)

    async def asyncSetUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.private_folder = tempfile.TemporaryDirectory()
        self.sessions = lambda: CompactSession(self.engine, self.private_folder.name, self.metadata_storage)
        self.cookies = SimpleCookie()
        self.persistent_metadata.create_all(self.engine)
        if self.metadata_storage == 'private':
            from app.storage.codec import PrivateFiles
            from app.storage.metadata_migration import migrate
            with self.engine.connect() as c:
                migrate(c, PrivateFiles(self.private_folder.name), self.engine)
        with self.sessions() as db:
            db.add_all(
                [UserRole(id=1, name="Admin"), UserRole(id=2, name="University")]
            )
            db.flush()
            db.add_all(
                [
                    User(username="admin", password_hash=self.password_hash, role_id=1),
                    User(
                        username="inactive",
                        password_hash=self.password_hash,
                        role_id=1,
                        is_active=False,
                    ),
                    User(
                        username="member", password_hash=self.password_hash, role_id=2
                    ),
                ]
            )
            db.commit()

        def test_db():
            with self.sessions() as db:
                yield db

        app.dependency_overrides[get_db] = test_db
        self.config = patch.multiple(
            settings,
            ADMIN_ROLE_NAME="Admin",
            PORTAL_COOKIE_SECURE=False,
        )
        self.config.start()
        self.engine_patch = patch.object(portal, "engine", self.engine)
        self.engine_patch.start()
        self.auth_db_patch = patch.object(admin_auth, "SessionLocal", self.sessions)
        self.auth_db_patch.start()
        self.lifespan = app.router.lifespan_context(app)
        await self.lifespan.__aenter__()

    async def asyncTearDown(self):
        await self.lifespan.__aexit__(None, None, None)
        app.dependency_overrides.clear()
        self.config.stop()
        self.engine_patch.stop()
        self.auth_db_patch.stop()
        self.engine.dispose()
        self.private_folder.cleanup()

    async def request(
        self,
        path="/portal",
        method="GET",
        form=None,
        extra_headers=(),
        target_app=None,
        raw_body=None,
        content_type=None,
    ):
        parsed = urlsplit(path)
        path = parsed.path
        body = raw_body if raw_body is not None else urlencode(form or {}).encode()
        headers = [(b"host", b"testserver")]
        headers.extend(extra_headers)
        if self.cookies:
            cookie = "; ".join(
                f"{key}={value.value}" for key, value in self.cookies.items()
            )
            headers.append((b"cookie", cookie.encode()))
        if content_type or method == "POST":
            headers.append(
                (
                    b"content-type",
                    (content_type or "application/x-www-form-urlencoded").encode(),
                )
            )
        messages = []

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            messages.append(message)

        await (target_app or app)(
            {
                "type": "http",
                "asgi": {"version": "3.0", "spec_version": "2.4"},
                "http_version": "1.1",
                "method": method,
                "scheme": "http",
                "path": path,
                "raw_path": path.encode(),
                "query_string": parsed.query.encode(),
                "root_path": "",
                "headers": headers,
                "client": ("127.0.0.1", 1234),
                "server": ("testserver", 80),
            },
            receive,
            send,
        )
        start = messages[0]
        for key, value in start["headers"]:
            if key == b"set-cookie":
                self.cookies.load(value.decode())
        text = b"".join(m.get("body", b"") for m in messages[1:]).decode()
        return start["status"], dict(start["headers"]), text

    async def csrf(self):
        status, _, body = await self.request()
        self.assertEqual(status, 200)
        return re.search(r'name="csrf_token" value="([^"]+)"', body).group(1)

    async def login(self, **overrides):
        fields = {
            "csrf_token": await self.csrf(),
            "username": "admin",
            "password": self.password,
        }
        fields.update(overrides)
        return await self.request("/portal/login", "POST", fields)


class PortalTests(PortalFixture):
    async def test_signed_out_page_and_session_cookie(self):
        status, headers, body = await self.request()
        self.assertEqual(status, 200)
        self.assertIn("Welcome back", body)
        self.assertEqual(headers[b"cache-control"], b"no-store")
        cookie = headers[b"set-cookie"]
        for attribute in (b"HttpOnly", b"SameSite=strict", b"Path=/;"):
            self.assertIn(attribute, cookie)

    async def test_login_rotates_session_and_logout_revokes_it(self):
        csrf = await self.csrf()
        anonymous_token = self.cookies[portal.COOKIE_NAME].value
        status, headers, _ = await self.request(
            "/portal/login",
            "POST",
            {
                "csrf_token": csrf,
                "username": "admin",
                "password": self.password,
            },
        )
        self.assertEqual(status, 303)
        self.assertEqual(headers[b"location"], b"http://testserver/dashboard")
        authenticated_token = self.cookies[portal.COOKIE_NAME].value
        self.assertNotEqual(anonymous_token, authenticated_token)
        status, _, body = await self.request("/dashboard")
        self.assertEqual(status, 200)
        self.assertIn("Welcome, admin.", body)
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', body).group(1)
        status, _, _ = await self.request(
            "/portal/logout", "POST", {"csrf_token": csrf}
        )
        self.assertEqual(status, 303)
        status, headers, _ = await self.request("/dashboard")
        self.assertEqual(status, 303)
        self.assertEqual(headers[b"location"], b"http://testserver/portal")
        self.cookies[portal.COOKIE_NAME] = authenticated_token
        _, _, body = await self.request()
        self.assertIn("Welcome back", body)
        with self.sessions() as db:
            self.assertIsNone(
                db.get(
                    AdminSession, portal.admin_session.token_hash(authenticated_token)
                )
            )

    async def test_wrong_credentials_and_unicode_fail_cleanly(self):
        for username, password in [
            ("admin", "wrong"),
            ("other", self.password),
            ("မြန်မာ", "စကားဝှက်"),
        ]:
            status, _, body = await self.login(username=username, password=password)
            self.assertEqual(status, 401)
            self.assertIn("username or password is incorrect", body)
            self.assertNotIn('value="wrong"', body)

    async def test_authenticated_admin_cannot_reenter_login(self):
        await self.login()
        token = self.cookies[portal.COOKIE_NAME].value
        for path, method in (
            ("/portal", "GET"),
            ("/portal/login", "GET"),
            ("/portal/login", "POST"),
        ):
            status, headers, body = await self.request(path, method)
            self.assertEqual(status, 303)
            self.assertEqual(headers[b"location"], b"http://testserver/dashboard")
            self.assertEqual(headers[b"cache-control"], b"no-store")
            self.assertNotIn("Welcome back", body)
            self.assertEqual(self.cookies[portal.COOKIE_NAME].value, token)
        _, _, body = await self.request("/dashboard")
        self.assertIn("Welcome, admin.", body)

    async def test_dashboard_requires_authenticated_admin(self):
        status, headers, _ = await self.request("/dashboard")
        self.assertEqual(status, 303)
        self.assertEqual(headers[b"location"], b"http://testserver/portal")
        await self.csrf()
        status, headers, _ = await self.request("/dashboard")
        self.assertEqual(status, 303)
        self.assertEqual(headers[b"location"], b"http://testserver/portal")

    async def test_all_nested_dashboard_paths_require_authentication(self):
        paths = (
            "/dashboard",
            "/dashboard/",
            "/dashboard/forms",
            "/dashboard/forms/123/edit",
        )
        for path in paths:
            status, headers, _ = await self.request(path)
            self.assertEqual(status, 303, path)
            self.assertEqual(headers[b"location"], b"http://testserver/portal", path)
            self.assertEqual(headers[b"cache-control"], b"no-store", path)

    async def test_registered_nested_route_is_guarded_before_handler_runs(self):
        protected = FastAPI()
        protected.add_middleware(admin_auth.AdminAuthorizationMiddleware)
        calls = []

        @protected.get("/dashboard/forms")
        def nested_page():
            calls.append("read")
            return {"authorized": True}

        status, _, _ = await self.request("/dashboard/forms", target_app=protected)
        self.assertEqual(status, 303)
        self.assertEqual(calls, [])
        await self.login()
        status, _, _ = await self.request("/dashboard/forms", target_app=protected)
        self.assertEqual(status, 200)
        self.assertEqual(calls, ["read"])
        _, _, body = await self.request("/dashboard")
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', body).group(1)
        await self.request("/portal/logout", "POST", {"csrf_token": csrf})
        status, _, _ = await self.request("/dashboard/forms", target_app=protected)
        self.assertEqual(status, 303)
        self.assertEqual(calls, ["read"])

    async def test_logout_blocks_nested_routes_and_copied_session_cookie(self):
        await self.login()
        token = self.cookies[portal.COOKIE_NAME].value
        _, _, body = await self.request("/dashboard")
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', body).group(1)
        status, headers, _ = await self.request(
            "/portal/logout", "POST", {"csrf_token": csrf}
        )
        self.assertEqual(status, 303)
        self.assertIn(b"Max-Age=0", headers[b"set-cookie"])
        for copied_cookie in (False, True):
            self.cookies.clear()
            if copied_cookie:
                self.cookies[portal.COOKIE_NAME] = token
            for path in ("/dashboard", "/dashboard/forms", "/dashboard/forms/1"):
                status, _, _ = await self.request(path)
                self.assertEqual(status, 303, path)
            status, _, _ = await self.request("/api/admin/session")
            self.assertEqual(status, 401)

    async def test_admin_api_checks_expiry_role_and_account_on_every_request(self):
        status, _, _ = await self.request("/api/admin/session")
        self.assertEqual(status, 401)
        await self.login()
        status, headers, body = await self.request("/api/admin/session")
        self.assertEqual(status, 200)
        self.assertIn('"username":"admin"', body)
        self.assertEqual(headers[b"cache-control"], b"no-store")
        with self.sessions() as db:
            account = db.query(User).filter(User.username == "admin").one()
            account.role_id = 2
            db.commit()
        status, _, _ = await self.request("/api/admin/session")
        self.assertEqual(status, 403)
        with self.sessions() as db:
            account = db.query(User).filter(User.username == "admin").one()
            account.role_id = 1
            account.is_active = False
            db.commit()
        status, _, _ = await self.request("/api/admin/session")
        self.assertEqual(status, 403)
        with self.sessions() as db:
            db.query(AdminSession).update(
                {AdminSession.expires_at: int(time.time()) - 1}
            )
            db.commit()
        status, _, _ = await self.request("/api/admin/session")
        self.assertEqual(status, 401)
        status, _, _ = await self.request("/dashboard/forms")
        self.assertEqual(status, 303)

    async def test_member_session_is_forbidden_from_admin_api(self):
        with self.sessions() as db:
            member = db.query(User).filter(User.username == "member").one()
            token = portal.admin_session.create_session(db, member.id)
        self.cookies[portal.COOKIE_NAME] = token
        status, _, _ = await self.request("/api/admin/session")
        self.assertEqual(status, 403)

    async def test_admin_namespace_requires_csrf_before_mutating_route_dispatch(self):
        await self.login()
        status, _, _ = await self.request("/api/admin/future-action", "POST")
        self.assertEqual(status, 403)
        token = self.cookies[portal.COOKIE_NAME].value
        status, headers, _ = await self.request(
            "/api/admin/future-action",
            "POST",
            extra_headers=[
                (b"x-csrf-token", portal.csrf_token(token).encode()),
            ],
        )
        self.assertEqual(status, 404)
        self.assertEqual(headers[b"cache-control"], b"no-store")

    async def test_dashboard_delivers_history_and_cross_tab_session_guard(self):
        await self.login()
        status, headers, body = await self.request("/dashboard")
        self.assertEqual(status, 200)
        self.assertEqual(headers[b"cache-control"], b"no-store")
        self.assertIn("data-admin-workspace", body)
        self.assertIn("/js/admin-session.js", body)
        status, _, _ = await self.request("/dashboard/forms")
        self.assertEqual(
            status, 200
        )  # The real database-driven form list is now registered.

    async def test_signed_out_admin_can_open_login_route(self):
        status, _, body = await self.request("/portal/login")
        self.assertEqual(status, 200)
        self.assertIn("Welcome back", body)

    async def test_expired_session_can_open_login_route(self):
        await self.login()
        with self.sessions() as db:
            db.query(AdminSession).update(
                {AdminSession.expires_at: int(time.time()) - 1}
            )
            db.commit()
        status, _, body = await self.request("/portal/login")
        self.assertEqual(status, 200)
        self.assertIn("Welcome back", body)

    async def test_login_requires_csrf_and_cookie(self):
        status, _, _ = await self.login(csrf_token="forged")
        self.assertEqual(status, 403)
        self.cookies.clear()
        status, _, _ = await self.request(
            "/portal/login",
            "POST",
            {
                "username": "admin",
                "password": self.password,
            },
        )
        self.assertEqual(status, 403)

    async def test_logout_requires_post_and_csrf(self):
        await self.login()
        status, _, _ = await self.request("/portal/logout")
        self.assertEqual(status, 405)
        status, _, _ = await self.request(
            "/portal/logout", "POST", {"csrf_token": "forged"}
        )
        self.assertEqual(status, 403)
        _, _, body = await self.request("/dashboard")
        self.assertIn("Welcome, admin.", body)

    async def test_expired_session_and_forged_cookie_cannot_authenticate(self):
        await self.login()
        with self.sessions() as db:
            db.query(AdminSession).update({AdminSession.expires_at: time.time() - 1})
            db.commit()
        _, _, body = await self.request()
        self.assertIn("Welcome back", body)
        self.cookies[portal.COOKIE_NAME] = "forged-token"
        _, _, body = await self.request()
        self.assertIn("Welcome back", body)

    async def test_inactive_and_non_admin_accounts_cannot_login(self):
        for username in ("inactive", "member"):
            status, _, _ = await self.login(username=username)
            self.assertEqual(status, 401)

    async def test_disabled_account_loses_existing_portal_access(self):
        await self.login()
        with self.sessions() as db:
            db.query(User).filter(User.username == "admin").update(
                {User.is_active: False}
            )
            db.commit()
        status, headers, _ = await self.request("/dashboard")
        self.assertEqual(status, 303)
        self.assertEqual(headers[b"location"], b"http://testserver/portal")
        _, _, body = await self.request()
        self.assertIn("Welcome back", body)

    async def test_role_change_revokes_portal_access(self):
        await self.login()
        with self.sessions() as db:
            db.query(User).filter(User.username == "admin").update({User.role_id: 2})
            db.commit()
        status, headers, _ = await self.request("/dashboard")
        self.assertEqual(status, 303)
        self.assertEqual(headers[b"location"], b"http://testserver/portal")
        _, _, body = await self.request()
        self.assertIn("Welcome back", body)

    async def test_secure_cookie_when_enabled(self):
        with patch.object(settings, "PORTAL_COOKIE_SECURE", True):
            _, headers, _ = await self.request()
            self.assertIn(b"Secure", headers[b"set-cookie"])

    async def test_template_escapes_username(self):
        status, _, body = await self.login(username='<script>alert("x")</script>')
        self.assertEqual(status, 401)
        self.assertNotIn('<script>alert("x")</script>', body)
        self.assertIn("&lt;script&gt;", body)

    async def test_oversized_form_is_rejected(self):
        status, _, _ = await self.login(password="x" * 9000)
        self.assertEqual(status, 413)

    async def test_landing_page_and_shared_styles_still_available(self):
        status, _, body = await self.request("/")
        self.assertEqual(status, 200)
        self.assertIn('id="login-dialog"', body)
        self.assertIn('href="/roadmap"', body)
        self.assertIn('href="/home" aria-current="page"', body)
        self.assertIn('href="/surveys"', body)
        self.assertIn('href="/surveys/ministry"', body)
        self.assertIn('href="/surveys/university"', body)
        self.assertIn('href="/#contact"', body)
        self.assertIn('class="nav-dropdown"', body)
        self.assertIn('href="/roadmap#pillar-2"', body)
        self.assertIn('class="nav-dropdown__all"', body)
        self.assertNotIn("၂၀၃၀ ခုနှစ်", body)
        self.assertNotIn('class="nav-dropdown__year"', body)
        status, _, _ = await self.request("/static/css/admin/workspace.css")
        self.assertEqual(status, 200)

        status, _, body = await self.request("/home")
        self.assertEqual(status, 200)
        self.assertIn('href="/home" aria-current="page"', body)
        self.assertIn('id="login-dialog"', body)

    async def test_survey_selection_page_offers_both_audiences(self):
        status, _, body = await self.request("/surveys")
        self.assertEqual(status, 200)
        self.assertIn("စစ်တမ်းဖြေဆိုရန် ကဏ္ဍကို ရွေးချယ်ပါ", body)
        self.assertIn('href="/surveys/ministry"', body)
        self.assertIn('href="/surveys/university"', body)
        self.assertIn('href="/static/css/pages/surveys.css"', body)
        self.assertRegex(body, r'href="/surveys"[^>]*aria-current="page"')
        self.assertNotIn('href="/survey/login"', body)
        self.assertNotIn('id="login-dialog"', body)
        self.assertNotIn('data-login-open', body)
        for path in (
            "/static/css/pages/surveys.css",
            "/static/css/components/nav-dropdown.css",
        ):
            status, _, _ = await self.request(path)
            self.assertEqual(status, 200, path)

    async def test_roadmap_page_serves_separate_assets(self):
        status, _, body = await self.request("/roadmap")
        self.assertEqual(status, 200)
        self.assertIn("MYANMAR DIGITAL ECONOMY ROADMAP 2030", body)
        self.assertIn('href="/static/css/pages/roadmap.css"', body)
        self.assertIn('src="/static/js/roadmap.js"', body)
        self.assertIn('href="/roadmap" aria-current="page"', body)
        self.assertNotIn('href="/home" aria-current="page"', body)
        self.assertIn('href="/#contact"', body)
        for path in (
            "/static/css/pages/roadmap.css",
            "/static/js/roadmap.js",
            "/static/css/components/nav-dropdown.css",
        ):
            status, _, _ = await self.request(path)
            self.assertEqual(status, 200, path)

    async def test_legacy_roadmap_url_redirects_without_html_extension(self):
        status, headers, _ = await self.request("/RoadMap.html")
        self.assertEqual(status, 301)
        self.assertEqual(headers[b"location"], b"/roadmap")


if __name__ == "__main__":
    unittest.main()
