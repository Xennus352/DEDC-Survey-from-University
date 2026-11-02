"""Exercise authenticated HTTP boundaries and real database writes, not just services."""

import csv
from io import BytesIO, StringIO
import json
from pathlib import Path
from test_portal import PortalFixture
from app.models.forms import AuditLog, FormField, Submission
from app.portal_auth import csrf_token
from app.routers.web.portal import COOKIE_NAME


class AdminApiTests(PortalFixture):
    async def admin_request(self, path, method="GET", data=None):
        if path.endswith("/submit") and data is not None:
            data = {
                "reporting_start": "2021-01-01",
                "reporting_end": "2026-03-31",
                **data,
            }
        headers = []
        if COOKIE_NAME in self.cookies:
            headers = [
                (b"x-csrf-token", csrf_token(self.cookies[COOKIE_NAME].value).encode())
            ]
        status, response_headers, body = await self.request(
            "/api/admin" + path,
            method,
            extra_headers=headers,
            raw_body=json.dumps(data).encode() if data is not None else b"",
            content_type="application/json",
        )
        try:
            result = json.loads(body)
        except ValueError:
            result = body
        return status, response_headers, result

    async def test_http_form_edit_publish_validate_submit_and_export(self):
        await self.login()
        status, _, created = await self.admin_request(
            "/forms", "POST", {"title": "API survey"}
        )
        self.assertEqual(status, 201)
        form_id = created["id"]
        version_id = created["versions"][0]["id"]
        definition = {
            "title": "API survey",
            "revision": 1,
            "sections": [
                {
                    "title": "Actual section",
                    "questions": [
                        {
                            "key": "answer",
                            "title": "Actual question",
                            "kind": "short_text",
                            "required": True,
                        }
                    ],
                }
            ],
        }
        status, _, saved = await self.admin_request(
            f"/forms/{form_id}/versions/{version_id}", "PUT", definition
        )
        self.assertEqual(status, 200, saved)
        status, _, _ = await self.admin_request(
            f"/forms/{form_id}/versions/{version_id}/validate", "POST", {"answers": {}}
        )
        self.assertEqual(status, 422)
        status, _, _ = await self.admin_request(
            f"/forms/{form_id}/versions/{version_id}/publish",
            "POST",
            {"revision": saved["revision"]},
        )
        self.assertEqual(status, 200)
        status, _, schema = await self.request(f"/api/forms/{form_id}/schema")
        self.assertEqual(status, 200)
        self.assertIn("Actual question", schema)
        status, _, result = await self.admin_request(
            f"/forms/{form_id}/submit",
            "POST",
            {"answers": {"answer": '=HYPERLINK("unsafe")'}},
        )
        self.assertEqual(status, 201, result)
        status, _, report = await self.admin_request("/reports?form_id=" + str(form_id))
        self.assertEqual(report["total"], 1)
        status, headers, export = await self.admin_request(
            "/reports/export/csv?form_id=" + str(form_id)
        )
        self.assertEqual(status, 200)
        self.assertIn("'=HYPERLINK", export)
        self.assertIn("Form", export)
        status, _, _ = await self.admin_request(
            "/submissions/review", "POST", {"ids": [result["id"]], "status": "approved"}
        )
        self.assertEqual(status, 200)
        status, _, report = await self.admin_request("/reports?status=rejected")
        self.assertEqual(report["total"], 0)
        with self.sessions() as db:
            self.assertEqual(db.query(Submission).one().status, "approved")
            self.assertTrue(
                db.query(AuditLog).filter_by(action="report.export").first()
            )

    async def test_admin_write_requires_csrf_and_preserves_published_form(self):
        await self.login()
        status, _, _ = await self.request(
            "/api/admin/forms",
            "POST",
            raw_body=b'{"title":"CSRF"}',
            content_type="application/json",
        )
        self.assertEqual(status, 403)
        status, _, forms = await self.admin_request("/forms")
        self.assertEqual(forms["total"], 0)

    async def test_user_update_cannot_remove_own_admin_access_or_leak_password(self):
        await self.login()
        _, _, data = await self.admin_request("/users")
        admin = next(u for u in data["items"] if u["username"] == "admin")
        status, _, _ = await self.admin_request(
            "/users/" + str(admin["id"]),
            "PUT",
            {"username": "admin", "role_id": admin["role_id"], "is_active": False},
        )
        self.assertEqual(status, 409)
        status, _, result = await self.admin_request(
            "/users",
            "POST",
            {"username": "new-user", "role_id": 2, "password": "test-password-123"},
        )
        self.assertEqual(status, 201, result)
        _, _, result = await self.admin_request("/users")
        self.assertNotIn("password", json.dumps(result))

    async def test_legacy_mobile_payloads_still_round_trip(self):
        status, _, body = await self.request(
            "/surveys/",
            "POST",
            raw_body=b'{"title":"Legacy","year":2026}',
            content_type="application/json",
        )
        self.assertEqual(status, 200, body)
        survey = json.loads(body)
        status, _, body = await self.request(
            f"/questions/survey/{survey['id']}",
            "POST",
            raw_body=b'{"text":"Legacy question","question_type":"multiple_choice","options":[{"text":"Yes"}]}',
            content_type="application/json",
        )
        self.assertEqual(status, 200, body)
        question = json.loads(body)
        payload = {
            "survey_id": survey["id"],
            "respondent_id": "mobile-123",
            "answers": [
                {
                    "question_id": question["id"],
                    "option_id": question["options"][0]["id"],
                    "answer_text": None,
                }
            ],
        }
        status, _, body = await self.request(
            "/responses/",
            "POST",
            raw_body=json.dumps(payload).encode(),
            content_type="application/json",
        )
        self.assertEqual(status, 200, body)
        self.assertEqual(json.loads(body)["respondent_id"], "mobile-123")

    async def test_respondent_can_submit_without_administrator_permissions(self):
        await self.login()
        _, _, created = await self.admin_request(
            "/forms", "POST", {"title": "Respondent survey"}
        )
        form_id = created["id"]
        version_id = created["versions"][0]["id"]
        definition = {
            "title": "Respondent survey",
            "revision": 1,
            "sections": [
                {
                    "title": "Section",
                    "questions": [
                        {"key": "answer", "title": "Your answer", "kind": "short_text"}
                    ],
                }
            ],
        }
        _, _, saved = await self.admin_request(
            f"/forms/{form_id}/versions/{version_id}", "PUT", definition
        )
        await self.admin_request(
            f"/forms/{form_id}/versions/{version_id}/publish",
            "POST",
            {"revision": saved["revision"]},
        )
        self.cookies.clear()
        _, _, body = await self.request("/survey/login")
        import re

        token = re.search(r'name="csrf_token" value="([^"]+)"', body).group(1)
        status, _, _ = await self.request(
            "/survey/login",
            "POST",
            {"csrf_token": token, "username": "member", "password": self.password},
        )
        self.assertEqual(status, 303)
        status, _, _ = await self.request("/api/admin/session")
        self.assertEqual(status, 403)
        status, _, _ = await self.request("/survey")
        self.assertEqual(status, 200)
        token = csrf_token(self.cookies[COOKIE_NAME].value)
        status, _, body = await self.request(
            f"/api/forms/{form_id}/submissions",
            "POST",
            raw_body=b'{"answers":{"answer":"Real respondent answer"},"reporting_start":"2021-01-01","reporting_end":"2026-03-31"}',
            content_type="application/json",
            extra_headers=[(b"x-csrf-token", token.encode())],
        )
        self.assertEqual(status, 201, body)
        with self.sessions() as db:
            self.assertNotEqual(db.query(Submission).one().user_id, 1)

    async def test_reporting_period_is_required_and_reversed_dates_are_rejected(self):
        await self.login()
        for period in [
            {"reporting_start": None, "reporting_end": None},
            {"reporting_start": "2026-06-30", "reporting_end": "2026-01-01"},
        ]:
            status, _, _ = await self.admin_request(
                "/forms/999/submit", "POST", {"answers": {}, **period}
            )
            self.assertEqual(status, 422)

    async def test_administrator_can_create_a_respondent_role(self):
        await self.login()
        status, _, role = await self.admin_request(
            "/roles", "POST", {"name": "Enumerator"}
        )
        self.assertEqual(status, 201)
        _, _, directory = await self.admin_request("/users")
        self.assertIn(role, directory["roles"])
