"""Regression coverage for dashboard requests and native builder persistence."""
from datetime import date
import json
from app.admin_auth import COOKIE_NAME
from app.portal_auth import csrf_token

from test_portal import PortalFixture
from app.storage.existing import metadata


class DashboardRecoveryTests(PortalFixture):
    persistent_metadata = metadata

    async def admin_request(self, path, method="GET", data=None, csrf=True):
        headers = [(b"x-csrf-token", csrf_token(self.cookies[COOKIE_NAME].value).encode())] if csrf else []
        status, headers, body = await self.request(
            "/api/admin" + path, method, extra_headers=headers,
            raw_body=json.dumps(data).encode() if data is not None else b"",
            content_type="application/json",
        )
        return status, headers, json.loads(body) if body else None

    async def test_dashboard_data_endpoints_return_the_workspace_contract(self):
        await self.login()
        for path, keys in (
            ('/overview', ('forms', 'submissions', 'trend')),
            ('/forms?limit=100', ('items', 'total')),
            ('/reports', ('items', 'total', 'statuses')),
            ('/users?limit=100', ('items', 'roles', 'total')),
            ('/audit', ('items', 'total')),
        ):
            status, _, data = await self.admin_request(path)
            self.assertEqual(status, 200, (path, data))
            for key in keys:
                self.assertIn(key, data, path)

    async def test_builder_year_and_question_survive_new_requests(self):
        await self.login()
        status, _, year = await self.admin_request('/survey/years', 'POST', {
            'year_from': 3, 'year_to': 2026, 'status': 1,
        })
        self.assertEqual(status, 201, year)
        self.assertEqual(year['year_from'], 3)
        _, _, matching = await self.admin_request('/survey/years?search=2026')
        self.assertEqual([row['yID'] for row in matching], [year['yID']])
        _, _, missing = await self.admin_request('/survey/years?search=2030')
        self.assertEqual(missing, [])
        status, _, title = await self.admin_request('/survey/question-titles', 'POST', {
            'qTDetail': 'Digital facilities',
        })
        self.assertEqual(status, 201, title)
        status, _, question = await self.admin_request('/survey/questions/university', 'POST', {
            'yID': year['yID'], 'qTID': title['qTID'], 'uQDetail': 'Computer laboratories',
        })
        self.assertEqual(status, 201, question)
        status, _, builder = await self.admin_request(f"/survey/builder/university/{year['yID']}")
        self.assertEqual(status, 200, builder)
        self.assertEqual(builder['questions'][0]['question_detail'], 'Computer laboratories')
        status, _, data = await self.admin_request(f"/survey/years/{year['yID']}")
        self.assertEqual(data['year_from'], 3)
        with self.sessions() as db:
            row = db.native.execute(metadata.tables['year'].select().where(
                metadata.tables['year'].c.yID == year['yID'])).one()
            self.assertEqual(row.yearFrom, date(2026, 3, 1))

    async def test_builder_page_has_its_controls_and_keeps_authentication(self):
        status, _, _ = await self.request('/dashboard/survey-builder')
        self.assertEqual(status, 303)
        status, _, _ = await self.request('/api/admin/survey/years')
        self.assertEqual(status, 401)
        await self.login()
        status, _, body = await self.request('/dashboard/survey-builder')
        self.assertEqual(status, 200)
        self.assertIn('id="years-table"', body)
        self.assertIn('id="form-canvas"', body)
        self.assertIn('survey-builder.js', body)
        status, _, _ = await self.admin_request('/survey/years', 'POST', {
            'year_from': 3, 'year_to': 2026, 'status': 1,
        }, csrf=False)
        self.assertEqual(status, 403)


class PrivateDashboardRecoveryTests(DashboardRecoveryTests):
    metadata_storage = 'private'
