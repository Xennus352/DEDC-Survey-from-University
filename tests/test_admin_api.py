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
    async def test_directory_paginates_both_organizations_without_omitting_records(self):
        from app.storage import schema
        with self.sessions() as db:
            db.native.execute(schema.university.insert(), [
                {'uniName': f'University {i:03}', 'uniType': 'Public'} for i in range(61)
            ])
            db.native.execute(schema.ministry.insert(), [
                {'ministryName': f'Ministry {i:03}'} for i in range(31)
            ])
            db.native.commit()
        status, _, _ = await self.request('/api/admin/departments')
        self.assertEqual(status, 401)
        await self.login()
        identities = []
        for page in range(1, 5):
            status, _, data = await self.admin_request(f'/departments?page={page}')
            self.assertEqual(status, 200)
            self.assertEqual(data['total'], 92)
            self.assertEqual(data['counts'], {'university': 61, 'ministry': 31})
            identities.extend((row['organization'], row['id']) for row in data['items'])
        self.assertEqual(len(identities), 92)
        self.assertEqual(len(set(identities)), 92)
        status, _, data = await self.admin_request('/departments?type=university&search=060')
        self.assertEqual(data['total'], 1)
        self.assertEqual(data['items'][0]['name'], 'University 060')
        status, _, _ = await self.admin_request('/departments?type=invalid')
        self.assertEqual(status, 422)

    async def test_saved_answers_have_readable_details_and_matching_report_export(self):
        await self.login()
        _, _, created = await self.admin_request('/forms', 'POST', {'title': 'Readable answers'})
        form_id, version_id = created['id'], created['versions'][0]['id']
        questions = [
            {'key': 'count', 'title': 'Count', 'kind': 'number'},
            {'key': 'present', 'title': 'Present', 'kind': 'yes_no'},
            {'key': 'choice', 'title': 'Choice', 'kind': 'multiple_choice',
             'options': [{'value': 'code', 'label': 'မြန်မာ label'}]},
            {'key': 'notes', 'title': 'Notes', 'kind': 'short_text'},
            {'key': 'missing', 'title': 'Missing', 'kind': 'short_text'},
            {'key': 'members', 'title': 'Members', 'kind': 'repeating_group',
             'config': {'fields': [{'key': 'name', 'title': 'Member name', 'kind': 'short_text'}]}},
        ]
        status, _, saved = await self.admin_request(f'/forms/{form_id}/versions/{version_id}', 'PUT', {
            'title': 'Readable answers', 'revision': 1,
            'sections': [{'title': 'Answers', 'questions': questions}],
        })
        self.assertEqual(status, 200, saved)
        await self.admin_request(f'/forms/{form_id}/versions/{version_id}/publish', 'POST', {'revision': saved['revision']})
        status, _, result = await self.admin_request(f'/forms/{form_id}/submit', 'POST', {
            'answers': {'count': 0, 'present': False, 'choice': ['code'], 'notes': '', 'members': [{'name': 'Test person'}]},
        })
        self.assertEqual(status, 201, result)
        _, _, detail = await self.admin_request(f'/submissions/{result["id"]}')
        values = {a['key']: a for a in detail['sections'][0]['answers']}
        self.assertEqual(values['count']['value'], 0)
        self.assertIs(values['present']['value'], False)
        self.assertEqual(values['count']['display_value'], '0')
        self.assertEqual(values['present']['display_value'], 'No')
        self.assertEqual(values['choice']['display_value'], 'မြန်မာ label')
        self.assertEqual(values['notes']['display_value'], 'Empty text')
        self.assertEqual(values['missing']['display_value'], 'No answer')
        self.assertIn('Member name: Test person', values['members']['display_value'])
        _, _, exported = await self.admin_request(f'/reports/export/csv?form_id={form_id}')
        rows = list(csv.reader(StringIO(exported.lstrip('\ufeff'))))
        answers = {row[9]: row[11] for row in rows[6:]}
        for key, item in values.items():
            self.assertEqual(answers[key], item['display_value'])
        _, _, report = await self.admin_request(f'/reports?form_id={form_id}&question=choice')
        self.assertEqual(report['analytics']['question_distribution'][0]['display_value'], 'မြန်မာ label')
        _, _, history = await self.admin_request('/audit')
        self.assertTrue(all(item['actor_name'] == 'admin' for item in history['items']))

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

    async def test_retired_api_is_unavailable(self):
        for path in ("/surveys/", "/questions/survey/1", "/responses/"):
            status, _, _ = await self.request(path)
            self.assertEqual(status, 404, path)

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

    async def test_organization_crud_persists_and_records_audit(self):
        await self.login()
        for path, kind in (("/ministries", "ministry"), ("/universities", "university")):
            with self.subTest(kind=kind):
                status, _, created = await self.admin_request(path, "POST", {"name": "Teacher's institute", "type": "Public"})
                self.assertEqual(status, 201, created)
                identifier = created["id"]
                status, _, duplicate = await self.admin_request(path, "POST", {"name": "Teacher's institute"})
                self.assertEqual(status, 409, duplicate)
                status, _, listing = await self.admin_request(path + "?search=Teacher&limit=1")
                self.assertEqual(status, 200, listing)
                self.assertEqual(listing["total"], 1)
                self.assertEqual(listing["items"][0]["id"], identifier)
                status, _, updated = await self.admin_request(f"{path}/{identifier}", "PUT", {"name": "Updated institute", "type": "Private"})
                self.assertEqual(status, 200, updated)
                status, _, listing = await self.admin_request(path + "?search=Updated")
                self.assertEqual(listing["items"][0]["name"], "Updated institute")
                if kind == "university":
                    self.assertEqual(listing["items"][0]["type"], "Private")
                status, _, body = await self.admin_request(f"{path}/{identifier}", "DELETE")
                self.assertEqual(status, 204, body)
                _, _, listing = await self.admin_request(path)
                self.assertEqual(listing["total"], 0)
                with self.sessions() as db:
                    self.assertEqual(db.query(AuditLog).filter(AuditLog.action.in_([kind + ".create", kind + ".update", kind + ".delete"])).count(), 3)

    async def test_bulk_delete_is_atomic_and_cascades_field_options(self):
        from app.models.forms import FieldOption, FormSection, FormVersion, SurveyForm
        await self.login()
        identifiers = []
        for title in ("First draft", "Second draft"):
            _, _, form = await self.admin_request("/forms", "POST", {"title": title})
            identifiers.append(form["id"])
            version = form["versions"][0]["id"]
            status, _, result = await self.admin_request(f"/forms/{form['id']}/versions/{version}", "PUT", {
                "title": title, "revision": 1,
                "sections": [{"title": "Section", "questions": [{"key": "choice", "title": "Choose", "kind": "single_choice", "options": [{"value": "yes", "label": "Yes"}]}]}],
            })
            self.assertEqual(status, 200, result)
        status, _, _ = await self.admin_request("/forms/bulk-delete", "POST", {"ids": [identifiers[0], 99999]})
        self.assertEqual(status, 404)
        _, _, listing = await self.admin_request("/forms")
        self.assertEqual(listing["total"], 2)
        status, _, result = await self.admin_request("/forms/bulk-delete", "POST", {"ids": identifiers + [identifiers[0]]})
        self.assertEqual(status, 204, result)
        with self.sessions() as db:
            for model in (SurveyForm, FormVersion, FormSection, FormField, FieldOption):
                self.assertEqual(db.query(model).count(), 0, model.__name__)
            self.assertEqual(db.query(AuditLog).filter_by(action="form.delete").count(), 2)

    async def test_delete_rejects_forms_with_submissions_without_deleting_other_selection(self):
        await self.login()
        _, _, draft = await self.admin_request("/forms", "POST", {"title": "Keep draft"})
        _, _, protected = await self.admin_request("/forms", "POST", {"title": "With submissions"})
        with self.sessions() as db:
            db.add(Submission(version_id=protected["versions"][0]["id"], user_id=1))
            db.commit()
        for path, method, data in (
            ("/forms/bulk-delete", "POST", {"ids": [draft["id"], protected["id"]]}),
            (f"/forms/{protected['id']}", "DELETE", None),
        ):
            status, _, result = await self.admin_request(path, method, data)
            self.assertEqual(status, 409, result)
        _, _, listing = await self.admin_request("/forms")
        self.assertEqual(listing["total"], 2)

    async def test_respondent_cannot_manage_organizations_or_bulk_delete(self):
        import re
        _, _, body = await self.request("/survey/login")
        token = re.search(r'name="csrf_token" value="([^"]+)"', body).group(1)
        status, _, _ = await self.request("/survey/login", "POST", {
            "csrf_token": token, "username": "member", "password": self.password,
        })
        self.assertEqual(status, 303)
        for path, method, data in (
            ("/ministries", "GET", None), ("/universities", "GET", None),
            ("/ministries", "POST", {"name": "Forbidden"}),
            ("/universities", "POST", {"name": "Forbidden"}),
            ("/forms/bulk-delete", "POST", {"ids": [1]}),
        ):
            status, _, _ = await self.admin_request(path, method, data)
            self.assertEqual(status, 403)

    async def test_question_library_persists_options_and_reuses_duplicate_definitions(self):
        await self.login()
        question = {
            "key": "institution", "title": "  Which institution?  ",
            "kind": "single_choice", "required": True, "title_my": "အဖွဲ့အစည်း",
            "options": [{"value": "public", "label": "Public"}, {"value": "private", "label": "Private"}],
        }
        status, _, saved = await self.admin_request("/question-library", "POST", question)
        self.assertEqual(status, 200, saved)
        self.assertTrue(saved["created"])
        _, _, duplicate = await self.admin_request("/question-library", "POST", {
            **question, "key": "another_key", "title": "WHICH institution?",
        })
        self.assertFalse(duplicate["created"])
        self.assertEqual(saved["id"], duplicate["id"])
        _, _, result = await self.admin_request("/question-library?search=INSTITUTION")
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["question"]["options"], question["options"])
        self.assertTrue(result["items"][0]["question"]["required"])
        from urllib.parse import quote
        _, _, translated = await self.admin_request("/question-library?search=" + quote("အဖွဲ့အစည်း"))
        self.assertEqual(translated["total"], 1)
        with self.sessions() as db:
            from app.models.forms import QuestionBankQuestion
            self.assertEqual(db.query(QuestionBankQuestion).count(), 1)
        # Same title with a different answer definition must not modify the saved template.
        _, _, alternative = await self.admin_request("/question-library", "POST", {
            **question, "kind": "short_text", "options": [],
        })
        self.assertTrue(alternative["created"])
        _, _, result = await self.admin_request("/question-library?search=institution&limit=1")
        self.assertEqual(result["total"], 2)
        self.assertEqual(len(result["items"]), 1)

    async def test_question_library_searches_existing_forms_and_burmese_titles(self):
        await self.login()
        _, _, created = await self.admin_request("/forms", "POST", {"title": "Existing survey"})
        question = {"key": "count", "title": "ကျောင်းသား အရေအတွက်", "kind": "number", "config": {"min": 0}}
        status, _, result = await self.admin_request(
            f"/forms/{created['id']}/versions/{created['versions'][0]['id']}", "PUT", {
                "title": "Existing survey", "revision": 1,
                "sections": [{"title": "Enrollment", "questions": [question]}],
            },
        )
        self.assertEqual(status, 200, result)
        from urllib.parse import quote
        _, _, result = await self.admin_request("/question-library?search=" + quote("ကျောင်းသား"))
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["source"], "form")
        self.assertEqual(result["items"][0]["question"]["config"], {"min": 0})
        await self.admin_request("/question-library", "POST", question)
        _, _, result = await self.admin_request("/question-library?search=" + quote("ကျောင်းသား"))
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["source"], "library")
        status, _, result = await self.admin_request("/question-library", "POST", {"key": "blank", "title": "   "})
        self.assertEqual(status, 422, result)
        status, _, result = await self.admin_request("/question-library", "POST", {"key": "invalid", "title": "Choose", "kind": "single_choice"})
        self.assertEqual(status, 422, result)
        _, _, result = await self.admin_request("/question-library?search=")
        self.assertEqual(result["items"], [])

    async def test_question_library_requires_admin_and_csrf(self):
        for method, data in (("GET", None), ("POST", {"key": "q", "title": "Question"})):
            status, _, _ = await self.admin_request("/question-library", method, data)
            self.assertEqual(status, 401)
        await self.login()
        status, _, _ = await self.request("/api/admin/question-library", "POST", raw_body=b'{"key":"q","title":"Question"}', content_type="application/json")
        self.assertEqual(status, 403)
