"""Portal integration checks using the ASGI interface, with no extra test packages."""

import re
import time
import unittest
from http.cookies import SimpleCookie
from unittest.mock import patch
from urllib.parse import urlencode

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.dependencies import get_db
from app.main import app
from app.models.admin_session import AdminSession
from app.models.user import User, UserRole
from app.portal_auth import hash_password
from app.routers.web import portal


class PortalTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.password = "a-test-password-123"
        cls.password_hash = hash_password(cls.password)

    async def asyncSetUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = sessionmaker(bind=self.engine)
        self.cookies = SimpleCookie()
        UserRole.__table__.create(self.engine)
        User.__table__.create(self.engine)
        with self.sessions() as db:
            db.add_all([UserRole(id=1, name="Admin"), UserRole(id=2, name="University")])
            db.flush()
            db.add_all([
                User(username="admin", password_hash=self.password_hash, role_id=1),
                User(username="inactive", password_hash=self.password_hash, role_id=1, is_active=False),
                User(username="member", password_hash=self.password_hash, role_id=2),
            ])
            db.commit()

        def test_db():
            with self.sessions() as db:
                yield db

        app.dependency_overrides[get_db] = test_db
        self.config = patch.multiple(
            settings, ADMIN_ROLE_NAME="Admin",
            PORTAL_COOKIE_SECURE=False,
        )
        self.config.start()
        self.engine_patch = patch.object(portal, "engine", self.engine)
        self.engine_patch.start()
        self.lifespan = app.router.lifespan_context(app)
        await self.lifespan.__aenter__()

    async def asyncTearDown(self):
        await self.lifespan.__aexit__(None, None, None)
        app.dependency_overrides.clear()
        self.config.stop()
        self.engine_patch.stop()
        self.engine.dispose()

    async def request(self, path="/portal", method="GET", form=None):
        body = urlencode(form or {}).encode()
        headers = [(b"host", b"testserver")]
        if self.cookies:
            cookie = "; ".join(f"{key}={value.value}" for key, value in self.cookies.items())
            headers.append((b"cookie", cookie.encode()))
        if method == "POST":
            headers.append((b"content-type", b"application/x-www-form-urlencoded"))
        messages = []

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            messages.append(message)

        await app({
            "type": "http", "asgi": {"version": "3.0", "spec_version": "2.4"}, "http_version": "1.1",
            "method": method, "scheme": "http", "path": path,
            "raw_path": path.encode(), "query_string": b"", "root_path": "",
            "headers": headers, "client": ("127.0.0.1", 1234),
            "server": ("testserver", 80),
        }, receive, send)
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
        fields = {"csrf_token": await self.csrf(), "username": "admin", "password": self.password}
        fields.update(overrides)
        return await self.request("/portal/login", "POST", fields)

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
        status, headers, _ = await self.request("/portal/login", "POST", {
            "csrf_token": csrf, "username": "admin", "password": self.password,
        })
        self.assertEqual(status, 303)
        self.assertEqual(headers[b"location"], b"http://testserver/dashboard")
        authenticated_token = self.cookies[portal.COOKIE_NAME].value
        self.assertNotEqual(anonymous_token, authenticated_token)
        status, _, body = await self.request("/dashboard")
        self.assertEqual(status, 200)
        self.assertIn("Welcome, admin.", body)
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', body).group(1)
        status, _, _ = await self.request("/portal/logout", "POST", {"csrf_token": csrf})
        self.assertEqual(status, 303)
        status, headers, _ = await self.request("/dashboard")
        self.assertEqual(status, 303)
        self.assertEqual(headers[b"location"], b"http://testserver/portal")
        self.cookies[portal.COOKIE_NAME] = authenticated_token
        _, _, body = await self.request()
        self.assertIn("Welcome back", body)
        with self.sessions() as db:
            self.assertIsNone(db.get(AdminSession, portal.admin_session.token_hash(authenticated_token)))

    async def test_wrong_credentials_and_unicode_fail_cleanly(self):
        for username, password in [("admin", "wrong"), ("other", self.password), ("မြန်မာ", "စကားဝှက်")]:
            status, _, body = await self.login(username=username, password=password)
            self.assertEqual(status, 401)
            self.assertIn("username or password is incorrect", body)
            self.assertNotIn('value="wrong"', body)

    async def test_authenticated_admin_cannot_reenter_login(self):
        await self.login()
        token = self.cookies[portal.COOKIE_NAME].value
        for path, method in (("/portal", "GET"), ("/portal/login", "GET"), ("/portal/login", "POST")):
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

    async def test_signed_out_admin_can_open_login_route(self):
        status, _, body = await self.request("/portal/login")
        self.assertEqual(status, 200)
        self.assertIn("Welcome back", body)

    async def test_expired_session_can_open_login_route(self):
        await self.login()
        with self.sessions() as db:
            db.query(AdminSession).update({AdminSession.expires_at: int(time.time()) - 1})
            db.commit()
        status, _, body = await self.request("/portal/login")
        self.assertEqual(status, 200)
        self.assertIn("Welcome back", body)

    async def test_login_requires_csrf_and_cookie(self):
        status, _, _ = await self.login(csrf_token="forged")
        self.assertEqual(status, 403)
        self.cookies.clear()
        status, _, _ = await self.request("/portal/login", "POST", {
            "username": "admin", "password": self.password,
        })
        self.assertEqual(status, 403)

    async def test_logout_requires_post_and_csrf(self):
        await self.login()
        status, _, _ = await self.request("/portal/logout")
        self.assertEqual(status, 405)
        status, _, _ = await self.request("/portal/logout", "POST", {"csrf_token": "forged"})
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
            db.query(User).filter(User.username == "admin").update({User.is_active: False})
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
        status, _, _ = await self.request("/static/css/pages/portal.css")
        self.assertEqual(status, 200)


if __name__ == "__main__":
    unittest.main()
